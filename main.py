import dearpygui.dearpygui as dpg
import cv2
import pytesseract
import re
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


def process_text(raw_text: str):
    result = ""
    lines = strip_lines(raw_text.splitlines())
    result += "Original text: \n" + "\n".join(lines) + "\n\n\n"
    question_line = []
    answers = []
    is_answer = False
    for line in lines:
        if line.find("Select one") >= 0:
            is_answer = True
            continue
        if is_answer == False:
            question_line.append(line)
        if is_answer == True:
            word = re.split("\s+", line)
            answer_index = None
            first = word[0]
            if len(first) <= 3:
                alphabet = ["a", "b", "c", "d", "e", "f"]
                chars = []
                if len(word) >= 2:
                    chars.append(word[1][0])
                if first[-1] == ".":
                    chars.append(first[-2])
                else:
                    chars.append(first[-1])
                for char in chars:
                    count = alphabet.count(char)
                    if count > 0:
                        answer_index = char
                        break
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

    result += "Question: \n" + " ".join(question_line) + "\n"
    for answer in answers:
        result += " ".join(answer) + "\n"
    return result


dpg.create_context()

file_dialog_tag = "file_dialog_id"
texture_tag = "texture_id"
input_tag = "input_id"

texture_registry = dpg.add_texture_registry()

vid_capture = None
frame = None
orig_size = (0, 0)
preview_frame_size = (0, 0)
cv_win = "Select Region"


def open_file(sender, data):
    global vid_capture
    global orig_size

    print(data)
    vid_capture = cv2.VideoCapture(data['file_path_name'])
    orig_size = (
        vid_capture.get(cv2.CAP_PROP_FRAME_WIDTH),
        vid_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    update_frame()


def show_preview(texture_data):
    if dpg.does_item_exist(texture_tag):
        if dpg.get_item_width(texture_tag) == orig_size[0] and dpg.get_item_height(texture_tag) == orig_size[1]:
            dpg.set_value(texture_tag, texture_data)
            return
        dpg.delete_item(texture_tag)

    dpg.add_raw_texture(
        orig_size[0], orig_size[1], texture_data, format=dpg.mvFormat_Float_rgb, tag=texture_tag, parent=texture_registry)

    with dpg.window(label="Preview"):
        dpg.add_image(texture_tag=texture_tag)


def update_frame():
    global frame
    global preview_frame_size
    ret, frame = vid_capture.read()
    data = np.flip(frame, 2)
    data = data.ravel()
    data = np.asfarray(data, dtype='f')
    texture_data = np.true_divide(data, 255.0)
    show_preview(texture_data)


def jump_frame_msec(diff):
    current_milis = vid_capture.get(cv2.CAP_PROP_POS_MSEC)
    vid_capture.set(cv2.CAP_PROP_POS_MSEC, current_milis + diff)
    update_frame()


def process_frame():
    cv2.namedWindow(cv_win, cv2.WINDOW_NORMAL |
                    cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)
    rect = cv2.selectROI(cv_win, frame, fromCenter=False)
    cv2.destroyWindow(cv_win)
    process_frame = frame[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]
    text = str(pytesseract.image_to_string(
        process_frame, lang="ind+eng", config="--oem 1 --psm 6"))
    new_text = process_text(text)
    print(new_text)
    dpg.set_value(input_tag, dpg.get_value(input_tag) + new_text)


with dpg.file_dialog(show=False, tag=file_dialog_tag, callback=open_file):
    dpg.add_file_extension(".mp4")

with dpg.window(label="Quiz Video OCR"):
    with dpg.group(horizontal=True):
        dpg.add_button(label="Open",
                       callback=lambda: dpg.show_item(file_dialog_tag))
        dpg.add_button(label="Previous Second",
                       callback=lambda: jump_frame_msec(-1000))
        dpg.add_button(label="Process", callback=process_frame)
        dpg.add_button(label='Next Second',
                       callback=lambda: jump_frame_msec(1000))
    dpg.add_input_text(label="Text", multiline=True, tag=input_tag)

dpg.create_viewport()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
