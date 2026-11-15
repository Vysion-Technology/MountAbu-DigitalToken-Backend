#!/usr/bin/env python3
"""
Weekly Alert script: Sends status updates to all official users (authorities) 
with pending and objected applications at their level on Tuesdays and Thursdays.

Execution:
    python scripts/send_weekly_alerts.py [--force]
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

# Add project root to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tasks.weekly_alerts import run_weekly_alerts_job


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

    sent_count = await run_weekly_alerts_job()
    print(f"[{datetime.now().isoformat()}] Weekly alerts processing complete. Total messages sent: {sent_count}.")


if __name__ == "__main__":
    asyncio.run(main())
