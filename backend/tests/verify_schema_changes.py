
import asyncio
import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.database import Base
from backend.dbmodels.user import User
from backend.dbmodels.master import Ward
from backend.dbmodels.application import Application, VehicleEntry, VehicleMaterial, Material
from backend.meta import UserRole, ApplicationStatus, ApplicationType
from backend.dao.master import MasterDataDAO
from backend.schemas.request.master import WardCreate

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def verify_schema():
    print("Setting up test database...")
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        print("Creating User...")
        user = User(
            mobile="9876543210",
            name="Test User",
            role=UserRole.NAKA_INCHARGE,
            username="testuser"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"User created: ID={user.id}")

        print("Testing Master Data Audit Fields...")
        dao = MasterDataDAO()
        ward_create = WardCreate(
            name="Test Ward",
            code="W001",
            type="Ward",
            description="Testing ward creation"
        )
        # Simulate Controller passing created_by_id
        ward = await dao.create_ward(session, ward_create, created_by_id=user.id)
        
        print(f"Ward created: {ward.name}, Created By ID: {ward.created_by_id}")
        assert ward.created_by_id == user.id
        assert ward.created_at is not None
        print("✅ Master Data Audit Fields Verified")

        print("Testing Vehicle Entry Models...")
        # Create Material
        material = Material(name="Cement", unit="Bags")
        session.add(material)
        
        # Create Dummy Application
        app = Application(
            user_id=user.id,
            applicant_name="John Doe",
            father_name="Jane Doe",
            mobile="1234567890",
            current_address="Address",
            property_address="Prop Address",
            title="House Construction",
            work_description="New House",
            department_id=None,
            ward_id=ward.id,
            status=ApplicationStatus.APPROVED,
            type=ApplicationType.NEW
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)
        await session.refresh(material)

        # Create Vehicle Entry
        vehicle_entry = VehicleEntry(
            application_id=app.id,
            phase=1,
            vehicle_number="RJ24 AB 1234",
            driver_name="Driver X",
            entry_by=user.id,
            remarks="Site check ok"
        )
        session.add(vehicle_entry)
        await session.flush() # Get ID

        # Create Vehicle Material
        vm = VehicleMaterial(
            vehicle_entry_id=vehicle_entry.id,
            material_id=material.id,
            quantity=50.0
        )
        session.add(vm)
        await session.commit()

        # Query back
        stmt = select(VehicleEntry).where(VehicleEntry.id == vehicle_entry.id)
        result = await session.execute(stmt)
        fetched_entry = result.scalar_one()

        # Explicitly load relationships to verify they work (async requires joinedload or explicit access in session context)
        # But we can just check if attributes are accessible or if scalars were saved correctly
        
        print(f"Vehicle Entry Retrieved: {fetched_entry.vehicle_number}")
        print(f"Vehicle Entry Driver: {fetched_entry.driver_name}")
        
        # Verify relationship to materials
        # Note: lazy loading won't work easily here without refresh/options, 
        # but let's query VehicleMaterial directly to confirm foreign key
        stmt_vm = select(VehicleMaterial).where(VehicleMaterial.vehicle_entry_id == fetched_entry.id)
        result_vm = await session.execute(stmt_vm)
        fetched_mats = result_vm.scalars().all()
        
        assert len(fetched_mats) == 1
        assert fetched_mats[0].quantity == 50.0
        print("✅ Vehicle Entry and Material Models Verified")

    print("\nALL CHECKS PASSED")

if __name__ == "__main__":
    try:
        asyncio.run(verify_schema())
    except Exception as e:
        import traceback
        with open("verification_error.log", "w") as f:
            f.write(traceback.format_exc())
        print("Error occurred. Check verification_error.log")
        sys.exit(1)
