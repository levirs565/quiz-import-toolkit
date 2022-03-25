import cv2


def calculate_image_contain_size(img, dest_size):
    img_h, img_w, c = img.shape
    dest_w, dest_h = dest_size

    img_ratio = img_w / img_h
    dest_ratio = dest_w / dest_h

    if img_ratio != dest_ratio:
        if img_ratio > dest_ratio:
            new_height = int(img_h / img_w * dest_w)
            dest_size = (dest_w, new_height)
        else:
            new_width = int(img_w / img_h * dest_h)
            dest_size = (new_width, dest_h)

    return dest_size
