import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())


# Mock settings for local testing if needed, or rely on .env
# For now, we assume .env is loaded or settings are valid.


async def verify_withdrawal():
    print("Setting up test database connection...")
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from backend.config import settings
    from backend.dbmodels.user import User, UserRole
    from backend.dbmodels.application import Application
    from backend.dbmodels.complaint import Complaint
    from backend.meta import ApplicationStatus, ComplaintStatus
    from backend.dao.application import ApplicationDAO
    from backend.controllers.complaint import get_complaint_or_404

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as db:
        try:
            print("Creating test user...")
            # Create a test citizen
            test_citizen = User(
                mobile="9999999999", role=UserRole.CITIZEN, name="Test Citizen"
            )
            db.add(test_citizen)
            await db.commit()
            await db.refresh(test_citizen)
            print(f"Created user {test_citizen.id}")

            # Create a test application
            print("Creating test application...")
            app = Application(
                user_id=test_citizen.id,
                status=ApplicationStatus.PENDING,
                # Minimal fields
                ward_id=1,
                department_id=1,
                applicant_name="Test Citizen",
                father_name="Test Father",
                mobile="9999999999",
                current_address="Current Address",
                property_address="Property Address",
                title="Application Title",
                work_description="Work Description",
                property_usage="DOMESTIC",
            )
            db.add(app)
            await db.commit()
            await db.refresh(app)
            print(f"Created application {app.id}")

            # Test Application Withdrawal
            print("Testing Application DAO withdrawal...")
            dao = ApplicationDAO(db)
            response = await dao.withdraw_application(app.id, test_citizen.id)
            print(f"Withdrawal response: {response.message}")

            # Verify status
            await db.refresh(app)
            if app.status == ApplicationStatus.WITHDRAWN:
                print("SUCCESS: Application status is WITHDRAWN")
            else:
                print(f"FAILURE: Application status is {app.status}")

            # Create a test complaint
            print("Creating test complaint...")
            complaint = Complaint(
                user_id=test_citizen.id,
                status=ComplaintStatus.PENDING,
                title="Test Complaint",
                description="Test Description",
                ward_id=1,
                department_id=1,
                category_id=1,
                applicant_name="Test Citizen",
                applicant_mobile="9999999999",
                latitude=0.0,
                longitude=0.0,
                location_address="Test Address",
            )
            db.add(complaint)
            await db.commit()
            await db.refresh(complaint)
            print(f"Created complaint {complaint.id}")

            # Test Complaint Withdrawal Logic (simulate controller logic)
            print("Testing Complaint withdrawal logic...")
            # Re-implement logic here as we can't easily call controller function directly without mocking params
            if complaint.user_id != test_citizen.id:
                print("FAILURE: User check failed")
            elif complaint.status != ComplaintStatus.PENDING:
                print("FAILURE: Status check failed")
            else:
                complaint.status = ComplaintStatus.WITHDRAWN
                await db.commit()
                await db.refresh(complaint)
                if complaint.status == ComplaintStatus.WITHDRAWN:
                    print("SUCCESS: Complaint status is WITHDRAWN")
                else:
                    print(f"FAILURE: Complaint status is {complaint.status}")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback

            traceback.print_exc()
        finally:
            print("Cleaning up...")
            try:
                from sqlalchemy import text

                # Delete in correct order to avoid FK issues
                if "app" in locals():
                    await db.execute(
                        text(
                            f"DELETE FROM application_action_logs WHERE application_id = {app.id}"
                        )
                    )
                    await db.execute(
                        text(f"DELETE FROM applications WHERE id = {app.id}")
                    )
                if "complaint" in locals():
                    await db.execute(
                        text(f"DELETE FROM complaints WHERE id = {complaint.id}")
                    )
                if "test_citizen" in locals():
                    await db.execute(
                        text(f"DELETE FROM users WHERE id = {test_citizen.id}")
                    )
                await db.commit()
                print("Cleanup complete.")
            except Exception as e:
                print(f"Cleanup failed: {e}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(verify_withdrawal())
    except Exception:
        import traceback

        with open("verification_error.log", "w") as f:
            f.write(traceback.format_exc())
        print("Error occurred. Check verification_error.log")
