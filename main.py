import cv2
import re
import pytesseract


def test_two_list_simmiliarity(list_1: list, list_2: list):
    simmiliar_item = 0
    for item_1 in list_1:
        for item_2 in list_2:
            if item_1 == item_2:
                simmiliar_item += 1
                break
    return simmiliar_item / max(len(list_1), len(list_2))


def strip_lines(list: list):
    lines = []
    for line in list:
        line = line.strip()
        if len(line) == 0:
            continue
        lines.append(line)
    return lines


win = "Frame"
cv2.namedWindow(win, cv2.WINDOW_NORMAL |
                cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)


vid_capture = cv2.VideoCapture(
    "C:\\Users\\levir\\Downloads\\NitroShare\\Record_2021-12-15-08-21-44.mp4")

if vid_capture.isOpened() == False:
    print("Error opening video")

fps = vid_capture.get(cv2.CAP_PROP_FPS)
frame_count = vid_capture.get(cv2.CAP_PROP_FRAME_COUNT)
print('FPS: ', fps, " Frame Count: ", frame_count)

current_frame_pos = 0
last_frame_pos = 0
while vid_capture.isOpened():
    ret, frame = vid_capture.read()
    current_frame_pos = vid_capture.get(cv2.CAP_PROP_POS_FRAMES)
    if ret:
        can_process = current_frame_pos - last_frame_pos >= fps or last_frame_pos == 0
        if can_process == False:
            continue

        last_frame_pos = current_frame_pos

        cv2.imshow(win, frame)
        key = cv2.waitKey()

        if key == ord('q'):
            break
        if key != ord("p"):
            continue

        rect = cv2.selectROI('Frame', frame, fromCenter=False)
        frame = frame[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]

        original_text = str(pytesseract.image_to_string(
            frame, lang="ind+eng", config="--oem 1 --psm 6"))
        lines = strip_lines(original_text.splitlines())
        content_index = 0
        for count, line in enumerate(lines):
            line = line.strip()
            if line.find("Question") >= 0 and line.find("Flag") >= 0:
                content_index = count + 2
                continue
            if line == "question":
                content_index = count + 1
                continue
        lines = lines[content_index:]

        # quest = []
        question_line = []
        answers = []
        is_answer = False
        for line in lines:
            # if line.find("Quiz navigation") >= 0 or line.find("Finish attempt") >= 0 or line.find("Time left") >= 0 or line.find("Previous") >= 0 or line.find("Next") >= 0:
            #     continue
            # choice_regex = "^\S+\s+[abcdef]\."
            # if re.search(choice_regex, line):
            #     line = re.sub(choice_regex, "", line)
            # procesed_lines.append(line)
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
    else:
        break

vid_capture.release()
cv2.destroyAllWindows()
