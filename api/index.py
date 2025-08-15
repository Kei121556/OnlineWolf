from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import hashlib
import random
import time

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = 'a-very-secret-key-for-wordwolf'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

rooms = {}

# (ここに以前のバージョンからtopics_jaとtopics_enの全データをコピー)
topics_ja = {
    "food": [["カレー", "シチュー"], ["うどん", "そば"], ["ビール", "発泡酒"], ["りんご", "なし"], ["マカロン", "トゥンカロン"], ["寿司", "刺身"], ["コーヒー", "紅茶"], ["ステーキ", "ハンバーグ"], ["パスタ", "ピザ"], ["パンケーキ", "ワッフル"], ["チョコレート", "キャラメル"], ["チーズ", "バター"]],
    "places": [["東京タワー", "スカイツリー"], ["ディズニーランド", "ディズニーシー"], ["金閣寺", "銀閣寺"], ["海", "川"], ["コンビニ", "スーパー"], ["山", "火山"], ["学校", "病院"], ["博物館", "美術館"], ["空港", "駅"], ["公園", "庭園"], ["図書館", "本屋"], ["カフェ", "レストラン"]],
    "people": [["俳優", "声優"], ["サンタクロース", "トナカイ"], ["先生", "生徒"], ["王様", "大統領"], ["科学者", "発明家"], ["芸術家", "音楽家"], ["シェフ", "パティシエ"], ["スポーツ選手", "コーチ"], ["探偵", "警察官"], ["YouTuber", "配信者"], ["パイロット", "宇宙飛行士"], ["農家", "庭師"]],
    "actions": [["ランニング", "ジョギング"], ["料理", "食事"], ["睡眠", "昼寝"], ["勉強", "仕事"], ["拍手", "手拍子"], ["歌", "ダンス"], ["読書", "執筆"], ["描画", "絵画"], ["笑う", "泣く"], ["歩く", "ハイキング"], ["押す", "引く"], ["投げる", "キャッチする"]],
    "things": [["スマホ", "携帯電話"], ["シャンプー", "リンス"], ["パソコン", "ノートパソコン"], ["鉛筆", "シャーペン"], ["傘", "日傘"], ["椅子", "ソファ"], ["本", "雑誌"], ["鍵", "錠"], ["腕時計", "時計"], ["メガネ", "サングラス"], ["スプーン", "フォーク"], ["タオル", "毛布"]],
    "sports": [["サッカー", "フットサル"], ["野球", "ソフトボール"], ["テニス", "バドミントン"], ["卓球", "ピンポン"], ["水泳", "飛び込み"], ["スキー", "スノーボード"], ["バスケットボール", "バレーボール"], ["柔道", "空手"], ["ゴルフ", "ボウリング"], ["ボクシング", "レスリング"], ["スケートボード", "サーフィン"], ["アーチェリー", "ダーツ"]],
    "entertainment": [["映画", "ドラマ"], ["漫画", "アニメ"], ["演劇", "ミュージカル"], ["YouTube", "TikTok"], ["コンサート", "フェス"], ["喜劇", "悲劇"], ["ラジオ", "ポッドキャスト"], ["サーカス", "マジックショー"], ["バレエ", "オペラ"], ["テレビゲーム", "アーケードゲーム"], ["小説", "詩"], ["彫刻", "絵画"]],
    "animals": [["犬", "猫"], ["ライオン", "トラ"], ["イルカ", "クジラ"], ["ハムスター", "モルモット"], ["馬", "シマウマ"], ["ニワトリ", "アヒル"], ["ヘビ", "トカゲ"], ["蝶", "蛾"], ["クモ", "サソリ"], ["うさぎ", "野うさぎ"], ["ペンギン", "ダチョウ"], ["カエル", "ヒキガエル"]],
    "nature": [["太陽", "月"], ["山", "丘"], ["春", "秋"], ["雷", "稲妻"], ["雲", "霧"], ["雨", "雪"], ["風", "そよ風"], ["星", "惑星"], ["森", "ジャングル"], ["砂漠", "オアシス"], ["川", "湖"], ["火山", "間欠泉"]],
    "tech": [["AI", "ロボット"], ["インターネット", "イントラネット"], ["VR", "AR"], ["プログラミング", "コーディング"], ["ドローン", "ヘリコプター"], ["Eメール", "手紙"], ["ヘッドホン", "イヤホン"], ["カメラ", "ビデオカメラ"], ["プリンター", "スキャナー"], ["タブレット", "電子書籍リーダー"], ["マウス", "キーボード"], ["バッテリー", "充電器"]],
    "fantasy": [["魔法使い", "魔女"], ["ドラゴン", "ワイバーン"], ["エルフ", "ドワーフ"], ["勇者", "魔王"], ["幽霊", "ゾンビ"], ["天使", "悪魔"], ["ユニコーン", "ペガサス"], ["吸血鬼", "狼男"], ["人魚", "セイレーン"], ["妖精", "ゴブリン"], ["フェニックス", "グリフィン"], ["ポーション", "呪文"]],
    "games": [["マリオ", "ルイージ"], ["ファイナルファンタジー", "ドラゴンクエスト"], ["パズル", "クイズ"], ["ボードゲーム", "カードゲーム"], ["ポケモン", "デジモン"], ["マインクラフト", "ロブロックス"], ["チェス", "将棋"], ["鬼ごっこ", "かくれんぼ"], ["ポーカー", "ブラックジャック"], ["ビリヤード", "ダーツ"], ["モノポリー", "スクラブル"], ["テトリス", "パックマン"]],
    "history": [["ローマ", "ギリシャ"], ["騎士", "侍"], ["ピラミッド", "スフィンクス"], ["第一次世界大戦", "第二次世界大戦"], ["ルネサンス", "産業革命"], ["城", "要塞"], ["バイキング", "海賊"], ["恐竜", "マンモス"], ["王", "皇帝"], ["革命", "反乱"], ["ナポレオン", "カエサル"], ["クレオパトラ", "ジャンヌ・ダルク"]],
    "jobs": [["医者", "看護師"], ["警察官", "消防士"], ["パン屋", "パティシエ"], ["パイロット", "客室乗務員"], ["弁護士", "検察官"], ["作家", "ジャーナリスト"], ["デザイナー", "建築家"], ["農家", "漁師"], ["歌手", "ダンサー"], ["エンジニア", "整備士"], ["写真家", "ビデオグラファー"], ["司書", "学芸員"]],
    "colors": [["赤", "ピンク"], ["黒", "紺"], ["金", "銀"], ["オレンジ", "茶色"], ["緑", "黄緑"], ["青", "水色"], ["紫", "ラベンダー"], ["白", "アイボリー"], ["灰色", "チャコール"], ["ベージュ", "クリーム色"], ["ターコイズ", "ティール"], ["マゼンタ", "フューシャ"]],
    "uk": [["ビッグ・ベン", "ロンドン塔"], ["バッキンガム宮殿", "ウィンザー城"], ["サッカー", "ラグビー"], ["フィッシュ・アンド・チップス", "シェパーズパイ"], ["ビートルズ", "ローリング・ストーンズ"], ["シャーロック・ホームズ", "ジェームズ・ボンド"], ["紅茶", "アフタヌーンティー"], ["イングランド", "スコットランド"], ["庶民院", "貴族院"], ["ハリー・ポッター", "指輪物語"], ["クイーン", "オアシス"], ["ウィンブルドン", "全英オープン"], ["ストーンヘンジ", "ハドリアヌスの長城"], ["大英博物館", "ナショナル・ギャラリー"], ["タワーブリッジ", "ロンドン橋"], ["エディンバラ城", "カーディフ城"], ["ロンドン", "マンチェスター"], ["スコーン", "クランペット"], ["ジン", "ウィスキー"], ["王子", "王女"], ["二階建てバス", "ブラックキャブ"], ["アーサー王", "ロビン・フッド"], ["テムズ川", "セヴァーン川"], ["ロンドン・アイ", "ザ・シャード"], ["チェダーチーズ", "スティルトンチーズ"], ["赤い電話ボックス", "赤い郵便ポスト"], ["シェイクスピア", "チャールズ・ディケンズ"], ["オックスフォード大学", "ケンブリッジ大学"], ["パディントン", "くまのプーさん"], ["ジャファケーキ", "ダイジェスティブビスケット"], ["ユニオンジャック", "イングランドの旗"], ["スコットランドの旗", "ウェールズの旗"], ["北アイルランドの旗", "アイルランドの旗"], ["エリザベス女王", "ヴィクトリア女王"], ["イングリッシュ・ブレックファスト", "サンデーロースト"], ["クリケット", "ポロ"], ["エド・シーラン", "アデル"], ["チャーチル", "サッチャー"], ["ブライトン", "ダラム"], ["湖水地方", "スコットランド高地"], ["コッツウォルズ", "コーンウォール"], ["国会議事堂", "ダウニング街10番地"], ["ウェンブリー・スタジアム", "トゥイッケナム・スタジアム"], ["セブン・シスターズ", "ドーバーの白い崖"]]
}
topics_en = {
    "food": [["Curry", "Stew"], ["Udon", "Soba"], ["Beer", "Low-malt Beer"], ["Apple", "Pear"], ["Macaron", "Fatcaron"], ["Sushi", "Sashimi"], ["Coffee", "Tea"], ["Steak", "Hamburger"], ["Pasta", "Pizza"], ["Pancake", "Waffle"], ["Chocolate", "Caramel"], ["Cheese", "Butter"]],
    "places": [["Tokyo Tower", "Skytree"], ["Disneyland", "DisneySea"], ["Kinkaku-ji", "Ginkaku-ji"], ["Ocean", "River"], ["Convenience Store", "Supermarket"], ["Mountain", "Volcano"], ["School", "Hospital"], ["Museum", "Art Gallery"], ["Airport", "Train Station"], ["Park", "Garden"], ["Library", "Bookstore"], ["Cafe", "Restaurant"]],
    "people": [["Actor", "Voice Actor"], ["Santa Claus", "Reindeer"], ["Teacher", "Student"], ["King", "President"], ["Scientist", "Inventor"], ["Artist", "Musician"], ["Chef", "Pâtissier"], ["Athlete", "Coach"], ["Detective", "Police Officer"], ["YouTuber", "Streamer"], ["Pilot", "Astronaut"], ["Farmer", "Gardener"]],
    "actions": [["Running", "Jogging"], ["Cooking", "Eating"], ["Sleeping", "Napping"], ["Studying", "Working"], ["Clapping", "Hand clapping"], ["Singing", "Dancing"], ["Reading", "Writing"], ["Drawing", "Painting"], ["Laughing", "Crying"], ["Walking", "Hiking"], ["Push", "Pull"], ["Throw", "Catch"]],
    "things": [["Smartphone", "Cellphone"], ["Shampoo", "Conditioner"], ["PC", "Laptop"], ["Pencil", "Mechanical Pencil"], ["Umbrella", "Parasol"], ["Chair", "Sofa"], ["Book", "Magazine"], ["Key", "Lock"], ["Watch", "Clock"], ["Glasses", "Sunglasses"], ["Spoon", "Fork"], ["Towel", "Blanket"]],
    "sports": [["Soccer", "Futsal"], ["Baseball", "Softball"], ["Tennis", "Badminton"], ["Table Tennis", "Ping-Pong"], ["Swimming", "Diving"], ["Skiing", "Snowboarding"], ["Basketball", "Volleyball"], ["Judo", "Karate"], ["Golf", "Bowling"], ["Boxing", "Wrestling"], ["Skateboarding", "Surfing"], ["Archery", "Darts"]],
    "entertainment": [["Movie", "Drama"], ["Manga", "Anime"], ["Theater", "Musical"], ["YouTube", "TikTok"], ["Concert", "Festival"], ["Comedy", "Tragedy"], ["Radio", "Podcast"], ["Circus", "Magic Show"], ["Ballet", "Opera"], ["Video Game", "Arcade Game"], ["Novel", "Poem"], ["Sculpture", "Painting"]],
    "animals": [["Dog", "Cat"], ["Lion", "Tiger"], ["Dolphin", "Whale"], ["Hamster", "Guinea Pig"], ["Horse", "Zebra"], ["Chicken", "Duck"], ["Snake", "Lizard"], ["Butterfly", "Moth"], ["Spider", "Scorpion"], ["Rabbit", "Hare"], ["Penguin", "Ostrich"], ["Frog", "Toad"]],
    "nature": [["Sun", "Moon"], ["Mountain", "Hill"], ["Spring", "Autumn"], ["Thunder", "Lightning"], ["Cloud", "Fog"], ["Rain", "Snow"], ["Wind", "Breeze"], ["Star", "Planet"], ["Forest", "Jungle"], ["Desert", "Oasis"], ["River", "Lake"], ["Volcano", "Geyser"]],
    "tech": [["AI", "Robot"], ["Internet", "Intranet"], ["VR", "AR"], ["Programming", "Coding"], ["Drone", "Helicopter"], ["Email", "Letter"], ["Headphones", "Earphones"], ["Camera", "Video Camera"], ["Printer", "Scanner"], ["Tablet", "e-Reader"], ["Mouse", "Keyboard"], ["Battery", "Charger"]],
    "fantasy": [["Wizard", "Witch"], ["Dragon", "Wyvern"], ["Elf", "Dwarf"], ["Hero", "Demon Lord"], ["Ghost", "Zombie"], ["Angel", "Demon"], ["Unicorn", "Pegasus"], ["Vampire", "Werewolf"], ["Mermaid", "Siren"], ["Fairy", "Goblin"], ["Phoenix", "Griffin"], ["Potion", "Spell"]],
    "games": [["Mario", "Luigi"], ["Final Fantasy", "Dragon Quest"], ["Puzzle", "Quiz"], ["Board Game", "Card Game"], ["Pokémon", "Digimon"], ["Minecraft", "Roblox"], ["Chess", "Shogi"], ["Tag", "Hide-and-seek"], ["Poker", "Blackjack"], ["Billiards", "Darts"], ["Monopoly", "Scrabble"], ["Tetris", "Pac-Man"]],
    "history": [["Rome", "Greece"], ["Knight", "Samurai"], ["Pyramid", "Sphinx"], ["World War I", "World War II"], ["Renaissance", "Industrial Revolution"], ["Castle", "Fortress"], ["Viking", "Pirate"], ["Dinosaur", "Mammoth"], ["King", "Emperor"], ["Revolution", "Rebellion"], ["Napoleon", "Caesar"], ["Cleopatra", "Joan of Arc"]],
    "jobs": [["Doctor", "Nurse"], ["Police Officer", "Firefighter"], ["Baker", "Pâtissier"], ["Pilot", "Cabin Attendant"], ["Lawyer", "Prosecutor"], ["Writer", "Journalist"], ["Designer", "Architect"], ["Farmer", "Fisherman"], ["Singer", "Dancer"], ["Engineer", "Mechanic"], ["Photographer", "Videographer"], ["Librarian", "Curator"]],
    "colors": [["Red", "Pink"], ["Black", "Navy"], ["Gold", "Silver"], ["Orange", "Brown"], ["Green", "Lime"], ["Blue", "Sky Blue"], ["Purple", "Lavender"], ["White", "Ivory"], ["Gray", "Charcoal"], ["Beige", "Cream"], ["Turquoise", "Teal"], ["Magenta", "Fuchsia"]],
    "uk": [["Big Ben", "Tower of London"], ["Buckingham Palace", "Windsor Castle"], ["Football", "Rugby"], ["Fish and Chips", "Shepherd's Pie"], ["The Beatles", "The Rolling Stones"], ["Sherlock Holmes", "James Bond"], ["Tea", "Afternoon Tea"], ["England", "Scotland"], ["House of Commons", "House of Lords"], ["Harry Potter", "The Lord of the Rings"], ["Queen", "Oasis"], ["Wimbledon", "The Open Championship"], ["Stonehenge", "Hadrian's Wall"], ["The British Museum", "The National Gallery"], ["Tower Bridge", "London Bridge"], ["Edinburgh Castle", "Cardiff Castle"], ["London", "Manchester"], ["Scone", "Crumpet"], ["Gin", "Whisky"], ["Prince", "Princess"], ["Double-decker bus", "Black cab"], ["King Arthur", "Robin Hood"], ["Thames River", "River Severn"], ["London Eye", "The Shard"], ["Cheddar cheese", "Stilton cheese"], ["Red telephone box", "Red post box"], ["Shakespeare", "Charles Dickens"], ["Oxford University", "Cambridge University"], ["Paddington Bear", "Winnie-the-Pooh"], ["Jaffa Cakes", "Digestive Biscuits"], ["Union Jack", "Flag of England"], ["Flag of Scotland", "Flag of Wales"], ["Flag of Northern Ireland", "Flag of Ireland"], ["Queen Elizabeth", "Queen Victoria"], ["English Breakfast", "Sunday Roast"], ["Cricket", "Polo"], ["Ed Sheeran", "Adele"], ["Churchill", "Thatcher"], ["Brighton", "Durham"], ["Lake District", "Scottish Highlands"], ["Cotswolds", "Cornwall"], ["Houses of Parliament", "10 Downing Street"], ["Wembley Stadium", "Twickenham Stadium"], ["Seven Sisters", "White Cliffs of Dover"]]
}

