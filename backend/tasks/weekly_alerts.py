import asyncio
from datetime import datetime, time, timedelta
from typing import Optional
import zoneinfo
import logging

from sqlalchemy import select, and_

from backend.database import AsyncSessionLocal
from backend.dao.user import UserDAO
from backend.dao.application import ApplicationDAO, _APPLICATION_LOAD_OPTIONS, _get_app_last_updated_at
from backend.dbmodels.application import Application
from backend.services.sms import sms_service
from backend.meta import (
    UserRole,
    ApplicationFlags,
    ApplicationStatus,
    ObjectionStatus,
    ApplicationType,
)

logger = logging.getLogger(__name__)
IST = zoneinfo.ZoneInfo("Asia/Kolkata")


def compute_authority_user_stats(
    app_dao: ApplicationDAO,
    user,
    applications: list[Application],
    now: datetime,
) -> dict[str, int]:
    """
    Compute pending, objected, and over 15 days counts for a specific official user
    using the exact same ApplicationFlags logic evaluated by the UI.
    """
    pending = 0
    objected = 0
    over15days = 0

    for app in applications:
        # If user has a specific jurisdiction zone assigned (e.g. ULB or UIT), match it
        if getattr(user, "jurisdiction_zone", None) and app.jurisdiction_zone != user.jurisdiction_zone:
            continue

        flags = app_dao.get_required_flags(app, user.role)
        if ApplicationFlags.PENDING_WITH_ME not in flags:
            continue

        start_ts: Optional[datetime] = None
        if app.status == ApplicationStatus.OBJECTED:
            objected += 1
            pending_objs = [
                o
                for o in getattr(app, "objections", [])
                if o.status == ObjectionStatus.PENDING
                and (
                    o.objected_to_role == user.role
                    or (not o.objected_to_role and user.role == UserRole.CITIZEN)
                )
            ]
            if pending_objs:
                start_ts = min([o.created_at for o in pending_objs if o.created_at])
            else:
                start_ts = _get_app_last_updated_at(app)
        else:
            pending += 1
            if user.role in (UserRole.NODAL_OFFICER, UserRole.SUPERADMIN):
                if app.type == ApplicationType.NEW and app.status == ApplicationStatus.SUBMITTED:
                    start_ts = app.created_at
                elif app_dao.is_pending_token_generation(app):
                    phases = sorted(app.phases, key=lambda p: p.phase) if getattr(app, "phases", None) else []
                    if phases and phases[-1].completed_at:
                        start_ts = phases[-1].completed_at
                    else:
                        insp_ts = [i.inspected_at for i in getattr(app, "inspections", []) if i.inspected_at]
                        start_ts = max(insp_ts) if insp_ts else _get_app_last_updated_at(app)
                else:
                    start_ts = _get_app_last_updated_at(app)
            elif user.role == UserRole.COMMISSIONER:
                if app.type == ApplicationType.RENOVATION and app.status == ApplicationStatus.SUBMITTED:
                    start_ts = app.created_at
                else:
                    start_ts = _get_app_last_updated_at(app)
            else:
                start_ts = _get_app_last_updated_at(app)

        if start_ts and (now - start_ts).days > 15:
            over15days += 1

    return {
        "pending": pending,
        "objected": objected,
        "over15days": over15days,
    }


async def run_weekly_alerts_job() -> int:
    """Fetch all active official users and send pending/objected stats via SMS using UI application flags."""
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

            # 2. Fetch all candidate applications once
            try:
                query = select(Application).options(*_APPLICATION_LOAD_OPTIONS).where(
                    and_(
                        Application.status != ApplicationStatus.PENDING,
                        Application.status != ApplicationStatus.WITHDRAWN,
                        Application.status != ApplicationStatus.REJECTED,
                    )
                )
                raw_scalars = await session.scalars(query)
                if hasattr(raw_scalars, "unique"):
                    res = raw_scalars.unique()
                    if hasattr(res, "__await__"):
                        res = await res
                    all_applications = list(res.all()) if hasattr(res, "all") else []
                else:
                    all_applications = []
            except Exception as query_err:
                print(f"[Weekly Authority Alerts Cron] Error fetching applications: {query_err}")
                all_applications = []
            now = datetime.now()

            for user in active_officials:
                # Skip roles that do not have actionable workflow queues
                if user.role in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.NAKA_INCHARGE):
                    continue

                if not user.mobile:
                    continue

                try:
                    stats = compute_authority_user_stats(app_dao, user, all_applications, now)
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
                            print(
                                f"[Weekly Authority Alerts Cron] Sent alert SMS to {user.name} ({user.mobile}): "
                                f"pending={pending}, objected={objected}, over15days={over15days}."
                            )
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
            # Wait at least 60s so next run is scheduled on the subsequent Tuesday/Thursday
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            print("[Weekly Authority Alerts Cron] Scheduler task cancelled.")
            break
        except Exception as e:
            print(f"[Weekly Authority Alerts Cron] Unexpected scheduler error: {e}")
            await asyncio.sleep(60)
