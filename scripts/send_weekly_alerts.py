#!/usr/bin/env python3
"""
Weekly Alert script: Sends status updates to all official users (authorities) 
with pending and objected applications at their level on Tuesdays and Thursdays.

Execution:
    python scripts/send_weekly_alerts.py
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

# Add project root to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal
from backend.dao.user import UserDAO
from backend.dao.application import ApplicationDAO
from backend.services.sms import sms_service
from backend.meta import UserRole

def get_ist_now() -> datetime:
    """Get current UTC time and convert to UTC+5:30 (IST)."""
    utc_now = datetime.now(timezone.utc)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return utc_now.astimezone(ist_tz)

async def main():
    # Timezone-aware IST execution check
    ist_now = get_ist_now()
    print(f"[{ist_now.isoformat()}] Starting weekly alerts processing...")
    
    # Check if --force flag is passed to run manually
    force = "--force" in sys.argv
    
    if not force:
        # Check if today is Tuesday (1) or Thursday (3)
        is_correct_day = ist_now.weekday() in (1, 3)
        # Check if the hour is 10 AM (10:00 - 10:59)
        is_correct_hour = ist_now.hour == 10
        
        if not (is_correct_day and is_correct_hour):
            print(
                f"Skipping execution: Current IST time {ist_now.strftime('%A %I:%M %p')} "
                f"is not Tuesday/Thursday at 10:00 AM. Use --force to override."
            )
            return
        else:
            print("Scheduling check passed. Executing weekly alerts...")

    
    async with AsyncSessionLocal() as session:
        user_dao = UserDAO()
        app_dao = ApplicationDAO(session)
        
        # 1. Fetch all active official users (not CITIZEN)
        all_users = await user_dao.get_users_filtered(session, is_citizen=False)
        active_officials = [u for u in all_users if u.is_active]
        print(f"Found {len(active_officials)} active official users.")
        
        sent_count = 0
        for user in active_officials:
            # Skip roles that do not participate in workflow queues (e.g. Naka Incharges/Superadmins)
            # Superadmin / Admin / Naka incharge don't have actionable workflow queues in the DAO check
            if user.role in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.NAKA_INCHARGE):
                continue
                
            try:
                stats = await app_dao.get_authority_pending_stats(user.role)
                pending = stats.get("pending", 0)
                objected = stats.get("objected", 0)
                over15days = stats.get("over15days", 0)
                
                # Check if user has anything pending or objected
                if pending > 0 or objected > 0:
                    print(f"User {user.name} ({user.role}) has pending={pending}, objected={objected}, over15days={over15days}.")
                    
                    # Trigger SMS
                    success = await sms_service.send_weekly_alert_sms(
                        mobile=user.mobile,
                        name=user.name,
                        pending=pending,
                        objected=objected,
                        over15days=over15days
                    )
                    
                    if success:
                        sent_count += 1
                        print(f"  SMS successfully triggered/queued for {user.name} ({user.mobile}).")
                    else:
                        print(f"  FAILED to trigger SMS for {user.name} ({user.mobile}).")
            except Exception as e:
                print(f"  Error processing alerts for user {user.name} ({user.role}): {e}", file=sys.stderr)
                
        print(f"[{datetime.now().isoformat()}] Weekly alerts processing complete. Total messages sent: {sent_count}.")

if __name__ == "__main__":
    asyncio.run(main())
