import math
import sys
import time
import random
import getpass
import os

import requests
from PIL import Image
from requests.adapters import HTTPAdapter

random.seed(time.time())



colors = [
    (255, 255, 255),
    (228, 228, 228),
    (136, 136, 136),
    (34, 34, 34),
    (255, 167, 209),
    (229, 0, 0),
    (229, 149, 0),
    (160, 106, 66),
    (229, 217, 0),
    (148, 224, 68),
    (2, 190, 1),
    (0, 211, 221),
    (0, 131, 199),
    (0, 0, 234),
    (207, 110, 228),
    (130, 0, 128)
]



def board_get_bitmap():
    "Fetch and store board as image"

    import urllib.request
    url = 'https://www.reddit.com/api/place/board-bitmap'
    response = urllib.request.urlopen(url, timeout=10)

    image = Image.new('P', (1000, 1000))
    # Set image color palette. PIL palettes have all colors
    # concatenated into one list: (255,255,255,228,228,228,...)
    image.putpalette(sum(colors, ()))
    pixels = image.load()

    for y in range(1000):
        for x in range(500):
            datum = ord(response.read(1))
            color1 = datum >> 4
            color2 = datum - (color1 << 4)
            pixels[x*2,     y] = color1
            pixels[x*2 + 1, y] = color2

    return image



def roll(image, delta):
    "Roll an image sideways"

    xsize, ysize = image.size

    delta = delta % xsize
    if delta == 0: return image

    part1 = image.crop((0, 0, delta, ysize))
    part2 = image.crop((delta, 0, xsize, ysize))
    image.paste(part2, (0, 0, xsize-delta, ysize))
    image.paste(part1, (xsize-delta, 0, xsize, ysize))

    return image



def get_differences(board, ref, offset):
    board_rgb = board.convert("RGB")
    (size_x, size_y) = ref.size
    board_img = board_rgb.crop((offset[0], offset[1], offset[0] + size_x, offset[1] + size_y))

    diff = []
    assert ref.mode == "RGBA"
    for i in range(size_x):
        for j in range(size_y):
            if ref.getpixel((i,j))[3] > 0:
                if ref.getpixel((i,j))[:3] != board_img.getpixel((i,j)):
                    diff.append((i,j))

    return diff



def find_palette(point):
    def distance(c1, c2):
        (r1, g1, b1) = c1
        (r2, g2, b2) = c2
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    closest_colors = sorted(colors, key=lambda color: distance(color, point))
    closest_color = closest_colors[0]

    return colors.index(closest_color)



def place_pixel(ax, ay, new_color):
    print ("Probing pixel {},{}:".format(ax, ay))

    while True:
        request_url = "http://reddit.com/api/place/pixel.json?x={}&y={}"
        r = s.get(request_url.format(ax, ay), timeout=5)
        if r.status_code == 200:
            data = r.json()
            break
        else:
            print("ERROR: ", r, r.text)
        time.sleep(random.randint(5, 10))

    old_color = data["color"] if "color" in data else 0
    old_user_name = data["user_name"] if "user_name" in data else "<nobody>"

    if old_color == new_color:
        print("Skipping, color #{} set by {}".format(new_color, old_user_name))
        time.sleep(.25)
        return None
    else:
        print("Placing color #{}, ".format(new_color), end='')
        print("currently #{} by {}.".format(old_color, old_user_name))

        r = s.post("https://www.reddit.com/api/place/draw.json",
                   data={"x": str(ax), "y": str(ay), "color": str(new_color)})

        if "error" not in r.json():
            print("Placed color.")
        else:
            print("Could not place color: cooldown period?")

        return r



def place_image(ref, offset):
    "Place image ref at offset"

    print("Starting image placement:")
    print("Image of width {}, height {};".format(ref.size[0], ref.size[1]))
    print("Offset: {}.".format(offset))

    while True:
        print("Getting differential:")
        board = board_get_bitmap()
        roll(board, 8)
        diff = get_differences(board, ref, offset)

        if not diff:
            print("All done, sleeping.")
            time.sleep(random.randint(5,10))
        else:
            print("Got {} diffs.".format(len(diff)))
            random.shuffle(diff)

            while diff:
                point = diff[0]

                ax = offset[0] + point[0]
                ay = offset[1] + point[1]
                r = place_pixel(ax, ay, colors.index(ref.getpixel(point)[:3]))

                if r is not None:
                    if "error" not in r.json():
                        diff.remove(point)

                    wait_seconds = float(r.json()["wait_seconds"])
                    wait_time = int(wait_seconds) + 2
                    while (wait_time > 0):
                        msg = "Waiting {} seconds. Diffs left: {}.".format(wait_time, len(diff))
                        time.sleep(1)
                        wait_time -= 1
                        if wait_time > 0:
                            print(msg, end="              \r")
                        else:
                            print(msg)
                else:
                    diff.remove(point)



# _ref = Image.open(sys.argv[1])
# _offset = (int(sys.argv[2]), int(sys.argv[3]))

# For now, setting it to Link
_ref = Image.open("Link_Field.png")
_offset = (299,454)

username = sys.argv[1]
password = getpass.getpass(prompt="Enter password for {}:".format(username))

while True:
    try:
        s = requests.Session()
        s.mount('https://www.reddit.com', HTTPAdapter(max_retries=5))
        s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36"
        r = s.post("https://www.reddit.com/api/login/{}".format(username),
                   data={"user": username, "passwd": password, "api_type": "json"})
        s.headers['x-modhash'] = r.json()["json"]["data"]["modhash"]

        place_image(_ref, _offset)
    except:
        print("Got an error, restarting...")
    finally:
        time.sleep(random.randint(5,10))
