import PySimpleGUI as sg
import cv2
import pytesseract
import re
import util


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


key_frame = "-FRAME-"
key_processed = "-PROCESSED-"

text_open = "Open"
text_next = "Next Second"
text_prev = "Previous Second"
text_process = "Process"

layout = [
    [
        sg.Column([

            [
                sg.Button(text_open),
            ],
            [
                sg.Button(text_prev)
            ],
            [
                sg.Button(text_process)
            ],
            [
                sg.Button(text_next)
            ],
            [
                sg.Multiline(key=key_processed, expand_y=True, size=(30, 0)),
            ]
        ], expand_y=True),
        sg.Column(
            [
                [
                    sg.Image(filename="", key=key_frame, expand_y=True, expand_x=True, background_color="red")
                ]
            ],
            expand_y=True, expand_x=True
        )
    ],
]

window = sg.Window(title="Quiz Video OCR", layout=layout,
                   margins=(0, 0), resizable=True)

vid_capture = None
frame = None
orig_size = (0, 0)
preview_frame_size = (0, 0)
cv_win = "Select Region"


def update_preview_frame(frame):
    data = cv2.imencode('.png', frame)[1].tobytes()
    window[key_frame].update(data=data)


def update_frame():
    global frame
    global preview_frame_size
    ret, frame = vid_capture.read()
    update_preview_frame(frame)
    preview_frame_size = orig_size


def jump_frame_msec(diff):
    current_milis = vid_capture.get(cv2.CAP_PROP_POS_MSEC)
    vid_capture.set(cv2.CAP_PROP_POS_MSEC, current_milis + diff)
    update_frame()


while True:
    event, values = window.read(timeout=20)

    if event == sg.WIN_CLOSED:
        break

    if event == text_open:
        print(values)
        vid_capture = cv2.VideoCapture(sg.popup_get_file("Select Video"))
        orig_size = (
            vid_capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            vid_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        update_frame()

    if event == text_next:
        jump_frame_msec(1000)

    if event == text_prev:
        jump_frame_msec(-1000)

    if event == text_process:
        cv2.namedWindow(cv_win, cv2.WINDOW_NORMAL |
                        cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)
        w, h = window.size
        cv2.resizeWindow(cv_win, w, h)
        rect = cv2.selectROI(cv_win, frame, fromCenter=False)
        cv2.destroyWindow(cv_win)
        process_frame = frame[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]
        text = str(pytesseract.image_to_string(
            process_frame, lang="ind+eng", config="--oem 1 --psm 6"))
        window[key_processed].update(process_text(text))

    if frame is not None:
        img_size = window[key_frame].get_size()
        if img_size == (1, 1):
            continue
        if img_size == preview_frame_size:
            continue
        update_preview_frame(util.image_contain(frame, img_size))
        preview_frame_size = img_size

window.close()
