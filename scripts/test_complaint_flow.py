import asyncio
import httpx
import random

BASE_URL = "http://localhost:8000"
MOBILE = f"{random.randint(6000000000, 9999999999)}"
OTP = "123456"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print(f"Testing Complaint Flow with mobile: {MOBILE}")

        # 1. Login
        await client.post("/auth/send-otp", json={"mobile": MOBILE})
        resp = await client.post("/auth/dict/signup", json={"mobile": MOBILE, "otp": OTP, "name": "Complaint User"})
        # Actually logic is try login, if fail signup.
        resp = await client.post("/auth/login/otp", json={"mobile": MOBILE, "otp": OTP})
        if resp.status_code == 404:
             resp = await client.post("/auth/signup", json={"mobile": MOBILE, "otp": OTP, "name": "Complaint User"})
        
        if resp.status_code != 200:
            print(f"Auth failed: {resp.text}")
            return
            
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Master Data
        # We need ward, dept, category
        ward_id = 1
        dept_id = 1
        cat_id = 1 # Complaint Category
        
        # Ensure they exist
        async def ensure_master(url, payload):
            r = await client.get(f"/api{url}", headers=headers)
            if r.status_code == 200 and r.json():
                return r.json()[0]["id"]
            r = await client.post(f"/api{url}", json=payload, headers=headers)
            return r.json()["id"]

        ward_id = await ensure_master("/master/wards", {"name":"Ward C", "code":"WC", "type":"Ward", "status":True})
        dept_id = await ensure_master("/master/departments", {"name":"Health", "code":"HLT", "type":"ULB", "status":True})
        cat_id = await ensure_master("/master/complaint-categories", {"name":"Garbage", "description":"Waste", "status":True})

        # 3. Create Complaint
        print("\n--- Creating Complaint ---")
        payload = {
            "title": "Garbage issue",
            "description": "Garbage not collected for 2 days",
            "ward_id": ward_id,
            "department_id": dept_id,
            "category_id": cat_id,
            "applicant_name": "Citizen One",
            "applicant_mobile": "+919876543210",
            "location_address": "Street 1",
            "media_keys": [] # Optional
        }
        
        resp = await client.post("/api/complaints", json=payload, headers=headers)
        print(f"Create Complaint: {resp.status_code}")
        if resp.status_code not in [200, 201]:
            print(f"Failed: {resp.text}")
            return
            
        complaint_id = resp.json()["id"]
        print(f"Complaint ID: {complaint_id}")
        
        # 4. Add Comment
        print("\n--- Adding Comment ---")
        resp = await client.post(f"/api/complaints/{complaint_id}/comments", json={"comment": "Still waiting"}, headers=headers)
        print(f"Add Comment: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
