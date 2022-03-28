import dearpygui.dearpygui as dpg
import cv2
import pytesseract
import re
import os
import json
from datetime import datetime

from scipy.__config__ import show
import util
import numpy as np


def strip_lines(list: list):
    lines = []
    for line in list:
        line = line.strip()
        if len(line) == 0:
            continue
        lines.append(line)
    return lines


def analyze_answer_line(line: str):
    word = re.split("\s+", line, maxsplit=1)
    if len(word) != 2:
        return (None, None)
    first, more = word
    answer_index = None
    if len(first) == 2 and first.endswith("."):
        alphabet = ["a", "b", "c", "d", "e", "f"]
        if alphabet.count(first[0]) > 0:
            answer_index = first[0]

    return (answer_index, more)


def process_text(raw_text: str, excluded_list: list[str]):
    result = ""
    lines = strip_lines(raw_text.splitlines())
    question_line = []
    answers = []
    is_answer = False
    for line in lines:
        if excluded_list.count(line):
            continue

        answer_index, _ = analyze_answer_line(line)
        if answer_index != None:
            is_answer = True

        if is_answer == False:
            question_line.append(line)
        if is_answer == True:
            if answer_index is not None:
                pos = line.find(answer_index)
                text = ""
                if line[pos+1] == ".":
                    text = line[pos+2:].strip()
                else:
                    text = line[pos+1:].strip()

                answers.append([answer_index + ". " + text])
            else:
                if len(answers) == 0:
                    answers.append([line])
                else:
                    answers[-1].append(line)

    result += " ".join(question_line) + "\n"
    for answer in answers:
        result += " ".join(answer) + "\n"
    return result


dpg.create_context()

video_file_dialog_tag = "file_dialog_id"
texture_tag = "texture_id"
preview_tag = "preview_id"
input_tag = "input_id"
excluded_tag = "excluded_id"
loading_tag = "loading_id"
video_nav_tag = "video_nav_id"
frame_operation_tag = "frame_operation_id"

texture_registry = dpg.add_texture_registry()

vid_capture = None
frame = None
frame_size = (0, 0)
preview_size = (0, 0)
cv_win = "Select Region"


