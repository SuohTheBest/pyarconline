import asyncio

from pyarconline import ArcOnlineHelper

helper = ArcOnlineHelper("YOURACCOUNT", "PASSWORD")

asyncio.run(helper.handle_task("Tong274", 'b30'))



# from pyarconline.utils import DifficultyRatingList, SongList
#
# s = SongList("./pyarconline/songlist")
# d = DifficultyRatingList(s)
#
# asyncio.run(d.update_via_wikiwiki())
