import logging
import re

from config import config

logger = logging.getLogger("BankHandler")


class BankHandler:
    def __init__(self, coin_handler=None):
        self.coin_handler = coin_handler

    def get_user_data(self, user_id: int) -> dict:
        user = self.coin_handler.get_user_data(user_id)
        if "debt" not in user:
            user["debt"] = 0
        if "max_debt" not in user:
            user["max_debt"] = config.get("bank_max_loan", 1000)
        return user

    def get_debt(self, user_id: int) -> int:
        return self.get_user_data(user_id).get("debt", 0)

    def get_max_debt(self, user_id: int) -> int:
        return self.get_user_data(user_id).get("max_debt", config.get("bank_max_loan", 1000))

    async def handle_loan(self, group_id: int, user_id: int, amount_str: str):
        if not config.get("bank_enabled", True):
            return

        try:
            amount = int(amount_str)
        except ValueError:
            await self.coin_handler.send_group_msg(group_id, "格式不对哦，请输入：借款<金额>，比如：借款100")
            return

        if amount <= 0:
            await self.coin_handler.send_group_msg(group_id, "金额必须大于0哦")
            return

        user = self.get_user_data(user_id)
        user_display = await self.coin_handler.get_user_display(user_id)
        current_debt = user.get("debt", 0)
        max_debt = user.get("max_debt", config.get("bank_max_loan", 1000))

        if current_debt + amount > max_debt:
            remaining = max_debt - current_debt
            await self.coin_handler.send_group_msg(
                group_id,
                f"{user_display} 你的借款额度上限是{max_debt}金币，还能再借{remaining}金币"
            )
            return

        user["debt"] = current_debt + amount
        user["coins"] = user.get("coins", 0) + amount
        self.coin_handler._save_data()

        logger.info(f"借款: {user_display} 借款{amount}金币 (负债{user['debt']})")
        await self.coin_handler.send_group_msg(
            group_id,
            f"{user_display} 借款成功，+{amount}金币，当前负债：{user['debt']}金币，当前金币：{user['coins']}"
        )

    async def handle_repay(self, group_id: int, user_id: int, amount_str: str):
        if not config.get("bank_enabled", True):
            return

        try:
            amount = int(amount_str)
        except ValueError:
            await self.coin_handler.send_group_msg(group_id, "格式不对哦，请输入：还款<金额>，比如：还款100")
            return

        if amount <= 0:
            await self.coin_handler.send_group_msg(group_id, "金额必须大于0哦")
            return

        user = self.get_user_data(user_id)
        user_display = await self.coin_handler.get_user_display(user_id)
        coins = user.get("coins", 0)
        debt = user.get("debt", 0)

        if debt <= 0:
            await self.coin_handler.send_group_msg(group_id, f"{user_display} 你没有欠款哦")
            return

        if amount > coins:
            await self.coin_handler.send_group_msg(
                group_id,
                f"{user_display} 你只有{coins}金币，不够还{amount}金币"
            )
            return

        actual_repay = min(amount, debt)
        user["coins"] = coins - actual_repay
        user["debt"] = debt - actual_repay
        self.coin_handler._save_data()

        logger.info(f"还款: {user_display} 还款{actual_repay}金币 (剩余负债{user['debt']})")
        await self.coin_handler.send_group_msg(
            group_id,
            f"{user_display} 还款成功，-{actual_repay}金币，当前金币：{user['coins']}，剩余负债：{user['debt']}金币"
        )

    async def handle_help(self, group_id: int):
        lines = [
            "📋 可用命令：",
            f"   {'签到':<10} → 领取每日随机金币",
            f"   {'借款<金额>':<10} → 从银行借钱，如：借款100",
            f"   {'还款<金额>':<10} → 还给银行钱，如：还款100",
            f"   {'/help 或 帮助':<10} → 显示本帮助菜单",
        ]
        await self.coin_handler.send_group_msg(group_id, "\n".join(lines))