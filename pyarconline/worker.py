import datetime
import heapq
import multiprocessing
import os
import queue
import threading
import sqlite3
import time
from PIL import Image, ImageFont, ImageDraw

from pyarconline import WebapiUtils, SongList, DifficultyRatingList, FriendManager
from .config import CHARACTER_PATH, IMG_SAVE_PATH, DB_PATH, CHIERI_BG_PATH, CHIERI_MASK_PATH, \
    get_diamond_path, SansSerifFLF_PATH, OpenSans_Regular_PATH, Roboto_Light_PATH, Exo_Regular_PATH, CHIERI_TABLE_PATH, \
    get_cover_path, get_diff_path, get_grade_path
from .utils import check_response

sem1 = multiprocessing.Semaphore(0)
sem2 = multiprocessing.Semaphore(0)


def average(lst):
    return sum(lst) / len(lst)


class QueryWorker(threading.Thread):
    def __init__(self, name: str, q: queue.Queue, song_list: SongList, difficulty_rating: DifficultyRatingList,
                 webapi: WebapiUtils):
        threading.Thread.__init__(self, name=name)
        self.queue = q
        self.song_list = song_list
        self.difficulty_rating = difficulty_rating
        self.webapi = webapi
        self.q2 = queue.Queue()
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.drawing_worker = DrawingWorker("drawing-worker of " + name, self.q2, song_list)
        self.drawing_worker.start()

    def run(self):
        while True:
            sem1.acquire()
            workload = self.queue.get()  # work_type + friend
            work_type = workload['work_type']
            friend = workload['friend']
            user_id = friend['user_id']
            _score = friend["recent_score"][0]
            last_active = 0
            if "time_played" in _score:
                last_active = _score["time_played"]
            table_name = 'scoreTable_' + str(user_id)
            self.create_score_table(table_name)
            self.cursor.execute(f'''
            SELECT * FROM {table_name} ORDER BY potential DESC
            ''')
            rows = self.cursor.fetchall()
            self.cursor.execute('''
            SELECT name FROM sqlite_master WHERE type='table'
            ''')
            tables = [t[0] for t in self.cursor.fetchall()]
            rows_dict = {(row[0], row[1]): row for row in rows}
            priority_queue = []
            song_size = len(self.difficulty_rating)

            if work_type == 'b30':
                for i in range(song_size):
                    b30_low_potential = 0.0 if len(priority_queue) < 33 else priority_queue[0]
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
                        heapq.heappush(priority_queue, rows_dict[(curr_idx, curr_difficulty)][8])
                        print("continue")
                        continue
                    curr_potential = self.update(curr_idx, curr_id, curr_difficulty, user_id, curr_rating, tables)
                    if curr_potential is not None:
                        heapq.heappush(priority_queue, curr_potential)
                    if len(priority_queue) > 33:
                        heapq.heappop(priority_queue)
                self.q2.put(workload)
                sem2.release()
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

            self.conn.commit()

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
            self.cursor.execute(f'''
            INSERT INTO {curr_table_name} (idx, difficulty, title, rating, play_time, time_stamp, score, clear_type, potential)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT (idx,difficulty)
            DO UPDATE SET play_time=excluded.play_time, time_stamp=excluded.time_stamp, score=excluded.score, clear_type=excluded.clear_type,potential=excluded.potential
            ''', (
                idx, difficulty, song_id, rating, item["time_played"], timestamp, score,
                item["best_clear_type"], curr_potential))
        self.conn.commit()
        time.sleep(0.5)
        return potential

    def create_score_table(self, name: str):
        self.cursor.execute(f'''
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
        self.conn.commit()

    @staticmethod
    def count_potential(score: int, rating: str):
        real_rating = float(rating)
        if score >= 10000000:
            ans = real_rating + 2.0
        elif score >= 9800000:
            ans = real_rating + 1.0 + (score - 9800000) / 200000
        else:
            ans = max(0.0, real_rating + (score - 9500000) / 300000)
        return round(ans, 5)


class DrawingWorker(threading.Thread):
    def __init__(self, name: str, q: queue.Queue, song_list: SongList):
        threading.Thread.__init__(self, name=name)
        self.q: queue.Queue = q
        self.song_list = song_list
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        if not os.path.exists(IMG_SAVE_PATH):
            os.mkdir(IMG_SAVE_PATH)

    def run(self):
        while True:
            sem2.acquire()
            workload = self.q.get()
            work_type = workload['work_type']
            friend = workload['friend']
            if work_type == 'b30':
                user_id = friend['user_id']
                user_name = friend['name']
                # todo : can be improved
                self.cursor.execute(f'''SELECT user_code FROM user WHERE user_id = {user_id}''')
                user_code = self.cursor.fetchone()[0]
                rating = friend['rating']
                character_id = friend['character']
                is_uncapped = friend['is_char_uncapped']
                img = self.draw_b30(user_id, user_name, user_code, rating, character_id, is_uncapped)
                file_name = user_name + "_" + str(user_id) + '.png'
                img.save(os.path.join(IMG_SAVE_PATH, file_name))

    def draw_b30(self, user_id: int, user_name: str, user_code: str, rating: int,
                 character_id: int,
                 is_character_uncapped,
                 style='chieri'):
        table_name = 'scoreTable_' + str(user_id)
        self.cursor.execute(f'''SELECT * FROM {table_name} ORDER BY potential DESC LIMIT 33''')
        rows = self.cursor.fetchall()
        if style == 'chieri':
            # 1. create bg
            ans = Image.open(CHIERI_BG_PATH).convert('RGBA')
            # 2. draw b30
            start_x = 108
            start_y = 823
            b30_sum = 0
            b10_sum = 0
            for i in range(min(30, len(rows))):
                single = self.draw_single_b30(rows[i], i + 1)
                potential = rows[i][8]
                b30_sum += potential
                if i < 10:
                    b10_sum += potential
                ans.paste(single, (start_x + 542 * (i % 3), start_y + 314 * (i // 3)), single)
            # 3. draw overflow
            for i in range(30, min(33, len(rows))):
                single = self.draw_single_b30(rows[i], i + 1)
                ans.paste(single, (start_x + 542 * (i % 3), 4010), single)
            # 4. draw diamond
            DIAMOND_PATH = get_diamond_path(self.get_diamond(rating))
            diamond = Image.open(DIAMOND_PATH).convert('RGBA').resize((357, 357))
            ans.alpha_composite(diamond, (127, 136))
            # 5. write user_name
            SansSerifFLF = ImageFont.truetype(SansSerifFLF_PATH, 104)
            draw = ImageDraw.Draw(ans)
            draw.text((462, 209), user_name, (255, 255, 255), SansSerifFLF)
            # 6. write user_code
            SansSerifFLF = ImageFont.truetype(SansSerifFLF_PATH, 61)
            draw.text((455, 326), self.user_code2str(user_code), (255, 255, 255), SansSerifFLF)
            # 7. write rating
            SansSerifFLF = ImageFont.truetype(SansSerifFLF_PATH, 90)
            self.write_boarder(draw, (191, 270), self.rating2str(rating), (255, 255, 255), SansSerifFLF, (98, 8, 98))
            # 8. write b30 and r10
            b30 = b30_sum / 30
            r10 = 4 * (rating / 100 - 0.75 * b30)
            SansSerifFLF = ImageFont.truetype(SansSerifFLF_PATH, 77)
            draw.text((450, 547), format(b30, ".3f"), (255, 255, 255), SansSerifFLF)
            draw.text((450, 637), format(r10, ".3f"), (255, 255, 255), SansSerifFLF)
            # 9. write max_b30
            max_b30 = (b30_sum + b10_sum) / 40
            SansSerifFLF = ImageFont.truetype(SansSerifFLF_PATH, 49)
            draw.text((884, 648), format(max_b30, ".3f"), (255, 255, 255), SansSerifFLF)
            # 10. draw character
            char_name = str(character_id)
            if is_character_uncapped:
                char_name += 'u'
            char_name += '.png'
            char_path = os.path.join(CHARACTER_PATH, char_name)
            if os.path.exists(char_path):
                character = Image.open(char_path).convert('RGBA').resize((684, 684))
                ans.alpha_composite(character, (1154, 119))
            return ans

    def draw_single_b30(self, data_row, index: int, style='chieri'):
        idx = data_row[0]  # example: 87
        id = data_row[2]  # example: fractureray
        difficulty = data_row[1]  # example: 2
        score = data_row[6]
        rating = data_row[3]
        potential = data_row[8]
        play_time = int(data_row[4] / 1000)
        title = self.song_list.get_song_name(idx, difficulty == 3)
        COVER_PATH = get_cover_path(id, difficulty)

        if style == 'chieri':
            # 1. cover process
            cover = Image.open(COVER_PATH).convert('RGBA').resize((241, 241))
            avg_color = self.get_average_color(cover)
            ans = Image.new('RGBA', (501, 241), avg_color)
            gradient = Image.new('L', (241, 1), color=0xFF)
            for x in range(198):
                gradient.putpixel((x, 0), int(255 * (x / 198)))
            gradient = gradient.resize((241, 241))
            cover.putalpha(gradient)
            ans.paste(cover, (260, 0), cover)
            # 2. paste table
            table = Image.open(CHIERI_TABLE_PATH).convert('RGBA')
            ans.paste(table, (0, 0), table)
            # 3. paste diff
            DIFF_PATH = get_diff_path(difficulty)
            diff = Image.open(DIFF_PATH).convert('RGBA')
            ans.paste(diff, (18, 22), diff)
            # 4. paste grade
            GRADE_PATH = get_grade_path(self.get_grade(score))
            grade = Image.open(GRADE_PATH).convert('RGBA').resize((110, 53))
            ans.paste(grade, (48, 157), grade)
            # 5. write title
            roboto_light = ImageFont.truetype(Roboto_Light_PATH, size=37)
            draw = ImageDraw.Draw(ans)
            color = self.choose_text_color(avg_color)
            draw.text((41, 21), title, fill=color, font=roboto_light)
            # 6. write score
            roboto_light = ImageFont.truetype(Roboto_Light_PATH, size=51)
            draw.text((37, 64), self.score2str(score), fill=color, font=roboto_light)
            # 7. write rating
            exo_regular = ImageFont.truetype(Exo_Regular_PATH, size=23)
            draw.text((213, 147), rating, fill=color, font=exo_regular)
            # 8. write potential
            exo_regular = ImageFont.truetype(Exo_Regular_PATH, size=37)
            draw.text((262, 128), '> ' + format(potential, ".2f"), fill=color, font=exo_regular)
            # 9. write time
            exo_regular = ImageFont.truetype(Exo_Regular_PATH, size=21)
            dt_object = datetime.datetime.fromtimestamp(play_time)
            formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            draw.text((213, 204), formatted_time, fill=color, font=exo_regular)
            # 10. write index
            opensans = ImageFont.truetype(OpenSans_Regular_PATH, size=28)
            shadow_color = (98, 8, 98)
            text = '#' + str(index)
            self.write_boarder(draw, (442, 202), text, (255, 255, 255), opensans, shadow_color)
            # 11. apply mask
            mask = Image.open(CHIERI_MASK_PATH).convert('L')
            ans.putalpha(mask)
            return ans

    @staticmethod
    def get_average_color(image: Image.Image):
        pix = image.load()
        R_list = []
        G_list = []
        B_list = []
        width, height = image.size
        for x in range(int(width / 5)):
            for y in range(height):
                R_list.append(pix[x, y][0])
                G_list.append(pix[x, y][1])
                B_list.append(pix[x, y][2])
        R_average = int(average(R_list))
        G_average = int(average(G_list))
        B_average = int(average(B_list))
        return 20 + R_average, 20 + G_average, 20 + B_average

    @staticmethod
    def choose_text_color(background_color: tuple[int, int, int]):
        r, g, b = background_color
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        return (255, 255, 255) if brightness < 128 else (0, 0, 0)

    @staticmethod
    def get_grade(score: int):
        if score >= 9900000:
            return 'ex+'
        elif score >= 9800000:
            return 'ex'
        elif score >= 9500000:
            return 'aa'
        elif score >= 9200000:
            return 'a'
        elif score >= 8900000:
            return 'b'
        elif score >= 8600000:
            return 'c'
        else:
            return 'd'

    @staticmethod
    def get_diamond(rating):
        if not isinstance(rating, int):
            return 'off'
        if rating >= 1300:
            return '7'
        elif rating >= 1250:
            return '6'
        elif rating >= 1200:
            return '5'
        elif rating >= 1100:
            return '4'
        elif rating >= 1000:
            return '3'
        elif rating >= 700:
            return '2'
        elif rating >= 350:
            return '1'
        else:
            return '0'

    @staticmethod
    def score2str(score: int):
        formatted_number = str(score).zfill(8)
        formatted_number = f"{formatted_number[:2]}'{formatted_number[2:5]}'{formatted_number[5:]}"
        return formatted_number

    @staticmethod
    def user_code2str(user_code: str):
        return f"{user_code[:3]} {user_code[3:6]} {user_code[6:]}"

    @staticmethod
    def rating2str(rating: int):
        decimal = rating % 100
        former = rating // 100
        return f"{str(former)}.{str(decimal).zfill(2)}"

    @staticmethod
    def write_boarder(draw: ImageDraw.Draw, pos: tuple[int, int], text, fill, font, shadow_color):
        x, y = pos
        draw.text((x - 2, y - 2), text, fill=shadow_color, font=font)
        draw.text((x + 2, y - 2), text, fill=shadow_color, font=font)
        draw.text((x - 2, y + 2), text, fill=shadow_color, font=font)
        draw.text((x + 2, y + 2), text, fill=shadow_color, font=font)
        draw.text((x - 1, y - 1), text, fill=shadow_color, font=font)
        draw.text((x + 1, y - 1), text, fill=shadow_color, font=font)
        draw.text((x - 1, y + 1), text, fill=shadow_color, font=font)
        draw.text((x + 1, y + 1), text, fill=shadow_color, font=font)
        draw.text((x - 2, y), text, fill=shadow_color, font=font)
        draw.text((x + 2, y), text, fill=shadow_color, font=font)
        draw.text((x, y + 2), text, fill=shadow_color, font=font)
        draw.text((x, y - 2), text, fill=shadow_color, font=font)
        draw.text((x, y), text, fill=fill, font=font)


class WorkerLauncher:
    def __init__(self, song_list: SongList, difficulty_rating: DifficultyRatingList,
                 webapi: WebapiUtils, friend_manager: FriendManager):
        self.q = queue.Queue()
        self.friend_manager = friend_manager
        self.query_worker = QueryWorker("query-worker", self.q, song_list, difficulty_rating, webapi)
        self.query_worker.start()

    async def start_task(self, user_id: int, work_type: str):
        friend = await self.friend_manager.get_friend_info(user_id)
        self.q.put({"work_type": work_type, "friend": friend})
        sem1.release()
