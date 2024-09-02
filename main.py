import asyncio

from pyarconline import ArcOnlineHelper

helper = ArcOnlineHelper("stbtestaccount", "fuckyou237313")

asyncio.run(helper.handle_task("SparklingFurina", 'b30'))



# from pyarconline.utils import DifficultyRatingList, SongList
#
# s = SongList("./pyarconline/songlist")
# d = DifficultyRatingList(s)
#
# asyncio.run(d.update_via_wikiwiki())
