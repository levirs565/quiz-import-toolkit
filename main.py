import sys
import cv2
import re
import pytesseract

def strip_lines(list: list):
    lines = []
    for line in list:
        line = line.strip()
        if len(line) == 0:
            continue
        lines.append(line)
    return lines


def process_text(text: str):
    lines = strip_lines(text.splitlines())
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
            alphabet = ["a", "b", "c", "d", "e", "f"]
            chars = [word[1][0]]
            answer_index = None
            if word[0][-1] == ".":
                chars.append(word[0][-2])
            else:
                chars.append(word[0][-1])
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

                answers.append(answer_index + ". " + text)
            else:
                print(text)

    print(" ".join(question_line))
    print("\n".join(answers))


win = "Frame"
cv2.namedWindow(win, cv2.WINDOW_NORMAL |
                cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)


vid_capture = cv2.VideoCapture(sys.argv[1])

if vid_capture.isOpened() == False:
    print("Error opening video")

fps = vid_capture.get(cv2.CAP_PROP_FPS)
frame_count = vid_capture.get(cv2.CAP_PROP_FRAME_COUNT)
print('FPS: ', fps, " Frame Count: ", frame_count)
print("Press q to quit, p to process frame, n to next frame")

last_frame_pos = 0
ret, frame = vid_capture.read()
current_frame_pos = vid_capture.get(cv2.CAP_PROP_POS_FRAMES)
while vid_capture.isOpened():
    if not ret:
        break

    can_process = current_frame_pos - last_frame_pos >= fps or last_frame_pos == 0
    if can_process:
        cv2.imshow(win, frame)
        key = cv2.waitKey()

        if key == ord('q'):
            break
        if key == ord("p"):
            rect = cv2.selectROI(win, frame, fromCenter=False)
            frame = frame[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]

            text = str(pytesseract.image_to_string(
                frame, lang="ind+eng", config="--oem 1 --psm 6"))
            process_text(text)
            continue
        if key != ord("n"):
            continue

        last_frame_pos = current_frame_pos

    ret, frame = vid_capture.read()
    current_frame_pos = vid_capture.get(cv2.CAP_PROP_POS_FRAMES)

vid_capture.release()
cv2.destroyAllWindows()
