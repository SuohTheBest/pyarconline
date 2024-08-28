import asyncio
from pyarconline.utils import *
from pyarconline.exceptions import *
from pyarconline.worker import WorkerLauncher


class ArcOnlineHelper:
    def __init__(self, username, password):
        song_list = SongList(r'D:/programs/arcaea-helper/pyarconline/pyarconline/songlist')
        self.difficulty_rating = DifficultyRatingList(song_list)
        self.webapi = WebapiUtils()
        self.login(username, password)
        self.friend_manager = FriendManager(self.webapi)
        self.launcher = WorkerLauncher(song_list, self.difficulty_rating, self.webapi, self.friend_manager)

    def login(self, username, password):
        response = self.webapi.login(username, password)
        is_logged_in = response['isLoggedIn']
        if not is_logged_in:
            raise LoginError

    async def handle_task(self, name: str, work_type: str):
        print("started.")
        user_id = await self.friend_manager.get_friend_id(name)
        await self.launcher.start_task(user_id, work_type)