def open_video_file(sender, data):
    global vid_capture
    global frame_size
    global preview_size

    vid_capture = cv2.VideoCapture(data['file_path_name'])
    frame_size = (
        int(vid_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(vid_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    preview_size = frame_size

    update_video_frame()
    dpg.show_item(video_nav_tag)
    dpg.show_item(frame_operation_tag)


def show_preview():
    preview = cv2.resize(frame, preview_size)
    preview_pos = (350, 0)
    data = np.flip(preview, 2)
    data = data.ravel()
    data = np.asfarray(data, dtype='f')
    texture_data = np.true_divide(data, 255.0)

    if dpg.does_item_exist(texture_tag):
        if dpg.get_item_width(texture_tag) == preview_size[0] and dpg.get_item_height(texture_tag) == preview_size[1]:
            dpg.set_value(texture_tag, texture_data)
            return
        preview_pos = dpg.get_item_pos(preview_tag)
        dpg.delete_item(texture_tag)
        dpg.remove_alias(texture_tag)
        dpg.delete_item(preview_tag)

    dpg.add_raw_texture(
        preview_size[0], preview_size[1], texture_data, format=dpg.mvFormat_Float_rgb, tag=texture_tag, parent=texture_registry)

    with dpg.window(label="Preview", tag=preview_tag, pos=preview_pos):
        dpg.add_image(texture_tag=texture_tag)


def update_video_frame():
    global frame
    ret, frame = vid_capture.read()
    show_preview()


def resize_preview():
    global preview_size
    preview_size = util.calculate_image_contain_size(
        frame, (dpg.get_item_width(preview_tag), dpg.get_item_height(preview_tag)))
    show_preview()


def jump_video_frame_msec(diff):
    current_milis = vid_capture.get(cv2.CAP_PROP_POS_MSEC)
    vid_capture.set(cv2.CAP_PROP_POS_MSEC, current_milis + diff)
    update_video_frame()


def select_region():
    cv2.namedWindow(cv_win, cv2.WINDOW_NORMAL |
                    cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)
    rect = cv2.selectROI(cv_win, frame, fromCenter=False)
    cv2.destroyWindow(cv_win)
    return (rect[0], rect[1], rect[0]+rect[2], rect[1]+rect[3])


def erase_frame():
    rect = select_region()
    cv2.rectangle(frame, (rect[0], rect[1]),
                  (rect[2], rect[3]), (255, 255, 255), thickness=cv2.FILLED)
    print(rect)
    show_preview()


def process_frame():
    rect = select_region()
    process_frame = frame[rect[1]:rect[3], rect[0]:rect[2]]

    dpg.show_item(loading_tag)

    text = str(pytesseract.image_to_string(
        process_frame, lang="ind+eng", config="--oem 1 --psm 6"))
    excluded = dpg.get_value(excluded_tag).splitlines()
    new_text = process_text(text, excluded)
    print(new_text)
    dpg.set_value(input_tag, dpg.get_value(input_tag) + new_text)

    dpg.hide_item(loading_tag)


def extract_image():
    rect = select_region()
    image = frame[rect[1]:rect[3], rect[0]:rect[2]]
    now = datetime.now()
    name = now.strftime("%d-%m-%Y %H-%M-%S") + ".png"
    if not os.path.exists("image"):
        os.makedirs("image")
    cv2.imwrite("image/" + name, image)


def export_to_quizx():
    text = strip_lines(dpg.get_value(input_tag).splitlines())
    question_list = []
    for line in text:
        answer_index, answer = analyze_answer_line(line)
        if answer_index == None:
            question_list.append({
                "type": "short-text",
                "question": line,
                "answer": ""
            })
        else:
            question = question_list[-1]
            choices = question.get("choices", [])
            choices.append(answer)
            question["choices"] = choices
            question["type"] = "multiple-choice"
            question["answer"] = 0

    quiz = {
        "title": "",
        "questions": question_list
    }
    raw = json.dumps(quiz, indent=4)

    with dpg.window(label="QuizX Json"):
        dpg.add_input_text(default_value=raw, multiline=True, readonly=True)


with dpg.file_dialog(show=False, tag=video_file_dialog_tag, callback=open_video_file):
    dpg.add_file_extension(".mp4")

with dpg.window(label="Quiz OCR", autosize=True, min_size=(350, 0)):
    dpg.add_button(label="Open Video",
                   callback=lambda: dpg.show_item(video_file_dialog_tag))
    with dpg.collapsing_header(label="Video Navigation", leaf=True, tag=video_nav_tag, show=False):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Previous Second",
                           callback=lambda: jump_video_frame_msec(-1000))
            dpg.add_button(label='Next Second',
                           callback=lambda: jump_video_frame_msec(1000))
    with dpg.collapsing_header(label="Frame Operation", leaf=True, tag=frame_operation_tag, show=False):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Erase", callback=erase_frame)
            dpg.add_button(label="Process", callback=process_frame)
            dpg.add_button(label="Extract Image", callback=extract_image)
            dpg.add_button(label="Resize Preview", callback=resize_preview)
    with dpg.collapsing_header(label="Quiz", leaf=True):
        dpg.add_button(label="Export to QuizX", callback=export_to_quizx)
        dpg.add_input_text(label="Excluded Lines", default_value="Select one:\nPilih salah satu:",
                           multiline=True, tag=excluded_tag)
        dpg.add_input_text(label="Text", multiline=True, tag=input_tag)
        dpg.add_loading_indicator(
            label="Processing text...", show=False, tag=loading_tag)

dpg.create_viewport()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.maximize_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
