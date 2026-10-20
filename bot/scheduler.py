import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from common import db
from common.models import daily_deposit_interest
from common.money import format_money
from common.notify import notify

logger = logging.getLogger(__name__)


async def capitalize_deposits(bot) -> None:
    today = db.today_str()
    to_notify = []
    with db.transaction() as data:
        rate = data["settings"]["deposit_rate_annual"]
        for user in data["users"]:
            if user["deposit"] <= 0:
                continue
            if user.get("deposit_last_capitalized_at") == today:
                continue
            interest = round(daily_deposit_interest(user["deposit"], rate), 2)
            if interest <= 0:
                continue
            user["deposit"] = round(user["deposit"] + interest, 2)
            user["deposit_interest_accrued"] = round(user.get("deposit_interest_accrued", 0.0) + interest, 2)
            user["deposit_last_capitalized_at"] = today
            db.add_transaction(
                data, "deposit_interest", interest, to_id=user["tg_id"],
                description="Капитализация процентов по вкладу",
            )
            to_notify.append((user["tg_id"], interest, user["deposit"]))

    for tg_id, interest, new_deposit in to_notify:
        await notify(
            bot, tg_id,
            f"💎 Начислено {format_money(interest)} процентов по вкладу.\n"
            f"Новый размер вклада: {format_money(new_deposit)}.",
        )


def setup_scheduler(application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def job():
        try:
            await capitalize_deposits(application.bot)
        except Exception:
            logger.exception("capitalize_deposits job failed")

    # Daily at 00:05 UTC. Idempotent (guarded by deposit_last_capitalized_at),
    # so a missed/duplicate run or a restart mid-day is harmless.
    scheduler.add_job(job, CronTrigger(hour=0, minute=5))
    scheduler.start()
    return scheduler
