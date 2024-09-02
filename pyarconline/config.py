import configparser
import os.path

config = configparser.ConfigParser()
config.read('config.ini')

SAVE_PATH = config.get('DEFAULT', 'SAVE_PATH')
IMG_SAVE_PATH = config.get('DEFAULT', 'IMG_SAVE_PATH')
ASSETS_PATH = config.get('DEFAULT', 'ASSETS_PATH')

FRIEND_LIST_PATH = os.path.join(SAVE_PATH, 'friendlist.json')
RATINGS_PATH = os.path.join(SAVE_PATH, 'ratings.json')
RATINGS_OLD_PATH = os.path.join(SAVE_PATH, 'ratings_old.json')

ASSETS_B30_PATH = os.path.join(ASSETS_PATH, 'b30')
CHIERI_PATH = os.path.join(ASSETS_B30_PATH, 'cheri')
CHIERI_BG_PATH = os.path.join(CHIERI_PATH, 'bg.png')
CHIERI_MASK_PATH = os.path.join(CHIERI_PATH, 'mask.png')
CHIERI_TABLE_PATH = os.path.join(CHIERI_PATH, 'table.png')

DIAMOND_PATH = os.path.join(ASSETS_PATH, 'diamonds')
FONT_PATH = os.path.join(ASSETS_PATH, "fonts")
DIFF_PATH = os.path.join(ASSETS_PATH, "diff")
GRADE_PATH = os.path.join(ASSETS_PATH, "grade")
SONG_PATH = os.path.join(ASSETS_PATH, "songs")
SONG_RANDOM_PATH = os.path.join(SONG_PATH, "random.jpg")
CHARACTER_PATH = os.path.join(ASSETS_PATH, "characters")
SansSerifFLF_PATH = os.path.join(FONT_PATH, "SansSerifFLF.otf")
Roboto_Light_PATH = os.path.join(FONT_PATH, "Roboto-Light.ttf")
Exo_Regular_PATH = os.path.join(FONT_PATH, "Exo-Regular.ttf")
OpenSans_Regular_PATH = os.path.join(FONT_PATH, "OpenSans-Regular.ttf")
DB_PATH = os.path.join(SAVE_PATH, 'b30data.db')


def get_diamond_path(n: str):
    return os.path.join(DIAMOND_PATH, f"rating_{n}.png")


def get_cover_path(id: str, difficulty: int):
    cover_path = os.path.join(SONG_PATH, f"{id}_{str(difficulty)}.jpg")
    if not os.path.exists(cover_path):
        cover_path = os.path.join(SONG_PATH, f"{id}.jpg")
    if not os.path.exists(cover_path):
        cover_path = SONG_RANDOM_PATH
    return cover_path


def get_diff_path(difficulty: int):
    return os.path.join(DIFF_PATH, f"diff_{str(difficulty)}.png")


def get_grade_path(grade: str):
    return os.path.join(GRADE_PATH, f"grade_{grade}.png")
