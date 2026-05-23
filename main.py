import asyncio
import json
import logging
import sys

import websockets
from websockets.server import WebServerSocketProtocol

from config import config
from handlers.group import GroupHandler
from handlers.coin import CoinHandler
from web.server import WebManager, LogHandler

logger = logging.getLogger("QQBot")


def setup_logging():
    log_level = getattr(logging, config.get("log_level", "INFO").upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root_logger.addHandler(console_handler)

    web_log_handler = LogHandler()
    web_log_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(web_log_handler)


class QQBot:
    def __init__(self):
        self.napcat_connected = False
        self.group_handler = GroupHandler()
        self.coin_handler = CoinHandler()
        self.web_manager = WebManager(bot=self)

    async def start(self):
        await self.group_handler.start()
        await self.coin_handler.start()

        web_host = config.get("web_host", "0.0.0.0")
        web_port = config.get("web_port", 9090)
        await self.web_manager.start(web_host, web_port)

        ws_host = config.get("ws_host")
        ws_port = config.get("ws_port")
        logger.info(f"正在启动 WebSocket 服务器 ws://{ws_host}:{ws_port}")
        logger.info("请确保 napcat 的 反向WebSocket 配置已指向此地址")
        logger.info(f"   napcat 配置地址: ws://{ws_host}:{ws_port}/")

        async def handler(websocket: WebServerSocketProtocol):
            client_info = f"{websocket.remote_address}"
            self.napcat_connected = True
            logger.info(f"napcat 已连接: {client_info}")
            try:
                async for raw in websocket:
                    await self._on_message(raw)
            except websockets.ConnectionClosed:
                logger.warning(f"napcat 连接断开: {client_info}")
            except Exception as e:
                logger.error(f"连接异常 ({client_info}): {e}")
            finally:
                self.napcat_connected = False

        async with websockets.serve(handler, ws_host, ws_port):
            logger.info(f"WebSocket 服务器已启动，等待 napcat 连接...")
            await asyncio.Future()

    async def _on_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"收到非法 JSON: {raw}")
            return

        post_type = data.get("post_type")

        if post_type == "notice":
            await self.group_handler.handle_notice(data)

        elif post_type == "message":
            await self._handle_message(data)

        elif post_type == "meta_event":
            if data.get("meta_event_type") == "lifecycle":
                logger.info("napcat 连接生命周期事件")

    async def _handle_message(self, msg: dict):
        if not config.get("coin_enabled", True):
            return

        msg_type = msg.get("message_type")
        if msg_type != "group":
            return

        raw_text = (msg.get("raw_message") or "").strip()
        if not raw_text:
            return

        group_id = msg.get("group_id")
        user_id = msg.get("user_id")

        if raw_text == "签到":
            await self.coin_handler.handle_checkin(group_id, user_id)

    async def stop(self):
        await self.web_manager.stop()
        await self.coin_handler.stop()
        await self.group_handler.stop()
        logger.info("机器人已停止")


async def main():
    setup_logging()
    logger.info(f"QQBot 启动中...")
    logger.info(f"机器人名称: {config.get('bot_name')}")
    logger.info(f"入群欢迎: {'已开启' if config.get('welcome_enabled') else '已关闭'}")

    bot = QQBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
