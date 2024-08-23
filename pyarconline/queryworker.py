import heapq
import multiprocessing
import queue
import threading
import sqlite3
import time

from pyarconline import WebapiUtils, SongList, DifficultyRatingList, FriendManager, exceptions
from .config import SAVE_PATH
from .utils import check_response

conn = sqlite3.connect(SAVE_PATH + '/b30data.db', check_same_thread=False)
cursor = conn.cursor()
sem1 = multiprocessing.Semaphore(0)
sem2 = multiprocessing.Semaphore(0)


def create_score_table(name: str):
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {name} (
        idx INTEGER NOT NULL,
        difficulty KEY NOT NULL,
        title TEXT NOT NULL,
        rating TEXT NOT NULL,
        play_time INTEGER NOT NULL,
        time_stamp INTEGER NOT NULL,
        score INTEGER NOT NULL,
        clear_type INTEGER NOT NULL,
        potential REAL NOT NULL,
        PRIMARY KEY (idx, difficulty)
        )
    ''')
    conn.commit()


class QueryWorker(threading.Thread):
    def __init__(self, name: str, q: queue.Queue, song_list: SongList, difficulty_rating: DifficultyRatingList,
                 webapi: WebapiUtils, friend_manager: FriendManager):
        threading.Thread.__init__(self, name=name)
        self.queue = q
        self.song_list = song_list
        self.difficulty_rating = difficulty_rating
        self.webapi = webapi
        self.friend_manager = friend_manager

    def run(self):
        while True:
            sem1.acquire()
            workload = self.queue.get()
            user_id = workload['user_id']
            work_type = workload['work_type']
            rating = workload['rating']
            last_active = workload['last_active']
            table_name = 'scoreTable_' + str(user_id)
            create_score_table(table_name)
            cursor.execute(f'''
            SELECT * FROM {table_name} ORDER BY potential DESC
            ''')
            rows = cursor.fetchall()
            cursor.execute('''
            SELECT name FROM sqlite_master WHERE type='table'
            ''')
            tables = [t[0] for t in cursor.fetchall()]
            rows_dict = {(row[0], row[1]): row for row in rows}
            priority_queue = []
            song_size = len(self.difficulty_rating)
            i = 0
            for item in rows:
                i += 1
                if i > 30:
                    break
                heapq.heappush(priority_queue, item[8])

            if work_type == 'b30':
                for i in range(song_size):
                    b30_low_potential = 0.0 if len(priority_queue) == 0 else priority_queue[0]
                    print("current:", i, "b30_low_potential:", b30_low_potential)
                    curr_song = self.difficulty_rating[i]
                    curr_rating = curr_song["rating"]
                    curr_id = curr_song["id"]
                    curr_idx = curr_song["idx"]
                    curr_difficulty = curr_song["difficulty"]
                    if 20 + int(10 * float(curr_rating)) <= int(10 * b30_low_potential):
                        print("break", 20 + int(10 * float(curr_rating)), int(10 * b30_low_potential))
                        break
                    if (curr_idx, curr_difficulty) in rows_dict and last_active <= \
                            rows_dict[(curr_idx, curr_difficulty)][5]:
                        print("continue")
                        continue
                    curr_potential = self.update(curr_idx, curr_id, curr_difficulty, user_id, curr_rating, tables)
                    if curr_potential is not None:
                        heapq.heappush(priority_queue, curr_potential)
                    if len(priority_queue) > 30:
                        heapq.heappop(priority_queue)
            elif work_type == 'all':
                for i in range(song_size):
                    curr_song = self.difficulty_rating[i]
                    curr_rating = curr_song["rating"]
                    curr_id = curr_song["id"]
                    curr_idx = curr_song["idx"]
                    curr_difficulty = curr_song["difficulty"]
                    if (curr_idx, curr_difficulty) in rows_dict and last_active <= \
                            rows_dict[(curr_idx, curr_difficulty)][5]:
                        print("continue")
                        continue
                    self.update(curr_idx, curr_id, curr_difficulty, user_id, curr_rating, tables)

            conn.commit()

    def update(self, idx: int, song_id: str, difficulty: int, user_id: int, rating: str, tables):
        response = self.webapi.friend_rank_score(song_id, difficulty)
        check_response(response)
        data = response["value"]
        potential = None
        for item in data:
            curr_user_id = item["user_id"]
            curr_table_name = 'scoreTable_' + str(curr_user_id)
            if curr_table_name not in tables:
                continue

            timestamp = int(1000 * time.time())
            score = item["score"]
            curr_potential = self.count_potential(score, rating)
            if curr_user_id == user_id:
                potential = curr_potential
            cursor.execute(f'''
            INSERT INTO {curr_table_name} (idx, difficulty, title, rating, play_time, time_stamp, score, clear_type, potential)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT (idx,difficulty)
            DO UPDATE SET play_time=excluded.play_time, time_stamp=excluded.time_stamp, score=excluded.score, clear_type=excluded.clear_type,potential=excluded.potential
            ''', (
                idx, difficulty, song_id, rating, item["time_played"], timestamp, score,
                item["best_clear_type"], curr_potential))
        conn.commit()
        time.sleep(1)
        return potential

    @staticmethod
    def count_potential(score: int, rating: str):
        real_rating = float(rating)
        ans = 0.0
        if score >= 10000000:
            ans = real_rating + 2.0
        elif score >= 9800000:
            ans = real_rating + 1.0 + (score - 9800000) / 200000
        else:
            ans = max(0.0, real_rating + (score - 9500000) / 300000)
        return round(ans, 5)


class DrawingWorker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)


class WorkerLauncher:
    def __init__(self, song_list: SongList, difficulty_rating: DifficultyRatingList,
                 webapi: WebapiUtils, friend_manager: FriendManager):
        self.q = queue.Queue()
        self.friend_manager = friend_manager
        self.query_worker = QueryWorker("query-worker", self.q, song_list, difficulty_rating, webapi, friend_manager)
        self.query_worker.start()

    async def start_task(self, user_id: int, work_type: str):
        friend = await self.friend_manager.get_friend_info(user_id)
        rating = friend["rating"]
        _score = friend["recent_score"][0]
        last_active = 0
        if "time_played" in _score:
            last_active = _score["time_played"]
        self.q.put({"user_id": user_id, "work_type": work_type, "rating": rating, "last_active": last_active,
                    "name": friend["name"], "character": friend["character"]})
        sem1.release()
