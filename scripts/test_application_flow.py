import asyncio
import httpx
import random
import os

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if different
MOBILE_NUMBER = f"{random.randint(6000000000, 9999999999)}"
OTP = "123456"


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print(f"Testing with mobile: {MOBILE_NUMBER}")

        # 1. Login/Signup
        print("\n--- 1. Login/Signup ---")
        # Send OTP
        resp = await client.post("/auth/send-otp", json={"mobile": MOBILE_NUMBER})
        print(f"Send OTP: {resp.status_code} - {resp.json()}")

        # Login
        resp = await client.post(
            "/auth/signup",
            json={
                "mobile": MOBILE_NUMBER,
                "otp": OTP,
                "name": f"Test User {MOBILE_NUMBER}",
            },
        )
        if resp.status_code == 400 and "already registered" in resp.text:
            resp = await client.post(
                "/auth/login/otp", json={"mobile": MOBILE_NUMBER, "otp": OTP}
            )

        print(f"Login: {resp.status_code}")
        if resp.status_code != 200:
            print("Login failed, exiting.")
            return

        token_data = resp.json()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        print(f"Got Access Token: {access_token[:20]}...")

        # 2. Create Application (No materials)
        print("\n--- 2. Create Application ---")
        app_payload = {
            "applicant_name": "John Doe",
            "father_name": "Richard Doe",
            "current_address": "123 Test St",
            "property_address": "456 Prop Ln",
            "title": "New Construction",
            "work_description": "Building a house",
            "is_agriculture_land": False,
            "property_usage": "DOMESTIC",
            "department_id": 1,
            "ward_id": 1,
            "type": "NEW",
            "description": "Test Application",
            "material_requirements": [],
        }

        # Helper to create master data if missing
        async def get_or_create_master(endpoint, payload):
            resp = await client.get(endpoint, headers=headers)
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]["id"]

            # Create
            print(f"Creating master data for {endpoint}...")
            resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code == 200:
                print(f"Created: {resp.json()}")
                return resp.json()["id"]
            else:
                print(f"Failed to create master data {endpoint}: {resp.text}")
                return 1  # Fallback

        ward_id = await get_or_create_master(
            "/api/master/wards",
            {"name": "Ward 1", "code": "W01", "type": "Ward", "status": True},
        )
        app_payload["ward_id"] = ward_id

        dept_id = await get_or_create_master(
            "/api/master/departments",
            {"name": "Engineering", "code": "ENG", "type": "ULB", "status": True},
        )
        app_payload["department_id"] = dept_id

        resp = await client.post("/api/applications", json=app_payload, headers=headers)
        print(f"Create App: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Failed: {resp.text}")
            return

        app_data = resp.json()
        app_id = app_data["id"]
        print(f"Created Application ID: {app_id}")

        # 3. Upload Document (AADHAAR)
        print("\n--- 3. Upload Document ---")
        # Create a dummy file
        with open("test_doc.txt", "w") as f:
            f.write("This is a test document content.")

        try:
            with open("test_doc.txt", "rb") as f:
                files = {"document": ("test_doc.txt", f, "text/plain")}
                data = {"document_type": "AADHAAR"}
                resp = await client.post(
                    f"/api/applications/{app_id}/document",
                    files=files,
                    data=data,
                    headers=headers,
                )
            print(f"Upload Doc: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"Upload failed: {e}. Body: {resp.text}")
        finally:
            if os.path.exists("test_doc.txt"):
                os.remove("test_doc.txt")

        # 4. Upload Materials
        print("\n--- 4. Upload Materials (Post-creation) ---")

        # Ensure materials exist
        mat1_id = await get_or_create_master(
            "/api/master/materials", {"name": "Cement", "unit": "bags"}
        )
        mat2_id = await get_or_create_master(
            "/api/master/materials", {"name": "Steel", "unit": "kg"}
        )

        material_payload = [
            {"material_id": mat1_id, "material_qty": 100},
            {"material_id": mat2_id, "material_qty": 50},
        ]

        resp = await client.post(
            f"/api/applications/{app_id}/materials",
            json=material_payload,
            headers=headers,
        )
        print(f"Upload Materials: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Failed: {resp.text}")
        else:
            print("Materials added successfully.")

        # 5. Verify Materials via Get Application
        print("\n--- 5. Verify Application Data ---")
        resp = await client.get(f"/api/applications/{app_id}", headers=headers)
        if resp.status_code == 200:
            final_data = resp.json()
            materials_count = len(final_data.get("materials", []))
            documents_count = len(final_data.get("documents", []))
            print(
                f"Verification: Materials={materials_count}, Documents={documents_count}"
            )

            # Print document types if visible
            for doc in final_data.get("documents", []):
                print(
                    f"- Doc: {doc.get('document_name')} Type: {doc.get('document_type')}"
                )
        else:
            print("Failed to fetch application.")


if __name__ == "__main__":
    asyncio.run(main())
