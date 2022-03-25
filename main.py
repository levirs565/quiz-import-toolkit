import dearpygui.dearpygui as dpg
import cv2
import pytesseract
import re

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


def process_text(raw_text: str, excluded_list: list[str]):
    result = ""
    lines = strip_lines(raw_text.splitlines())
    question_line = []
    answers = []
    is_answer = False
    for line in lines:
        if excluded_list.count(line):
            continue

        word = re.split("\s+", line)
        answer_index = None
        first = word[0]
        if len(first) == 2 and first.endswith("."):
            alphabet = ["a", "b", "c", "d", "e", "f"]
            if alphabet.count(first[0]) > 0:
                is_answer = True
                answer_index = first[0]

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

file_dialog_tag = "file_dialog_id"
texture_tag = "texture_id"
preview_tag = "preview_id"
input_tag = "input_id"
excluded_tag = "excluded_id"
loading_tag = "loading_id"

texture_registry = dpg.add_texture_registry()

vid_capture = None
frame = None
frame_size = (0, 0)
preview_size = (0, 0)
cv_win = "Select Region"


def open_file(sender, data):
    global vid_capture
    global frame_size
    global preview_size

    print(data)
    vid_capture = cv2.VideoCapture(data['file_path_name'])
    frame_size = (
        int(vid_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(vid_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    preview_size = frame_size

    update_frame()


def show_preview():
    preview = cv2.resize(frame, preview_size)
    preview_pos = (0, 0)
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


def update_frame():
    global frame
    ret, frame = vid_capture.read()
    show_preview()


def resize_preview():
    global preview_size
    preview_size = util.calculate_image_contain_size(
        frame, (dpg.get_item_width(preview_tag), dpg.get_item_height(preview_tag)))
    show_preview()


def jump_frame_msec(diff):
    current_milis = vid_capture.get(cv2.CAP_PROP_POS_MSEC)
    vid_capture.set(cv2.CAP_PROP_POS_MSEC, current_milis + diff)
    update_frame()


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


with dpg.file_dialog(show=False, tag=file_dialog_tag, callback=open_file):
    dpg.add_file_extension(".mp4")

with dpg.window(label="Quiz Video OCR"):
    with dpg.group(horizontal=True):
        dpg.add_button(label="Open",
                       callback=lambda: dpg.show_item(file_dialog_tag))
        dpg.add_button(label="Previous Second",
                       callback=lambda: jump_frame_msec(-1000))
        dpg.add_button(label="Erase", callback=erase_frame)
        dpg.add_button(label="Process", callback=process_frame)
        dpg.add_button(label='Next Second',
                       callback=lambda: jump_frame_msec(1000))
        dpg.add_button(label="Resize Preview", callback=resize_preview)
    dpg.add_input_text(label="Excluded Lines",
                       multiline=True, tag=excluded_tag)
    dpg.add_input_text(label="Text", multiline=True, tag=input_tag)
    dpg.add_loading_indicator(
        label="Processing text...", show=False, tag=loading_tag)


dpg.set_value(excluded_tag, "Select one:\nPilih salah satu:")

dpg.create_viewport()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.maximize_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
