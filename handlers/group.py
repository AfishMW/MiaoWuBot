import logging
import aiohttp
from config import config

logger = logging.getLogger("GroupHandler")


class GroupHandler:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def stop(self):
        if self.session:
            await self.session.close()

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

    async def handle_notice(self, notice: dict):
        notice_type = notice.get("notice_type")
        if notice_type == "group_increase":
            await self._handle_group_increase(notice)

    async def _handle_group_increase(self, notice: dict):
        if not config.get("welcome_enabled"):
            return

        group_id = notice.get("group_id")
        user_id = notice.get("user_id")

        welcome_msg = config.get("welcome_message")
        welcome_msg = welcome_msg.replace("{user_name}", f"[CQ:at,qq={user_id}]")

        image_path = config.get("welcome_image")
        if image_path:
            full_msg = f"{welcome_msg}\n[CQ:image,file={image_path}]"
        else:
            full_msg = welcome_msg

        logger.info(f"群 {group_id} 新成员 {user_id} 加入，发送欢迎消息")
        await self.send_group_msg(group_id, full_msg)
