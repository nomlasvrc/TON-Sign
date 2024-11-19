import asyncio
import socket
import time
from pythonosc.udp_client import SimpleUDPClient
import websockets
import json

def IsBool(value): # 不要かも
    if value == "true" or value == "True" or value == True:
        return True
    else:
        return False
    
def clamp_color(value):
    if (value > 255):
        value = 255
    if (value < 0):
        value = 0
    return value
    
def color(display_color, hexType: bool):
    color_r = clamp_color(int(display_color / 65536))
    color_g = clamp_color(int(display_color % 65536 / 256))
    color_b = clamp_color(int(display_color % 256))
    if hexType:
        return f"#{color_r:0=2x}{color_g:0=2x}{color_b:0=2x}"
    else:
        return f"\033[38;2;{color_r};{color_g};{color_b}m"

def XSOverlayNotification(NotificationMessage):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    msg = {
    "messageType": 1,
    "index": 0,
    "title": NotificationMessage,
    "content": "",
    "height": 120.0,
    "sourceApp": "ToN WebSocket",
    "timeout": 6.0,
    "volume": 0.1,
    "audioPath": "default",
    "useBase64Icon": False,
    "icon": "default",
    "opacity": 1.0
    }
    msgdata = json.dumps(msg)
    byte = msgdata.encode()
    sock.sendto(byte, ("127.0.0.1", 42069))   
    sock.close()

# ---ToNSign用関数

def classify_round(round_type_number):
    exempt_rounds = {100, 101, 102, 103}
    special_rounds = {2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 51, 52, 53, 105, 107}
    classic_rounds = {1, 104}
    
    if round_type_number in exempt_rounds:
        return "Exempt"
    elif round_type_number in special_rounds:
        return "特殊"
    elif round_type_number in classic_rounds:
        return "クラシック"
    else:
        return None

def update_round_log(round_log, round_type_number):
    classification = classify_round(round_type_number)
    
    if classification == "Exempt":
        if len(round_log) >= 2:
            if round_log[-2:] == ["クラシック", "クラシック"]:
                classification = "特殊"
            elif round_log[-2:] == ["クラシック", "特殊"]:
                classification = "クラシック"
            elif round_log[-2:] == ["特殊", "クラシック"]:
                classification = "クラシック"
    
    round_log.append(classification)
    
    if len(round_log) > 7:
        round_log.pop(0)

def predict_next_round(round_log):
    if len(round_log) < 2:
        return "クラシック"
    
    if round_log[-2:] == ["特殊", "特殊"]:
        print("ホストは去った. 訂正！\n===================")
        round_log.pop()

    return "特殊" if round_log[-2:] == ["クラシック", "クラシック"] else "特殊かクラシック" if round_log[-2:] == ["特殊", "クラシック"] else "クラシック"

def get_recent_rounds_log(round_log):
    return ', '.join(['X' if round_type == "クラシック" else 'O' for round_type in round_log])

# ---

def show_message(message, round_log, osc_client):
    colorful = True
    xsoverlay = False
    show_player_notification = True

    RESET = '\033[0m'
    try:
        data = json.loads(message)
        type = data.get("Type")
        match type:
            case "CONNECTED":
                display_name = data.get("DisplayName")
                user_id = data.get("UserID")
                args = data.get("Args", [])
                print(f"Hello, {display_name}さん！")

            case "TERRORS":
                command = data.get("Command")
                names = data.get("Names", [])
                display_name = data.get("DisplayName")
                display_color = data.get("DisplayColor")
                if names != None:
                    m = "テラー:"
                    n = "テラー:"
                    for i in range(len(names)):
                        if i == 0:
                            if colorful:
                                m += f" {color(display_color, False)}{names[i]}{RESET}"
                                n += f" <color={color(display_color, True)}>{names[i]}</color>"
                            else:
                                m += f" {names[i]}"
                                n += f" {names[i]}"
                        else:
                            m += f", {names[i]}"
                            n += f", {names[i]}"
                    print(m)
                    if xsoverlay:
                        XSOverlayNotification(n)

            case "ROUND_TYPE":
                command = data.get("Command")
                value = data.get("Value")
                name = data.get("Name")
                display_name = data.get("DisplayName")
                display_color = data.get("DisplayColor")

                possible_round_type_number = value
                round_type = display_name
                if command == 0:
                    print(f"ラウンド終了")
                elif command == 1:
                    # ラウンド開始
                    update_round_log(round_log, possible_round_type_number)
                    if colorful:
                        print(f"~ 新しいラウンドが始まった！ ~\n~ ラウンドの種類は: {color(display_color, False)}{round_type}{RESET} ~\n")
                    else:
                        print(f"~ 新しいラウンドが始まった！ ~\n~ ラウンドの種類は: {round_type} ~\n")
                    prediction = predict_next_round(round_log)
                    recent_rounds_log = get_recent_rounds_log(round_log)

                    print(f"(最近の試合: {recent_rounds_log})\n ~ 次の試合は: {prediction}\n===================\n次の試合を待っている... :3")

                    # Send OSC message
                    if prediction == "特殊":
                        osc_client.send_message("/avatar/parameters/TON_Sign_Sp", True)
                        osc_client.send_message("/avatar/parameters/TON_Sign_Cl", False)
                    elif prediction == "特殊かクラシック":
                        osc_client.send_message("/avatar/parameters/TON_Sign_Sp", True)
                        osc_client.send_message("/avatar/parameters/TON_Sign_Cl", True)
                    else:
                        osc_client.send_message("/avatar/parameters/TON_Sign_Sp", False)
                        osc_client.send_message("/avatar/parameters/TON_Sign_Cl", True)
                else:
                    print(f"(未定義エラー)ラウンドコマンド: {command}")

            case "PLAYER_JOIN":
                player_name = data.get("Value")
                if show_player_notification:
                    print(f"[Join] { player_name}")

            case "PLAYER_LEAVE":
                player_name = data.get("Value")
                if show_player_notification:
                    print(f"[Leave] {player_name}")

            case "MASTER_CHANGE":
                print("***\n*** ホストが去った、次回は特殊ラウンドとなる。\n***")
                osc_client.send_message("/avatar/parameters/TON_Sign_Sp", True)
                osc_client.send_message("/avatar/parameters/TON_Sign_Cl", False)
        return round_log

    except json.JSONDecodeError:
        print("JSON解析エラー")
        print(message)
        return []

async def main():

    # OSC setup
    ip = "127.0.0.1"
    port = 9000
    osc_client = SimpleUDPClient(ip, port)

    uri = "ws://localhost:11398"
    async with websockets.connect(uri) as websocket:
        round_log = []
        while True:
            round_log = show_message(await websocket.recv(), round_log, osc_client)

try:
    print("ToNSaveManagerに接続中...")
    asyncio.run(main())
except ConnectionRefusedError as e:
    print()
    print(e)
    print()
    print("接続拒否エラーが発生しました。ToNSaveManagerが起動していることを確認してください。")
    print("5秒後に終了します...")
    time.sleep(5)
except websockets.exceptions.ConnectionClosedError as e:
    print()
    print(e)
    print()
    print("切断されました。")
    print("5秒後に終了します...")
    time.sleep(5)
except KeyboardInterrupt as e:
    print(e)
    print("終了中...")
    exit()

#こんにちは、コーダー仲間！ <3 :3/
