import asyncio
import logging
import time
from pathlib import Path

from aiohttp import web

from config import config

logger = logging.getLogger("WebManager")

STATIC_DIR = Path(__file__).parent / "static"

LOG_RECORDS = []
MAX_LOG_RECORDS = 500


class LogHandler(logging.Handler):
    def emit(self, record):
        entry = {
            "time": time.strftime("%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        LOG_RECORDS.append(entry)
        if len(LOG_RECORDS) > MAX_LOG_RECORDS:
            LOG_RECORDS.pop(0)


class WebManager:
    def __init__(self, bot=None):
        self.bot = bot
        self.app = web.Application()
        self.runner = None
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/api/status", self._handle_status)
        self.app.router.add_get("/api/config", self._handle_get_config)
        self.app.router.add_put("/api/config", self._handle_update_config)
        self.app.router.add_get("/api/logs", self._handle_get_logs)
        self.app.router.add_get("/api/coin-ranking", self._handle_coin_ranking)
        self.app.router.add_get("/api/bank-ranking", self._handle_bank_ranking)
        self.app.router.add_post("/api/test-welcome", self._handle_test_welcome)
        self.app.router.add_static("/", path=STATIC_DIR, name="static", show_index=True)

    async def _handle_status(self, request):
        return web.json_response({
            "bot_name": config.get("bot_name"),
            "running": True,
            "welcome_enabled": config.get("welcome_enabled"),
            "notify_leave_enabled": config.get("notify_leave_enabled"),
            "coin_enabled": config.get("coin_enabled"),
            "bank_enabled": config.get("bank_enabled"),
            "ws_port": config.get("ws_port"),
            "api_port": config.get("api_port"),
            "napcat_connected": getattr(self.bot, "napcat_connected", False) if self.bot else False,
        })

    async def _handle_get_config(self, request):
        safe_keys = [
            "ws_host", "ws_port", "api_host", "api_port",
            "bot_name", "welcome_enabled", "welcome_message",
            "welcome_image", "notify_leave_enabled", "notify_leave_message",
            "notify_kick_message", "coin_enabled", "coin_checkin_min",
            "coin_checkin_max", "bank_enabled", "bank_max_loan",
            "admin_qq", "log_level",
        ]
        result = {k: config.get(k) for k in safe_keys}
        return web.json_response(result)

    async def _handle_update_config(self, request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "无效的 JSON"}, status=400)

        allowed = {
            "ws_host", "ws_port", "api_host", "api_port",
            "api_token", "bot_name", "welcome_enabled",
            "welcome_message", "welcome_image",
            "notify_leave_enabled", "notify_leave_message", "notify_kick_message",
            "coin_enabled", "coin_checkin_min", "coin_checkin_max",
            "bank_enabled", "bank_max_loan", "admin_qq",
            "log_level",
        }
        updated = []
        for key, value in body.items():
            if key in allowed:
                if key in ("ws_port", "api_port", "coin_checkin_min", "coin_checkin_max", "bank_max_loan"):
                    value = int(value)
                elif key in ("welcome_enabled", "notify_leave_enabled", "coin_enabled", "bank_enabled"):
                    value = bool(value)
                config.set(key, value)
                updated.append(key)

        logger.info(f"配置已更新: {', '.join(updated)}")
        return web.json_response({"updated": updated})

    async def _handle_get_logs(self, request):
        level = request.query.get("level", "").upper()
        search = request.query.get("search", "").lower()
        logs = LOG_RECORDS
        if level:
            logs = [r for r in logs if r["level"] == level]
        if search:
            logs = [r for r in logs if search in r["message"].lower()]
        return web.json_response(logs[-200:])

    async def _handle_coin_ranking(self, request):
        if not self.bot or not self.bot.coin_handler:
            return web.json_response({"error": "机器人未就绪"}, status=503)
        coin_handler = self.bot.coin_handler
        users = coin_handler._data.get("users", {})
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("coins", 0), reverse=True)
        ranking = [
            {"user_id": uid, "coins": info.get("coins", 0), "last_checkin": info.get("last_checkin", "")}
            for uid, info in sorted_users[:50]
        ]
        return web.json_response(ranking)

    async def _handle_bank_ranking(self, request):
        if not self.bot or not self.bot.coin_handler:
            return web.json_response({"error": "机器人未就绪"}, status=503)
        coin_handler = self.bot.coin_handler
        users = coin_handler._data.get("users", {})
        sorted_users = sorted(
            [(uid, info) for uid, info in users.items() if info.get("debt", 0) > 0],
            key=lambda x: x[1].get("debt", 0), reverse=True
        )
        ranking = [
            {"user_id": uid, "debt": info.get("debt", 0), "coins": info.get("coins", 0)}
            for uid, info in sorted_users[:50]
        ]
        return web.json_response(ranking)

    async def _handle_test_welcome(self, request):
        if not self.bot or not self.bot.group_handler:
            return web.json_response({"error": "机器人未就绪"}, status=503)
        try:
            body = await request.json()
            group_id = int(body.get("group_id", 0))
        except Exception:
            return web.json_response({"error": "参数无效"}, status=400)
        if group_id <= 0:
            return web.json_response({"error": "请填写有效的群号"}, status=400)

        welcome_msg = config.get("welcome_message")
        welcome_msg = welcome_msg.replace("{user_name}", "测试用户（123456）")
        image_path = config.get("welcome_image")
        if image_path:
            full_msg = f"{welcome_msg}\n[CQ:image,file={image_path}]"
        else:
            full_msg = welcome_msg

        result = await self.bot.group_handler.send_group_msg(group_id, full_msg)
        if result.get("status") == "failed":
            return web.json_response({"error": "发送失败，请检查群号是否正确"}, status=502)
        logger.info(f"网页管理 - 测试发送欢迎消息到群 {group_id}")
        return web.json_response({"success": True, "group_id": group_id})

    async def start(self, host="0.0.0.0", port=9090):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        logger.info(f"网页管理后台: http://{host}:{port}")
        logger.info(f"  本地访问: http://127.0.0.1:{port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
