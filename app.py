import os
import time
import uuid
import threading
import requests
from flask import Flask

# =====================================================================
# CONFIGURATION
# Pulling sensitive values from Environment Variables (or filling below)
# =====================================================================
ACCESS_TOKEN = os.environ.get("GROUPME_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
GROUP_ID = os.environ.get("GROUP_ID", "YOUR_GROUP_ID_HERE")
TRIGGER_USER_ID = os.environ.get("TRIGGER_USER_ID", "TARGET_USER_ID_HERE")

# Put your two exact, case-sensitive phrases here:
TRIGGER_PHRASES = [
    "Music mMondays",
    "Music mWednesdays"
]

POLL_INTERVAL = 1.5  # Seconds between checks (1.5s avoids GroupMe rate limits)
# =====================================================================

app = Flask(__name__)

@app.route("/")
def home():
    # Your ping bot will hit this URL to keep the Render service awake
    return "Bot is alive and monitoring!", 200

def get_latest_message():
    """Fetches only the 1 most recent message from the GroupMe group."""
    url = f"https://api.groupme.com/v3/groups/{GROUP_ID}/messages"
    params = {
        "token": ACCESS_TOKEN,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            messages = response.json()["response"]["messages"]
            if messages:
                return messages[0]
    except Exception as e:
        print(f"Error checking messages: {e}")
    return None

def send_user_message(text):
    """Sends a message directly from your personal GroupMe user account."""
    url = f"https://api.groupme.com/v3/groups/{GROUP_ID}/messages"
    params = {"token": ACCESS_TOKEN}
    
    # GroupMe requires a unique source_guid for every user message to prevent
    # duplicate sends if your internet hiccups. uuid.uuid4() makes a unique ID.
    payload = {
        "message": {
            "source_guid": str(uuid.uuid4()),
            "text": text
        }
    }
    try:
        response = requests.post(url, params=params, json=payload, timeout=5)
        if response.status_code == 201:
            print(f"Successfully sent: '{text}'")
        else:
            print(f"Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending message: {e}")

def poll_groupme():
    """Background loop that checks the chat every 1.5 seconds."""
    print("Starting GroupMe listener...")
    last_seen_id = None

    # Grab the latest message right when the bot starts so we don't
    # accidentally reply to an old message that was already in the chat.
    initial_msg = get_latest_message()
    if initial_msg:
        last_seen_id = initial_msg["id"]
        print(f"Initialized! Ignoring messages up to ID: {last_seen_id}")

    while True:
        time.sleep(POLL_INTERVAL)
        msg = get_latest_message()

        if not msg:
            continue

        msg_id = msg["id"]

        # Only inspect this message if we haven't seen its ID yet
        if msg_id != last_seen_id:
            last_seen_id = msg_id
            sender_id = str(msg.get("user_id", ""))
            text = msg.get("text") or ""  # Handle image-only messages where text is None

            # 1. Check if the sender is our specific [trigger_user]
            if sender_id == str(TRIGGER_USER_ID):
                # 2. Check if either of our 2 phrases is inside the message (case-sensitive)
                for phrase in TRIGGER_PHRASES:
                    if phrase in text:
                        print(f"Match detected from {msg.get('name')}: '{phrase}' found in '{text}'")
                        time.sleep(10)
                        send_user_message(phrase)
                        # Note: If both phrases are in the same message, this sends both.
                        # Add 'break' right below this line if you only want it to send one!
                        break

# Start the GroupMe polling loop in a background thread so Flask can run simultaneously
listener_thread = threading.Thread(target=poll_groupme, daemon=True)
listener_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)