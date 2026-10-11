import asyncio
from datetime import datetime, time, timedelta
import zoneinfo
import logging

from backend.database import AsyncSessionLocal
from backend.dao.user import UserDAO
from backend.dao.application import ApplicationDAO
from backend.services.sms import sms_service
from backend.meta import UserRole

logger = logging.getLogger(__name__)
IST = zoneinfo.ZoneInfo("Asia/Kolkata")


async def run_weekly_alerts_job() -> int:
    """Fetch all active official users and send pending/objected stats via SMS."""
    sent_count = 0
    print("[Weekly Authority Alerts Cron] Starting alerts dispatch...")
    async with AsyncSessionLocal() as session:
        try:
            user_dao = UserDAO()
            app_dao = ApplicationDAO(session)

            # 1. Fetch all active official users (not CITIZEN)
            all_users = await user_dao.get_users_filtered(session, is_citizen=False)
            active_officials = [u for u in all_users if u.is_active]
            print(f"[Weekly Authority Alerts Cron] Found {len(active_officials)} active official users.")

            for user in active_officials:
                # Skip roles that do not have actionable workflow queues
                if user.role in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.NAKA_INCHARGE):
                    continue

                try:
                    stats = await app_dao.get_authority_pending_stats(user.role)
                    pending = stats.get("pending", 0)
                    objected = stats.get("objected", 0)
                    over15days = stats.get("over15days", 0)

                    # Trigger SMS only if user has anything pending or objected
                    if pending > 0 or objected > 0:
                        success = await sms_service.send_weekly_alert_sms(
                            mobile=user.mobile,
                            name=user.name,
                            pending=pending,
                            objected=objected,
                            over15days=over15days,
                        )
                        if success:
                            sent_count += 1
                            print(f"[Weekly Authority Alerts Cron] Sent alert SMS to {user.name} ({user.mobile}).")
                        else:
                            print(f"[Weekly Authority Alerts Cron] Failed to send SMS to {user.name} ({user.mobile}).")
                except Exception as user_err:
                    print(f"[Weekly Authority Alerts Cron] Error processing alerts for user {user.name} ({user.role}): {user_err}")

            print(f"[Weekly Authority Alerts Cron] Completed. Total alert messages sent: {sent_count}.")
        except Exception as e:
            print(f"[Weekly Authority Alerts Cron] Unexpected error during job execution: {e}")

    return sent_count


def get_next_weekly_alert_time(now_ist: datetime) -> datetime:
    """
    Calculate the next occurrence of Tuesday or Thursday at 10:00 AM IST.
    Tuesday is weekday 1, Thursday is weekday 3.
    """
    for days_ahead in range(8):
        candidate_date = now_ist.date() + timedelta(days=days_ahead)
        if candidate_date.weekday() in (1, 3):  # Tuesday or Thursday
            candidate_dt = datetime.combine(candidate_date, time(hour=10, minute=0), tzinfo=IST)
            if candidate_dt > now_ist:
                return candidate_dt

    # Fallback default
    return datetime.combine(now_ist.date() + timedelta(days=1), time(hour=10, minute=0), tzinfo=IST)


async def schedule_weekly_authority_alerts():
    """Runs indefinitely, triggering run_weekly_alerts_job every Tuesday and Thursday at 10:00 AM IST."""
    while True:
        try:
            now_ist = datetime.now(IST)
            target_run = get_next_weekly_alert_time(now_ist)

            wait_seconds = (target_run - now_ist).total_seconds()
            print(
                f"[Weekly Authority Alerts Cron] Next run scheduled at "
                f"{target_run.strftime('%Y-%m-%d %A %H:%M:%S %Z')} (in {wait_seconds:.1f}s)"
            )

            await asyncio.sleep(wait_seconds)
            await run_weekly_alerts_job()
        except asyncio.CancelledError:
            print("[Weekly Authority Alerts Cron] Scheduler task cancelled.")
            break
        except Exception as e:
            print(f"[Weekly Authority Alerts Cron] Unexpected scheduler error: {e}")
            await asyncio.sleep(60)
