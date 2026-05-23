import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ws_host": "0.0.0.0",
    "ws_port": 8080,
    "api_host": "127.0.0.1",
    "api_port": 3000,
    "api_token": "",
    "bot_name": "小助手",
    "welcome_enabled": True,
    "welcome_message": "欢迎新群友 {user_name} 加入本群！请先阅读群公告，祝您玩得开心~",
    "welcome_image": "",
    "log_level": "INFO",
    "web_host": "0.0.0.0",
    "web_port": 9090,
}


class Config:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = dict(DEFAULT_CONFIG)
            self.save()

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, DEFAULT_CONFIG.get(key, default))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def ws_url(self) -> str:
        return f"ws://{self.get('ws_host')}:{self.get('ws_port')}"

    @property
    def api_url(self) -> str:
        return f"http://{self.get('api_host')}:{self.get('api_port')}"


config = Config()
