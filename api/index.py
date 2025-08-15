import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

# Vercelのサーバーレス環境では、非同期モードに`threading`を使用します
async_mode = "threading"

app = Flask(__name__, template_folder='../templates', static_folder='../static')
# NOTE: 秘密鍵は環境変数から読み込むのがベストプラクティスです
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-very-secret-key')
socketio = SocketIO(app, async_mode=async_mode)

# --- 重要 ---
# Vercelはステートレスな環境です。つまり、リクエストごとにサーバーの状態がリセットされる可能性があります。
# そのため、`rooms`変数はリクエストをまたいでデータを保持できません。
# 本番環境では、RedisやFirestoreのような外部データベースを使用して部屋の状態を永続化する必要があります。
# このサンプルコードは、ローカルでのテストやコンセプト実証用です。
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
    # room.htmlを返すだけ。実際のゲームロジックはSocketIOで処理
    return render_template('room.html')

# --- SocketIOイベントハンドラ ---

@socketio.on('join')
def on_join(data):
    room_id = data['room']
    player_name = data['name']
    player_id = request.sid

    # 部屋が存在しない場合は作成
    if room_id not in rooms:
        rooms[room_id] = {
            'id': room_id,
            'host_id': player_id,
            'state': 'waiting',
            'players': [],
            'settings': {'wolf_count': 1, 'topic': 'food'}
        }
    
    room = rooms[room_id]
    
    # プレイヤーを部屋に追加
    player = {
        'id': player_id,
        'name': player_name,
    }
    room['players'].append(player)
    
    join_room(room_id)
    print(f"Player {player_name} ({player_id}) joined room {room_id}")
    
    # 部屋の全員に更新情報を送信
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

    # プレイヤーが3人未満、または人狼の数が不適切な場合はエラー
    if len(players) < 3 or wolf_count >= len(players):
        emit('error', {'message': 'Invalid player or wolf count.'})
        return

    # 役職の割り当て
    roles = ['wolf'] * wolf_count + ['citizen'] * (len(players) - wolf_count)
    random.shuffle(roles)

    # お題の選択
    topic_key = settings.get('topic', 'food')
    word_pair = random.choice(TOPICS.get(topic_key, TOPICS['food']))
    random.shuffle(word_pair)
    citizen_word, wolf_word = word_pair

    # 各プレイヤーに役職とお題を割り当て
    for i, player in enumerate(players):
        player['role'] = roles[i]
        player['word'] = wolf_word if roles[i] == 'wolf' else citizen_word

    room['state'] = 'role_assignment'
    emit('room_update', room, to=room_id)

@socketio.on('disconnect')
def on_disconnect():
    player_id = request.sid
    room_to_update = None
    
    # プレイヤーがどの部屋にいたかを探す
    for room_id, room in rooms.items():
        if any(p['id'] == player_id for p in room['players']):
            room['players'] = [p for p in room['players'] if p['id'] != player_id]
            room_to_update = room
            
            # ホストが退出した場合、新しいホストを任命
            if room['host_id'] == player_id and room['players']:
                room['host_id'] = room['players'][0]['id']
            
            break
            
    if room_to_update:
        # 部屋が空になったら削除
        if not room_to_update['players']:
            del rooms[room_to_update['id']]
            print(f"Room {room_to_update['id']} is empty and has been closed.")
        else:
            emit('room_update', room_to_update, to=room_to_update['id'])
            print(f"Player {player_id} disconnected. Room {room_to_update['id']} updated.")

# Flaskアプリのエントリーポイント
if __name__ == '__main__':
    socketio.run(app, debug=True)
