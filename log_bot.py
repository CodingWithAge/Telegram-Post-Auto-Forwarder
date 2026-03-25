import requests

class TelegramLogBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_log(self, message: str):
        data = {
            'chat_id': self.chat_id,
            'text': message
        }
        try:
            response = requests.post(self.api_url, data=data)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send log message: {e}")
