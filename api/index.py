import os
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

# Vercelのサーバーレス環境では、非同期モードに`threading`を使用します
async_mode = "threading"

# --- ↓↓↓ ここが修正点です！ ↓↓↓ ---
# プロジェクトのルートディレクトリを基準に、templateとstaticフォルダの絶対パスを指定します。
# これにより、Vercel環境でも確実にファイルを見つけられるようになります。
app = Flask(__name__, template_folder='../templates', static_folder='../static')
# --- ↑↑↑ 修正点はここまで ↑↑↑ ---

# NOTE: 秘密鍵は環境変数から読み込むのがベストプラクティスです
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-very-secret-key')
socketio = SocketIO(app, async_mode=async_mode)

rooms = {}

# --- お題データ ---
TOPICS = {
    "food": [["Curry", "Stew"], ["Sushi", "Sashimi"], ["Coffee", "Tea"]],
    "places": [["Tokyo Tower", "Skytree"], ["Ocean", "River"], ["School", "Hospital"]],
    "actions": [["Running", "Jogging"], ["Cooking", "Eating"], ["Sleeping", "Napping"]]
}

# --- ルーティング ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/room/<string:room_id>')
def room(room_id):
    return render_template('room.html')

# --- SocketIOイベントハンドラ ---
# (join, update_settings, start_game, disconnectなどの関数は変更なし)
@socketio.on('join')
def on_join(data):
    room_id = data['room']
    player_name = data['name']
    player_id = request.sid

    if room_id not in rooms:
        rooms[room_id] = {
            'id': room_id,
            'host_id': player_id,
            'state': 'waiting',
            'players': [],
            'settings': {'wolf_count': 1, 'topic': 'food'}
        }
    
    room = rooms[room_id]
    
    player = { 'id': player_id, 'name': player_name }
    room['players'].append(player)
    
    join_room(room_id)
    print(f"Player {player_name} ({player_id}) joined room {room_id}")
    emit('room_update', room, to=room_id)

@socketio.on('update_settings')
def on_update_settings(data):
    room_id = data['room']
    if room_id in rooms and request.sid == rooms[room_id]['host_id']:
        rooms[room_id]['settings'].update(data['settings'])
        emit('room_update', rooms[room_id], to=room_id)

@socketio.on('start_game')
def on_start_game(data):
    room_id = data['room']
    room = rooms.get(room_id)

    if not room or request.sid != room['host_id']:
        return

    players = room['players']
    settings = room['settings']
    wolf_count = int(settings.get('wolf_count', 1))

    if len(players) < 3 or wolf_count >= len(players):
        emit('error', {'message': 'Invalid player or wolf count.'})
        return

    roles = ['wolf'] * wolf_count + ['citizen'] * (len(players) - wolf_count)
    random.shuffle(roles)

    topic_key = settings.get('topic', 'food')
    word_pair = random.choice(TOPICS.get(topic_key, TOPICS['food']))
    random.shuffle(word_pair)
    citizen_word, wolf_word = word_pair

    for i, player in enumerate(players):
        player['role'] = roles[i]
        player['word'] = wolf_word if roles[i] == 'wolf' else citizen_word

    room['state'] = 'role_assignment'
    emit('room_update', room, to=room_id)

@socketio.on('disconnect')
def on_disconnect():
    player_id = request.sid
    room_to_update = None
    
    for room_id, room in list(rooms.items()): # Iterate over a copy
        if any(p['id'] == player_id for p in room['players']):
            room['players'] = [p for p in room['players'] if p['id'] != player_id]
            
            if not room['players']:
                del rooms[room_id]
                print(f"Room {room_id} is empty and has been closed.")
                return

            if room['host_id'] == player_id:
                room['host_id'] = room['players'][0]['id']
            
            emit('room_update', room, to=room_id)
            print(f"Player {player_id} disconnected. Room {room_id} updated.")
            break

# Flaskアプリのエントリーポイント
if __name__ == '__main__':
    socketio.run(app, debug=True)
