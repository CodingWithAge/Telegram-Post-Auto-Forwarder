import os
from dotenv import load_dotenv
load_dotenv()
LOG_BOT_API_TOKEN = os.getenv("LOG_BOT_API_TOKEN", "<LOG_BOT_TOKEN_HERE>")
LOG_BOT_TARGET_CHAT_ID = os.getenv("LOG_BOT_TARGET_CHAT_ID", "<LOG_BOT_CHAT_ID_HERE>")
from cryptography.fernet import Fernet
import json
import os


KEY_FILE = 'secret.key'
CONFIG_FILE_TEMPLATE = 'config_{user_id}.enc'

def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)

def load_key():
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Encryption key not found. Run the bot to generate it.")
    with open(KEY_FILE, 'rb') as f:
        return f.read()

def save_config(data):
    user_id = data.get('_user_id')
    if not user_id:
        raise ValueError('User ID required in data for per-user config.')
    key = load_key()
    fernet = Fernet(key)
    enc = fernet.encrypt(json.dumps(data).encode())
    config_file = CONFIG_FILE_TEMPLATE.format(user_id=user_id)
    with open(config_file, 'wb') as f:
        f.write(enc)

def load_config(user_id=None):
    if not user_id:
        raise ValueError('User ID required for per-user config.')
    key = load_key()
    fernet = Fernet(key)
    config_file = CONFIG_FILE_TEMPLATE.format(user_id=user_id)
    if not os.path.exists(config_file):
        raise FileNotFoundError("Config file not found. Run the bot to create it.")
    with open(config_file, 'rb') as f:
        enc = f.read()
    return json.loads(fernet.decrypt(enc).decode())