from math import floor
import dearpygui.dearpygui as dpg
import cv2
import pytesseract
import re
import os
import json
import fitz
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


def analyze_question_index(line: str):
    word = re.split("\s+", line, maxsplit=1)
    if len(word) != 2:
        return (None, None)
    first, more = word
    dot_index = first.find(".")
    question_index = None
    if dot_index > 0:
        number_str = first[:dot_index]
        try:
            question_index = int(number_str)
        except:
            pass
    return (question_index, more)


dpg.create_context()

picture_file_dialog_tag = "picture_file_dialog_id"
pdf_file_dialog_tag = "pdf_file_dialog_id"
video_file_dialog_tag = "video_file_dialog_id"
texture_tag = "texture_id"
preview_tag = "preview_id"
input_tag = "input_id"
excluded_tag = "excluded_id"
loading_tag = "loading_id"
video_nav_tag = "video_nav_id"
frame_operation_tag = "frame_operation_id"

texture_registry = dpg.add_texture_registry()

vid_capture = None
pdf_file = None
pdf_page_number = 0
frame = None
frame_size = (0, 0)
preview_size = (0, 0)
cv_win = "Select Region"


def reset_layout():
    dpg.hide_item(video_nav_tag)
    dpg.hide_item(frame_operation_tag)


def open_picture_file(sender, data):
    global frame
    global frame_size
    global preview_size

    reset_layout()

    frame = cv2.imread(data['file_path_name'])
    img_h, img_w, c = frame.shape
    frame_size = (img_w, img_h)
    preview_size = frame_size

    show_preview()
    dpg.show_item(frame_operation_tag)


def open_pdf_file(sender, data):
    global pdf_file
    global pdf_page_number
    global preview_size

    reset_layout()

    pdf_file = fitz.Document(data['file_path_name'])
    pdf_page_number = 0
    preview_size = (0, 0)

    update_pdf_page()
    dpg.show_item(frame_operation_tag)


def open_video_file(sender, data):
    global vid_capture
    global frame_size
    global preview_size

    reset_layout()

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


def update_pdf_page():
    global frame
    global frame_size
    global preview_size
    page = pdf_file.load_page(0)
    pixmap = page.get_pixmap(alpha=False, dpi=144)
    frame_size = (pixmap.w, pixmap.h)
    if preview_size == (0, 0):
        preview_size = frame_size
    frame = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.h, pixmap.w, pixmap.n)
    frame = np.ascontiguousarray(frame[..., [2, 1, 0]])
    show_preview()


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
    excluded = dpg.get_value(excluded_tag).splitlines()

    rect = select_region()
    process_frame = frame[rect[1]:rect[3], rect[0]:rect[2]]

    dpg.show_item(loading_tag)

    data = pytesseract.image_to_data(
        process_frame, lang="ind+eng", output_type=pytesseract.Output.DICT)
    lines_words = []
    last_block_num = 0
    last_line_num = 0
    last_right = 0
    for i in range(len(data['text'])):
        level = data['level'][i]
        if level != 5:
            continue
        text = data['text'][i]
        block_num = data['block_num'][i]
        line_num = data['line_num'][i]
        left = data['left'][i]
        width = data['width'][i]
        right = left + width

        if block_num != last_block_num or line_num != last_line_num:
            lines_words.append([text])
        else:
            char_width = width / len(text)
            delta_pixel = left - last_right
            delta_char = floor(delta_pixel / char_width)
            if delta_char >= 4:
                lines_words.append([text])
            else:
                lines_words[-1].append(text)

        last_block_num = block_num
        last_line_num = line_num
        last_right = right

    lines = map(lambda words: " ".join(words), lines_words)
    lines = filter(lambda line: excluded.count(line) == 0, lines)
    new_text = "\n".join(lines) + "\n"

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
    is_question = False
    is_answer = False
    for line in text:
        answer_index, answer = analyze_answer_line(line)
        question_index, question = analyze_question_index(line)
        if question_index != None:
            question_list.append({
                "type": "short-text",
                "question": question,
                "answer": ""
            })
            is_question = True
            is_answer = False
        elif answer_index != None:
            question = question_list[-1]
            choices = question.get("choices", [])
            choices.append(answer)
            question["choices"] = choices
            question["type"] = "multiple-choice"
            question["answer"] = 0

            is_answer = True
            is_question = False
        elif is_question:
            question_list[-1]["question"] += "\n" + line
        elif is_answer:
            question_list[-1]["choices"][-1] += "\n" + line
        else:
            print(answer_index, answer)
            print(question_index, question_index)
            raise Exception("Unknown condition")

    quiz = {
        "title": "",
        "questions": question_list
    }
    raw = json.dumps(quiz, indent=4)

    with dpg.window(label="QuizX Json"):
        dpg.add_input_text(default_value=raw, multiline=True, readonly=True)


with dpg.file_dialog(show=False, tag=picture_file_dialog_tag, callback=open_picture_file):
    dpg.add_file_extension(".jpg")
    dpg.add_file_extension(".png")

with dpg.file_dialog(show=False, tag=pdf_file_dialog_tag, callback=open_pdf_file):
    dpg.add_file_extension('.pdf')

with dpg.file_dialog(show=False, tag=video_file_dialog_tag, callback=open_video_file):
    dpg.add_file_extension(".mp4")

with dpg.window(label="Quiz OCR", autosize=True, min_size=(350, 0)):
    with dpg.group(horizontal=True):
        dpg.add_button(label="Open Picture",
                       callback=lambda: dpg.show_item(picture_file_dialog_tag))
        dpg.add_button(label="Open PDF",
                       callback=lambda: dpg.show_item(pdf_file_dialog_tag))
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
