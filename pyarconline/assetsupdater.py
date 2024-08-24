from pyarconline.utils import DifficultyRatingList
from pyarconline import ASSETS_PATH, SongList
import os
import fnmatch


def find_matching_images(pattern, directory):
    matching_files = []
    for root, dirs, files in os.walk(directory):
        for filename in fnmatch.filter(files, pattern):
            full_path = os.path.join(root, filename)
            matching_files.append(full_path)

    return matching_files


img_path = r"C:\Users\Bangn\Downloads\arcaea_5.9.3c\assets\songs"
songs = SongList("./pyarconline/songlist")
if not os.path.exists(ASSETS_PATH):
    os.mkdir(ASSETS_PATH)
    os.mkdir(os.path.join(ASSETS_PATH, "songs"))
if not os.path.exists(os.path.join(ASSETS_PATH, "songs")):
    os.mkdir(os.path.join(ASSETS_PATH, "songs"))
SAVE_PATH = ASSETS_PATH + "/songs"

rating_list = DifficultyRatingList(songs)
for song in rating_list:
    dir_path1 = os.path.join(img_path, song["id"])
    dir_path2 = os.path.join(img_path, "dl_" + song["id"])
    real_dir_path = ""
    if os.path.exists(dir_path1):
        real_dir_path = dir_path1
    elif os.path.exists(dir_path2):
        real_dir_path = dir_path2
    else:
        raise Exception(f"{dir_path1} or {dir_path2} does not exist")
    pattern1 = "*" + str(song["difficulty"]) + "_256.jpg"
    pattern2 = "*base_256.jpg"
    matching_files1 = find_matching_images(pattern1, real_dir_path)
    matching_files2 = find_matching_images(pattern2, real_dir_path)
    matching_files = matching_files1
    dst_path = SAVE_PATH + "/" + song["id"] + "_" + str(song["difficulty"]) + ".jpg"
    if len(matching_files) == 0:
        matching_files = matching_files2
        dst_path = SAVE_PATH + "/" + song["id"] + ".jpg"
    if len(matching_files) == 0:
        raise Exception(f"{dir_path1} or {dir_path2} does not exist")
    if len(matching_files) > 1:
        raise Exception(f"{dir_path1} or {dir_path2} contains multiple songs")
    if os.path.exists(dst_path):
        continue
    with open(matching_files[0], "rb") as src, open(dst_path, "wb") as dst:
        dst.write(src.read())
