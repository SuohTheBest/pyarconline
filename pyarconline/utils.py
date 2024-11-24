import re
import string
import time
import random
import requests
import requests.utils
import requests.cookies
import json
from bs4 import BeautifulSoup
import os
from pyarconline import exceptions
from .config import SAVE_PATH, FRIEND_LIST_PATH, RATINGS_PATH, RATINGS_OLD_PATH


def check_response(response):
    if not response['success']:
        raise exceptions.ApiException(response)


class WebapiUtils:
    """
    This class provides utility functions for interacting with the arcaea web api.

    Note: This class does not perform any validation checks on the data!
    It is the responsibility of the caller to ensure that the data being sent
    to the server is valid and properly formatted. This class merely facilitates
    the transmission of data to the server.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})

    @staticmethod
    def create_boundary_str() -> str:
        characters = string.digits + string.ascii_lowercase + string.ascii_uppercase
        random_string = ''.join(random.choice(characters) for _ in range(16))
        boundary = f"----WebKitFormBoundary{random_string}"
        return boundary

    def authenticate(self):
        response = self.session.get('https://webapi.lowiro.com/auth/me')
        return response.json()

    def userinfo(self):
        response = self.session.get('https://webapi.lowiro.com/webapi/user/me')
        return response.json()

    def clear_statistic(self, difficulty: int):
        response = self.session.get(f'https://webapi.lowiro.com/webapi/user/me/clear_statistic?difficulty={difficulty}')
        return response.json()

    def add_friend(self, friend_code: str):
        # if you have a better way, please tell me😥
        boundary = self.create_boundary_str()
        self.session.headers.update({'Content-Type': f'multipart/form-data; boundary={boundary}'})
        data = f"""--{boundary}\r\nContent-Disposition: form-data; name="friend_code"\r\n\r\n{friend_code}\r\n--{boundary}--\r\n"""
        response = self.session.post('https://webapi.lowiro.com/webapi/friend/me/add', data=data)
        self.session.headers.pop('Content-Type')
        return response.json()

    def delete_friend(self, friend_id: str):
        boundary = self.create_boundary_str()
        self.session.headers.update({'Content-Type': f'multipart/form-data; boundary={boundary}'})
        data = f"""--{boundary}\r\nContent-Disposition: form-data; name="friend_id"\r\n\r\n{friend_id}\r\n--{boundary}--\r\n"""
        response = self.session.post('https://webapi.lowiro.com/webapi/friend/me/delete', data=data)
        self.session.headers.pop('Content-Type')
        return response.json()

    def login(self, email: str, password: str):
        data = {'email': email, 'password': password}
        response = self.session.post('https://webapi.lowiro.com/auth/login', json=data)
        return response.json()

    def logout(self):
        data = {}
        response = self.session.post('https://webapi.lowiro.com/auth/logout', json=data)
        return response.json()

    def my_score(self, difficulty: int, page: int, sort: str, term: str = ""):
        """
        returns your score. you should subscribe arcaea online before using this function
        :param difficulty: 0-3
        :param page: 1-count/10+1
        :param sort: score,date,score_below_max,title
        :param term: search term
        :return: response
        """
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/score/song/me/all?difficulty={difficulty}&page={page}&sort={sort}&term={term}')
        return response.json()

    def world_rank_score(self, song_id: str, difficulty: int, limit: int = 20):
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/score/song?song_id={song_id}&difficulty={difficulty}&limit={limit}')
        return response.json()

    def friend_rank_score(self, song_id: str, difficulty: int, limit: int = 30):
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/score/song/friend?song_id={song_id}&difficulty={difficulty}&limit={limit}')
        return response.json()

    def my_rating(self):
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/score/rating/me')
        return response.json()

    def my_rating_progression(self, duration: str):
        """
        returns your rating progression, you should subscribe arcaea online before using this function
        :param duration: w,m,y,3y,5y
        :return: response
        """
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/score/rating_progression/me?duration={duration}')
        return response.json()

    def get_apk_url(self):
        response = self.session.get(
            f'https://webapi.lowiro.com/webapi/serve/static/bin/arcaea/apk')
        return response.json()


class SongList:
    # todo:to be done
    def __init__(self, song_list_path):
        self.song_list_path = song_list_path
        with open(self.song_list_path, 'r', encoding='UTF-8') as f:
            self.song_list = json.load(f)
        self.song_list = self.song_list['songs']

    def __getitem__(self, idx: int):
        return self.song_list[idx]

    def __iter__(self):
        return iter(self.song_list)

    async def get_song_info(self, *args):
        """
        accept one parameter, which is either idx or id.

        Examples: get_song_info(0) equals to get_song_info('sayonarahatsukoi').
        :param args: idx or id of the song
        :return: complete song_info in json format
        :raises SongNotFoundError: if song does not exist
        :raises TypeError: if len(args) != 1 or args[0] is not an int or a string
        """
        if len(args) > 1 or len(args) == 0:
            raise TypeError('Invalid arguments')
        if isinstance(args[0], int):
            return self.song_list[args[0]]
        elif isinstance(args[0], str):
            for song in self.song_list:
                if song['id'] == args[0]:
                    return song
            raise exceptions.SongNotFoundError(args[0])
        else:
            raise TypeError('Invalid arguments')

    def get_song_name(self, song_idx: int, is_beyond: bool, country: str = 'en'):
        song = self.song_list[song_idx]
        if 'deleted' in song:
            return ''
        if country in song['title_localized']:
            song_name = song['title_localized'][country]
        else:
            song_name = song['title_localized']['en']
        if is_beyond and len(song['difficulties']) > 3:
            beyond_song = song['difficulties'][3]
            if 'title_localized' in beyond_song:
                if country in beyond_song['title_localized']:
                    song_name = beyond_song['title_localized'][country]
                else:
                    song_name = beyond_song['title_localized']['en']
        return song_name

    async def get_all_song_ids(self):
        ans = []
        for song in self.song_list:
            ans.append(song['id'])
        return ans

    async def get_song_id_idx(self, song_name: str, is_beyond: bool):
        for song in self.song_list:
            curr_song_name = self.get_song_name(song['idx'], is_beyond, 'ja')
            if song_name == curr_song_name:
                return song['id'], song['idx']
        raise exceptions.SongNotFoundError(song_name)


class FriendManager:
    def __init__(self, webapi: WebapiUtils):
        if not os.path.exists(SAVE_PATH):
            os.makedirs(SAVE_PATH)
        self.recent_use = {}
        try:
            with open(FRIEND_LIST_PATH, 'r') as f:
                content = json.load(f)
                for item in content:
                    self.recent_use[item['friend_id']] = item['recent_use']
        except FileNotFoundError:
            with open(FRIEND_LIST_PATH, 'w') as f:
                f.write('[]')
        self.webapi = webapi
        # you should log in first!
        userinfo = self.webapi.userinfo()
        check_response(userinfo)
        userinfo = userinfo['value']
        self.max_friend = userinfo['max_friend']
        self.friends = userinfo['friends']
        self.curr_friend = len(self.friends)
        self.user_id = userinfo['user_id']
        self.user_code = userinfo['user_code']

    async def save_mapping(self):
        json_array = [{"friend_id": friend_id, "recent_use": recent_use} for
                      friend_id, recent_use in
                      self.recent_use.items()]
        with open(FRIEND_LIST_PATH, 'w') as json_file:
            json.dump(json_array, json_file, indent=4)

    async def delete_friend_least_used(self):
        least_use_id = min(self.recent_use, key=self.recent_use.get)
        response = self.webapi.delete_friend(least_use_id)
        check_response(response)
        del self.recent_use[least_use_id]
        self.curr_friend -= 1

    async def add_friend(self, friend_code: str):
        if self.curr_friend == self.max_friend:
            await self.delete_friend_least_used()
        if not friend_code.isdigit() or len(friend_code) != 9:
            raise exceptions.FriendcodeError(friend_code)
        old_ids = []
        for friend in self.friends:
            old_ids.append(friend['user_id'])
        response = self.webapi.add_friend(friend_code)
        check_response(response)
        self.friends = response['value']['friends']
        new_user = -1
        for friend in self.friends:
            if friend['user_id'] not in old_ids:
                new_user = friend['user_id']
                break
        self.recent_use[new_user] = time.time()
        self.curr_friend += 1
        if new_user == -1:
            raise exceptions.PyarconlineException("Unknown Error. Unable to add friend.")
        return new_user

    async def record(self, friend_id: int):
        self.recent_use[friend_id] = time.time()

    async def update_friend(self):
        response = self.webapi.userinfo()
        check_response(response)
        self.friends = response['value']['friends']

    async def get_friend_info(self, friend_id: int):
        await self.update_friend()
        for friend in self.friends:
            if friend['user_id'] == friend_id:
                self.recent_use[friend_id] = time.time()
                return friend
        raise exceptions.FriendNotFoundError(friend_id)

    async def get_friend_id(self, name: str):
        await self.update_friend()
        for friend in self.friends:
            if friend['name'] == name:
                return friend['user_id']
        raise exceptions.FriendNotFoundError(name)


class DifficultyRatingList:
    def __init__(self, songList: SongList):
        if not os.path.exists(SAVE_PATH):
            os.makedirs(SAVE_PATH)
        self.rating_list = []
        self.version = "0.0"
        self.song_list = songList
        try:
            with open(RATINGS_PATH, 'r', encoding='UTF-8') as f:
                ratings = json.load(f)
                self.rating_list = ratings['value']
                self.version = ratings['version']
        except FileNotFoundError:
            self.save()

    def __getitem__(self, index: int):
        if isinstance(index, slice):
            return self.rating_list[index.start:index.stop:index.step]
        else:
            return self.rating_list[index]

    def __len__(self):
        return len(self.rating_list)

    def __iter__(self):
        return iter(self.rating_list)

    def save(self):
        with open(RATINGS_PATH, 'w', encoding='UTF-8') as f:
            content = {'version': self.version, 'value': self.rating_list}
            json.dump(content, f, indent=4)

    async def update_via_wikiwiki(self):
        """
        This function relies on an external website to fetch difficulty rating data (wikiwiki.jp).
        Due to the dependence on the external service, the function may not be stable.
        Please use this function with caution, and ensure to handle potential exceptions or errors that may arise.
        """
        # back_up
        self.save()
        with (open(RATINGS_PATH, 'r', encoding='UTF-8') as source,
              open(RATINGS_OLD_PATH, 'w', encoding='UTF-8') as target):
            target.write(source.read())
        self.version = "0.0"
        self.rating_list = []
        session = requests.session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'})
        response = session.get(
            'https://wikiwiki.jp/arcaea/%E8%AD%9C%E9%9D%A2%E5%AE%9A%E6%95%B0%E8%A1%A8')  # difficulty rating >= 8.0
        response_code = response.status_code
        assert response_code == 200
        soup = BeautifulSoup(response.text, 'html.parser')
        table_elements = soup.find_all(class_='h-scrollable')
        difficulty_rating_re = r'<a class="rel-wiki-page".*?>(.*?)<\/a>.*?background-color:(.*?);.*?<td style="text-align:center; width:30px;">([0-9\.]*)<\/td><\/tr>'
        version_re = r'\(iOS/Android : ver.(.*?)収録分 '
        version = re.findall(version_re, response.text)
        assert len(version) > 0
        self.version = version[0]
        for element in table_elements:
            matches = re.findall(difficulty_rating_re, str(element))
            for match in matches:
                title = match[0]
                difficulty = match[1]
                rating = match[2]
                # 0=past 1=present 2=future 3=beyond 4=eternal
                if difficulty == 'Deepskyblue':
                    difficulty = 0
                elif difficulty == 'Mediumseagreen':
                    difficulty = 1
                elif difficulty == 'Mediumvioletred':
                    difficulty = 2
                elif difficulty == 'Firebrick':
                    difficulty = 3
                elif difficulty == 'Slateblue':
                    difficulty = 4
                title_space = title.replace('<br class="spacer"/>', ' ')
                title_nospace = title.replace('<br class="spacer"/>', '')
                # 'foreign key'
                is_beyond = False
                if difficulty == 3:
                    is_beyond = True
                # song_id, song_idx = await self.song_list.get_song_id_idx(title_space, is_beyond)
                try:
                    song_id, song_idx = await self.song_list.get_song_id_idx(title_space, is_beyond)
                except Exception:
                    try:
                        song_id, song_idx = await self.song_list.get_song_id_idx(title_nospace, is_beyond)
                    except Exception as e:
                        print(e)
                        song_idx = int(input(f"Song {title_nospace} not found in database, please specify its idx."))
                        song_id = (await self.song_list.get_song_info(song_idx))['id']
                    title_space = self.song_list.get_song_name(song_idx, is_beyond, 'en')
                self.rating_list.append(
                    {'idx': song_idx, 'id': song_id, 'title': title_space, 'difficulty': difficulty, 'rating': rating})
        self.save()
