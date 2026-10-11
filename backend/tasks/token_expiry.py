import asyncio
from datetime import datetime, time, timedelta
import zoneinfo
from sqlalchemy import select, or_, and_

from backend.database import AsyncSessionLocal
from backend.dbmodels.application import ApprovedApplicationPhase, ApplicationActionLog, Application
from backend.meta import ApplicationPhaseStatus, WorkflowAction, ApplicationStatus
from backend.schemas.response.application import TOKEN_VALIDITY_DAYS

IST = zoneinfo.ZoneInfo("Asia/Kolkata")


async def run_expire_tokens_job() -> int:
    """Find all active tokens whose validity has passed and mark their status as EXPIRED."""
    now = datetime.now()
    cutoff_60d = now - timedelta(days=TOKEN_VALIDITY_DAYS)

    expired_count = 0
    async with AsyncSessionLocal() as session:
        try:
            # Active phases where valid_till < now OR (valid_till is null and activated_at < cutoff_60d)
            stmt = select(ApprovedApplicationPhase).where(
                ApprovedApplicationPhase.status == ApplicationPhaseStatus.ACTIVE,
                or_(
                    and_(
                        ApprovedApplicationPhase.valid_till.is_not(None),
                        ApprovedApplicationPhase.valid_till < now,
                    ),
                    and_(
                        ApprovedApplicationPhase.valid_till.is_(None),
                        ApprovedApplicationPhase.activated_at.is_not(None),
                        ApprovedApplicationPhase.activated_at < cutoff_60d,
                    ),
                ),
            )
            result = await session.execute(stmt)
            phases = result.scalars().all()

            for phase in phases:
                phase.status = ApplicationPhaseStatus.EXPIRED
                expired_count += 1
                session.add(
                    ApplicationActionLog(
                        application_id=phase.application_id,
                        action=WorkflowAction.APPROVE,
                        from_status=ApplicationStatus.TOKEN_GENERATED,
                        to_status=ApplicationStatus.TOKEN_GENERATED,
                        performed_by=None,
                        performed_at=now,
                        remarks=f"Phase {phase.phase} token marked as EXPIRED by automated daily expiry job",
                        phase=phase.phase,
                    )
                )

            if expired_count > 0:
                await session.commit()
                print(f"[Daily Token Expiry Cron] Successfully marked {expired_count} tokens as EXPIRED.")
        except Exception as e:
            await session.rollback()
            print(f"[Daily Token Expiry Cron] Error expiring tokens: {e}")

    return expired_count


async def schedule_daily_token_expiry():
    """Runs indefinitely, triggering run_expire_tokens_job every day at 00:01 AM IST."""
    while True:
        try:
            now_ist = datetime.now(IST)
            target_today = datetime.combine(now_ist.date(), time(hour=0, minute=1), tzinfo=IST)

            if now_ist >= target_today:
                # Next run is tomorrow 00:01 IST
                target_run = target_today + timedelta(days=1)
            else:
                target_run = target_today

            wait_seconds = (target_run - now_ist).total_seconds()
            print(f"[Token Expiry Cron] Next run scheduled at {target_run.strftime('%Y-%m-%d %H:%M:%S %Z')} (in {wait_seconds:.1f}s)")

            await asyncio.sleep(wait_seconds)
            await run_expire_tokens_job()
        except asyncio.CancelledError:
            print("[Token Expiry Cron] Scheduler task cancelled.")
            break
        except Exception as e:
            print(f"[Token Expiry Cron] Unexpected scheduler error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying
