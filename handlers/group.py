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

    async def _get_user_display(self, user_id: int) -> str:
        result = await self._call_api("get_stranger_info", {"user_id": user_id})
        data = result.get("data")
        if data and data.get("nickname"):
            nickname = data["nickname"]
            return f"{nickname}（{user_id}）"
        return str(user_id)

    async def handle_notice(self, notice: dict):
        notice_type = notice.get("notice_type")
        if notice_type == "group_increase":
            await self._handle_group_increase(notice)
        elif notice_type == "group_decrease":
            await self._handle_group_decrease(notice)

    async def _handle_group_increase(self, notice: dict):
        if not config.get("welcome_enabled"):
            return

        group_id = notice.get("group_id")
        user_id = notice.get("user_id")
        user_display = await self._get_user_display(user_id)

        welcome_msg = config.get("welcome_message")
        welcome_msg = welcome_msg.replace("{user_name}", user_display)

        image_path = config.get("welcome_image")
        if image_path:
            full_msg = f"{welcome_msg}\n[CQ:image,file={image_path}]"
        else:
            full_msg = welcome_msg

        logger.info(f"群 {group_id} 新成员 {user_display} 加入，发送欢迎消息")
        await self.send_group_msg(group_id, full_msg)

    async def _handle_group_decrease(self, notice: dict):
        if not config.get("notify_leave_enabled"):
            return

        sub_type = notice.get("sub_type")
        group_id = notice.get("group_id")
        user_id = notice.get("user_id")

        if sub_type == "leave":
            msg_template = config.get("notify_leave_message")
            logger.info(f"群 {group_id} 成员 {user_id} 主动退群")
        elif sub_type == "kick":
            msg_template = config.get("notify_kick_message")
            operator_id = notice.get("operator_id")
            logger.info(f"群 {group_id} 成员 {user_id} 被 {operator_id} 踢出")
        elif sub_type == "kick_me":
            logger.warning(f"机器人已被踢出群 {group_id}")
            return
        else:
            return

        user_display = await self._get_user_display(user_id)
        msg = msg_template.replace("{user_name}", user_display)
        await self.send_group_msg(group_id, msg)
