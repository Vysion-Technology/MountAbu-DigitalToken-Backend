"""
Seed script: Creates one user per authority role + one citizen.
Uses the superadmin /superadmin/setup & /superadmin/users endpoints.

Run after docker compose up:
    python scripts/seed_users.py
"""

import httpx
import sys

BASE_URL = "http://localhost:8000"

# Superadmin credentials (will be created via /superadmin/setup)
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_PASSWORD = "admin123"
SUPERADMIN_MOBILE = "0000000000"

# One user per authority role + one citizen
SEED_USERS = [
    {"mobile": "1000000001", "name": "Nodal Officer",   "role": "NODAL_OFFICER",  "username": "nodal",       "password": "nodal123"},
    {"mobile": "1000000002", "name": "Commissioner",    "role": "COMMISSIONER",   "username": "commissioner","password": "comm123"},
    {"mobile": "1000000003", "name": "Naka Incharge",   "role": "NAKA_INCHARGE",  "username": "naka",        "password": "naka123"},
    {"mobile": "1000000004", "name": "JEN Officer",     "role": "JEN",            "username": "jen",         "password": "jen123"},
    {"mobile": "1000000005", "name": "Dept Land",       "role": "DEPT_LAND",      "username": "land",        "password": "land123"},
    {"mobile": "1000000006", "name": "Dept Legal",      "role": "DEPT_LEGAL",     "username": "legal",       "password": "legal123"},
    {"mobile": "1000000007", "name": "Dept ATP",        "role": "DEPT_ATP",       "username": "atp",         "password": "atp123"},
    {"mobile": "9999999999", "name": "Test Citizen",    "role": "CITIZEN",        "username": None,          "password": None},
]


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. Setup superadmin
    print("=== Setting up Superadmin ===")
    resp = client.post("/superadmin/setup", json={
        "username": SUPERADMIN_USERNAME,
        "password": SUPERADMIN_PASSWORD,
        "mobile": SUPERADMIN_MOBILE,
    })
    print(f"  Setup: {resp.status_code} - {resp.json()}")

    # 2. Login as superadmin
    print("\n=== Logging in as Superadmin ===")
    resp = client.post("/auth/login/password", json={
        "username": SUPERADMIN_USERNAME,
        "password": SUPERADMIN_PASSWORD,
    })
    if resp.status_code != 200:
        print(f"  Login failed: {resp.status_code} - {resp.text}")
        sys.exit(1)

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  Logged in. Token: {token[:20]}...")

    # 3. Create seed users
    print("\n=== Creating Seed Users ===")
    for user in SEED_USERS:
        payload = {
            "mobile": user["mobile"],
            "name": user["name"],
            "role": user["role"],
        }
        if user.get("password"):
            payload["password"] = user["password"]
        if user.get("username"):
            payload["username"] = user["username"]

        resp = client.post("/superadmin/users", json=payload, headers=headers)
        status = "OK" if resp.status_code == 201 else f"SKIP ({resp.status_code})"
        try:
            body = resp.json()
            detail = body.get("message", body.get("detail", ""))
        except Exception:
            detail = resp.text[:120]
        print(f"  {user['role']:16s} {user['name']:20s} -> {status} {detail}")

    # 4. Create basic master data (ward + department + materials) — skip if already exists
    print("\n=== Creating Master Data (idempotent) ===")

    def safe_post(label, url, payload):
        try:
            resp = client.post(url, json=payload, headers=headers)
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:120]
            status = "OK" if resp.status_code in (200, 201) else f"SKIP ({resp.status_code})"
            print(f"  {label}: {status} - {body}")
        except Exception as e:
            print(f"  {label}: ERROR - {e}")

    safe_post("Ward", "/api/master/wards",
              {"name": "Ward 1", "code": "W01", "type": "Ward", "status": True})

    safe_post("Dept", "/api/master/departments",
              {"name": "Engineering", "code": "ENG", "type": "ULB", "status": True})

    for mat_name, mat_unit in [("Cement", "bags"), ("Steel", "kg"), ("Bricks", "nos"), ("Sand", "cft")]:
        safe_post(f"Material '{mat_name}'", "/api/master/materials",
                  {"name": mat_name, "unit": mat_unit})

    print("\n=== Seed Complete ===")
    print("Citizen login: mobile=9999999999, OTP=123456")
    print("Authority logins use username/password (see SEED_USERS in this script)")


if __name__ == "__main__":
    main()
