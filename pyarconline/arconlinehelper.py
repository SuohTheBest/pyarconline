import atexit
import sqlite3
from pyarconline.utils import *
from pyarconline.exceptions import *
from pyarconline.worker import WorkerLauncher
from pyarconline.config import DB_PATH, SONGLIST_PATH


class ArcOnlineHelper:
    def __init__(self, username, password):
        song_list = SongList(SONGLIST_PATH)
        self.difficulty_rating = DifficultyRatingList(song_list)
        self.webapi = WebapiUtils()
        self.login(username, password)
        self.friend_manager = FriendManager(self.webapi)
        self.launcher = WorkerLauncher(song_list, self.difficulty_rating, self.webapi, self.friend_manager)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init_db()
        atexit.register(self._exit)

    def _exit(self):
        self.friend_manager.save_mapping()

    def _init_db(self):
        self.c.execute('''
        CREATE TABLE IF NOT EXISTS user(
        id TEXT PRIMARY KEY NOT NULL,
        user_id INTEGER NOT NULL,
        user_code TEXT NOT NULL
        )''')
        self.conn.commit()

    def login(self, username, password):
        response = self.webapi.login(username, password)
        is_logged_in = response['isLoggedIn']
        if not is_logged_in:
            raise LoginError

    async def handle_task(self, name: str, work_type: str, **kwargs):
        print("started.")
        user_id = await self.friend_manager.get_friend_id(name)
        ans = await self.launcher.start_task(user_id, work_type, **kwargs)
        return ans

    async def add_friend(self, friend_code: str, identifier: str = ''):
        friend_id = await self.friend_manager.add_friend(friend_code)
        if identifier == '':
            identifier = str(friend_id)
        self.c.execute('''
            INSERT INTO user (id, user_id, user_code) VALUES (?, ?, ?)
        ''', (identifier, friend_id, friend_code))
        self.conn.commit()
        return identifier
