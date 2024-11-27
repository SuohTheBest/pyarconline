from pyarconline import ArcOnlineHelper
from flask import Flask, request, jsonify, send_file

helper = ArcOnlineHelper("ACCOUNT", "PASSWORD")
app = Flask(__name__)


@app.route('/api/b30', methods=['GET'])
async def b30_pic():
    try:
        username = request.args.get('username')
        json_only = request.args.get('jsonOnly', default=False)
        ans = await helper.handle_task(username, 'b30', json_only=json_only)
        if json_only:
            return jsonify(ans)
        else:
            return send_file(ans, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)

# import asyncio
# from pyarconline.config import SONGLIST_PATH
# from pyarconline.utils import DifficultyRatingList, SongList
#
# s = SongList(SONGLIST_PATH)
# d = DifficultyRatingList(s)
#
# asyncio.run(d.update_via_wikiwiki())