def generate_room_id():
    while True:
        seed = str(time.time()) + 'wolf_secret_salt'
        room_id = hashlib.sha256(seed.encode()).hexdigest()[:6].upper()
        if room_id not in rooms:
            return room_id

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/room/<room_id>')
def room_page(room_id):
    return app.send_static_file('room.html')


@socketio.on('create_room')
def handle_create_room(data):
    player_name = data.get('name')
    room_id = generate_room_id()
    
    rooms[room_id] = {
        'host_sid': request.sid,
        'players': [{ 'sid': request.sid, 'name': player_name, 'is_host': True }],
        'game_state': {
            'status': 'waiting',
            'settings': None,
            'game_data': None
        }
    }
    join_room(room_id)
    emit('room_created', {'room_id': room_id})

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id', '').upper()
    player_name = data.get('name')

    if room_id not in rooms:
        emit('error', {'message': 'Room not found.'})
        return

    if any(p['sid'] == request.sid for p in rooms[room_id]['players']):
        pass
    else:
        rooms[room_id]['players'].append({ 'sid': request.sid, 'name': player_name, 'is_host': False })
    
    join_room(room_id)
    
    player_list = [{'name': p['name'], 'is_host': p.get('is_host', False)} for p in rooms[room_id]['players']]
    emit('update_player_list', {'players': player_list}, room=room_id)
    emit('joined_room', {'room_id': room_id})

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id')
    if room_id not in rooms or rooms[room_id]['host_sid'] != request.sid:
        return

    settings = data.get('settings')
    rooms[room_id]['game_state']['settings'] = settings
    rooms[room_id]['game_state']['status'] = 'playing'
    
    players = rooms[room_id]['players']
    player_count = len(players)
    wolf_count = int(settings['wolfCount'])
    
    roles = ['wolf'] * wolf_count + ['citizen'] * (player_count - wolf_count)
    random.shuffle(roles)
    
    lang = settings['lang']
    topic_key = settings['topic']
    
    if lang == 'ja':
        word_pairs = topics_ja.get(topic_key, topics_ja['food'])
    else:
        word_pairs = topics_en.get(topic_key, topics_en['food'])
    
    word_pair = random.choice(word_pairs)
    citizen_word, wolf_word = word_pair[0], word_pair[1]

    for i, player in enumerate(players):
        player['role'] = roles[i]
        player['word'] = wolf_word if roles[i] == 'wolf' else citizen_word
        emit('your_role_is', {'role': player['role'], 'word': player['word']}, room=player['sid'])

    rooms[room_id]['game_state']['game_data'] = {
        'citizen_word': citizen_word,
        'wolf_word': wolf_word
    }
    
    player_list = [{'name': p['name'], 'is_host': p.get('is_host', False)} for p in players]
    emit('game_started', {'players': player_list}, room=room_id)


@socketio.on('disconnect')
def handle_disconnect():
    sid_to_remove = request.sid
    room_to_update = None
    
    for room_id, room_data in list(rooms.items()):
        if any(p['sid'] == sid_to_remove for p in room_data['players']):
            room_to_update = room_id
            room_data['players'] = [p for p in room_data['players'] if p['sid'] != sid_to_remove]
            
            if not room_data['players']:
                del rooms[room_id]
                print(f"Room {room_id} deleted.")
                break
            
            if room_data['host_sid'] == sid_to_remove:
                new_host = room_data['players'][0]
                new_host['is_host'] = True
                room_data['host_sid'] = new_host['sid']
                print(f"New host for room {room_id} is {new_host['name']}")

            player_list = [{'name': p['name'], 'is_host': p.get('is_host', False)} for p in room_data['players']]
            emit('update_player_list', {'players': player_list}, room=room_to_update)
            break

# Vercelで実行するためのエントリーポイント
handler = app
