import configparser

config = configparser.ConfigParser()
config.read('config.ini')

SAVE_PATH = config.get('DEFAULT', 'SAVE_PATH')
ASSETS_PATH = config.get('DEFAULT', 'ASSETS_PATH')
FONT_PATH = ASSETS_PATH + "/fonts/"
CHARACTER_PATH = ASSETS_PATH + "/characters/"
