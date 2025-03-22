import pyautogui
import re

offsetx, offsety = (0, 0)

current = input("current: ")
current = re.sub('[()]', '', current)
# (812, 25), (853, 36)
tlx, tly, blx, bly  = (int(x.strip()) for x in current.split(","))

while True:

    pyautogui.screenshot(region=(tlx + offsetx, tly + offsety, blx - tlx, bly - tly)).show()

    tlx += int(input("shift left x: "))
    tly += int(input("shift left y: "))
    blx += int(input("shift left x: "))
    bly += int(input("shift left y: "))
    print(f"current: ({tlx}, {tly}), ({blx}, {bly})")