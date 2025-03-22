from PIL import Image
import pytesseract
import numpy as np
import cv2
import pyautogui
import time

SCREENSHOT_DIR = "screenshots\\"

def get_image(image_path):
    return Image.open(SCREENSHOT_DIR + image_path)

def ss(name, bounds):
    return pyautogui.screenshot(region=bounds)

def extract_sub_image(image, p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    image = Image.fromarray(np.array(image)[int(min(y1, y2)) : int(max(y1, y2)), int(min(x1, x2)) : int(max(x1, x2))], "RGB")
    return image

def get_high_contrast_image(image):
    gry = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    (h, w) = gry.shape[:2]
    gry = cv2.resize(gry, (w * 2, h * 2))
    erd = cv2.erode(gry, None, iterations=1)
    thr = cv2.threshold(erd, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # thr = cv2.threshold(erd, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # bnt = cv2.bitwise_not(thr)
    return Image.fromarray(thr)

def extract_text_from_image(image):
    new_image = get_high_contrast_image(image)
    text = pytesseract.image_to_string(new_image, lang='eng', config='--psm 7').strip()
    return text

def extract_number_from_image(image):
    new_image = get_high_contrast_image(image)
    num = pytesseract.image_to_string(new_image, config="--psm 7 digits").strip()
    return num

def extract_color_from_image(image):
    pix = np.array(image)
    color = np.mean(pix, axis=(0,1))
    return color

def check_master(image):
    color = extract_color_from_image(image)
    return color[0] > color[2]

# extraction_args = {
#     # var_name: top_left_pixel, bottom_right_pixel, extraction_func
#     "song": ((50, 8), (600, 31), extract_text_from_image),
#     "artist": ((52, 27), (203, 43), extract_text_from_image),
#     "is_master": ((812, 31), (852, 42), check_master),
#     "bpm": ((749, 127), (799, 148), extract_number_from_image),
#     "time": ((674, 25), (731, 44), extract_number_from_image),
# }

extraction_args_deck_1 = {
    # var_name: top_left_pixel, bottom_right_pixel, extraction_func
    "song": ((52, 270), (602, 293), extract_text_from_image),
    "artist": ((54, 289), (205, 305), extract_text_from_image),
    "is_master": ((814, 293), (854, 304), check_master),
    "bpm": ((751, 389), (801, 410), extract_number_from_image),
    "time": ((676, 287), (733, 306), extract_number_from_image),
}

extraction_args_deck_3 = {
    # var_name: top_left_pixel, bottom_right_pixel, extraction_func
    "song": ((52, 465), (602, 488), extract_text_from_image),
    "artist": ((54, 484), (205, 500), extract_text_from_image),
    "is_master": ((814, 488), (854, 499), check_master),
    "bpm": ((751, 584), (801, 605), extract_number_from_image),
    "time": ((676, 482), (733, 501), extract_number_from_image),
}

def get_x(image, extraction_args, var_name):
    top_left_pixel, bottom_right_pixel, extraction_func = extraction_args[var_name]
    return extraction_func(extract_sub_image(image, top_left_pixel, bottom_right_pixel))

def check_all():
    image = pyautogui.screenshot()

    print("deck 1:")
    for k in extraction_args_deck_1.keys():
        print(k, "=", get_x(image, extraction_args_deck_1, k))
    print()

    print("deck 3:")
    for k in extraction_args_deck_3.keys():
        print(k, "=", get_x(image, extraction_args_deck_3, k))

    print()
    print("======")
    print()

while True:
    check_all()
    time.sleep(5)