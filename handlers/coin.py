import json
import logging
import random
import time
from datetime import date
from pathlib import Path

import aiohttp
from config import config

logger = logging.getLogger("CoinHandler")

COINS_FILE = Path(__file__).parent.parent / "coins.json"


class CoinHandler:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._data = self._load_data()

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def stop(self):
        if self.session:
            await self.session.close()
        self._save_data()

    def _load_data(self) -> dict:
        if COINS_FILE.exists():
            try:
                with open(COINS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("coins.json 解析失败，使用空数据")
        return {"users": {}}

    def _save_data(self):
        COINS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COINS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _get_api_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        token = config.get("api_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _call_api(self, action: str, params: dict = None) -> dict:
        api_url = config.api_url
        url = f"{api_url}/{action}"
        payload = params or {}
        try:
            async with self.session.post(url, json=payload, headers=self._get_api_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                result = await resp.json()
                logger.debug(f"API {action} 响应: {result}")
                return result
        except Exception as e:
            logger.error(f"调用 API {action} 失败: {e}")
            return {"status": "failed", "retcode": -1}

    async def send_group_msg(self, group_id: int, message: str):
        return await self._call_api("send_group_msg", {
            "group_id": group_id,
            "message": message
        })

    async def get_user_display(self, user_id: int) -> str:
        result = await self._call_api("get_stranger_info", {"user_id": user_id})
        data = result.get("data")
        if data and data.get("nickname"):
            return f"{data['nickname']}（{user_id}）"
        return str(user_id)

    def get_user_data(self, user_id: int) -> dict:
        uid = str(user_id)
        if uid not in self._data["users"]:
            self._data["users"][uid] = {"coins": 0, "last_checkin": ""}
        return self._data["users"][uid]

    def has_checked_in_today(self, user_id: int) -> bool:
        uid = str(user_id)
        user = self.get_user_data(user_id)
        return user.get("last_checkin") == str(date.today())

    def get_coins(self, user_id: int) -> int:
        return self.get_user_data(user_id).get("coins", 0)

    def add_coins(self, user_id: int, amount: int):
        user = self.get_user_data(user_id)
        user["coins"] = user.get("coins", 0) + amount
        self._save_data()

    def do_checkin(self, user_id: int) -> dict:
        min_coins = config.get("coin_checkin_min", 1)
        max_coins = config.get("coin_checkin_max", 100)
        amount = random.randint(min_coins, max_coins)
        user = self.get_user_data(user_id)
        user["coins"] = user.get("coins", 0) + amount
        user["last_checkin"] = str(date.today())
        self._save_data()
        return {"amount": amount, "total": user["coins"]}

    async def handle_checkin(self, group_id: int, user_id: int):
        if self.has_checked_in_today(user_id):
            user = self.get_user_data(user_id)
            await self.send_group_msg(
                group_id,
                f"你今天已经签到过了，当前金币：{user['coins']}"
            )
            return

        result = self.do_checkin(user_id)
        user_display = await self.get_user_display(user_id)
        reply = f"{user_display} 签到成功，+{result['amount']}金币，当前金币：{result['total']}"

        logger.info(f"签到: {user_display} +{result['amount']}金币 (共{result['total']})")
        await self.send_group_msg(group_id, reply)