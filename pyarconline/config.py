import configparser

config = configparser.ConfigParser()
config.read('config.ini')

SAVE_PATH = config.get('DEFAULT', 'SAVE_PATH')
ASSETS_PATH = config.get('DEFAULT', 'ASSETS_PATH')