import os
import glob
import time
from pythonosc.udp_client import SimpleUDPClient

def find_latest_log(directory):
    log_files = glob.glob(os.path.join(directory, "*.txt"))
    if not log_files:
        print("No log files found.")
        return None
    
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"VRChat Log: {latest_log}\nOK! ToNの試合が表示されるはずだ！ ^^\n===================")
    return latest_log

def classify_round(round_type):
    exempt_rounds = {"ミスティックムーン", "トワイライト", "ソルスティス", "Mystic Moon", "Twilight", "Solstice"}
    special_rounds = {"霧", "パニッシュ", "サボタージュ", "狂気", "オルタネイト", "ブラッドバス", "ミッドナイト", "8ページ", "アンバウンド", "ゴースト", "ダブル・トラブル", "Fog", "Punished", "Sabotage", "Cracked", "Alternate", "Bloodbath", "Midnight", "8 Pages", "Unbound", "Ghost", "Double Trouble"}
    classic_rounds = {"クラシック", "ブラッドムーン", "Classic", "Blood Moon"}
    
    if round_type in exempt_rounds:
        return "Exempt"
    elif round_type in special_rounds:
        return "特殊"
    elif round_type in classic_rounds:
        return "クラシック"
    else:
        return None

def update_round_log(round_log, round_type):
    classification = classify_round(round_type)
    
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

def monitor_round_types(log_file, known_round_types, osc_client):
    round_log = []
    last_position = 0

    while True:
        with open(log_file, 'r', encoding='utf-8') as file:
            file.seek(last_position)
            lines = file.readlines()
            new_position = file.tell()

            for line in lines:
                if "OnMasterClientSwitched" in line:
                    print("***\n*** ホストが去った、次回は特殊ラウンドとなる。\n***")
                    osc_client.send_message("/avatar/parameters/TON_Sign", True)

                if "Round type is" in line:
                    parts = line.split("Round type is")
                    if len(parts) > 1:
                        possible_round_type = parts[1].strip().split()[0:2]
                        possible_round_type = " ".join(possible_round_type)

                        if possible_round_type in known_round_types:
                            update_round_log(round_log, possible_round_type)
                            print(f"~ 新しいラウンドが始まった！ ~\n~ ラウンドの種類は: {possible_round_type} ~\n")
                            
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
            
            last_position = new_position

        time.sleep(10)

# OSC setup
ip = "127.0.0.1"
port = 9000
osc_client = SimpleUDPClient(ip, port)

# Current round types in game
round_types = [
    'クラシック', '霧', 'パニッシュ', 'サボタージュ', '狂気', 'オルタネイト',
    'ブラッドバス', 'ミッドナイト', 'ミスティックムーン', 'トワイライト', 'ソルスティス', 
    '8ページ', 'ブラッドムーン', 'アンバウンド', 'ゴースト', 'ダブル・トラブル',

    'Classic', 'Fog', 'Punished', 'Sabotage', 'Cracked', 'Alternate',
    'Bloodbath', 'Midnight', 'Mystic Moon', 'Twilight', 'Solstice', 
    '8 Pages', 'Blood Moon', 'Unbound', 'Ghost', 'ダブル・トラブル'
]

# Directory and file search UPDATED becuase some people's getlogin function EXPLODED so we're doing it this way now :3
log_directory = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "VRChat", "VRChat")
latest_log_file = find_latest_log(log_directory)

if latest_log_file:
    monitor_round_types(latest_log_file, round_types, osc_client)
    
#こんにちは、コーダー仲間！ <3 :3/
