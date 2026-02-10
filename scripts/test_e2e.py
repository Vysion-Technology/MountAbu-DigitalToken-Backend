"""
End-to-end test: Seed users, citizen application creation, file uploads,
GET applications with flags, and authority logins.

Prerequisites: docker compose up -d --build
Run: python scripts/test_e2e.py
"""

import httpx
import sys
import os
import tempfile

BASE_URL = "http://localhost:8000"
OTP = "123456"
CITIZEN_MOBILE = "9999999999"

# Authority credentials (must match seed_users.py)
AUTHORITIES = {
    "SUPERADMIN":    {"username": "admin",        "password": "admin123"},
    "NODAL_OFFICER": {"username": "nodal",        "password": "nodal123"},
    "COMMISSIONER":  {"username": "commissioner", "password": "comm123"},
    "JEN":           {"username": "jen",           "password": "jen123"},
    "NAKA_INCHARGE": {"username": "naka",          "password": "naka123"},
    "DEPT_LAND":     {"username": "land",          "password": "land123"},
    "DEPT_LEGAL":    {"username": "legal",         "password": "legal123"},
    "DEPT_ATP":      {"username": "atp",           "password": "atp123"},
}

passed = 0
failed = 0


def report(name: str, ok: bool, detail: str = ""):
    global passed, failed
    icon = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    suffix = f" - {detail}" if detail else ""
    print(f"  [{icon}] {name}{suffix}")


def login_citizen(client: httpx.Client) -> str | None:
    """Send OTP + login for citizen. Returns access_token or None."""
    resp = client.post("/auth/send-otp", json={"mobile": CITIZEN_MOBILE})
    if resp.status_code != 200:
        report("Citizen send-otp", False, f"{resp.status_code}: {resp.text}")
        return None
    report("Citizen send-otp", True)

    resp = client.post("/auth/login/otp", json={"mobile": CITIZEN_MOBILE, "otp": OTP})
    if resp.status_code != 200:
        report("Citizen login/otp", False, f"{resp.status_code}: {resp.text}")
        return None
    data = resp.json()
    report("Citizen login/otp", True, f"role={data['role']}, user_id={data['user_id']}")
    return data["access_token"]


def login_authority(client: httpx.Client, role: str) -> str | None:
    """Login authority by username/password. Returns access_token or None."""
    creds = AUTHORITIES.get(role)
    if not creds:
        report(f"{role} login", False, "No credentials defined")
        return None
    resp = client.post("/auth/login/password", json=creds)
    if resp.status_code != 200:
        report(f"{role} login", False, f"{resp.status_code}: {resp.text}")
        return None
    data = resp.json()
    report(f"{role} login", True, f"user_id={data['user_id']}")
    return data["access_token"]


def test_citizen_application_flow(client: httpx.Client, token: str) -> int | None:
    """Create application, upload doc, add materials. Returns app_id or None."""
    headers = {"Authorization": f"Bearer {token}"}

    # Get master data IDs
    wards = client.get("/api/master/wards", headers=headers)
    depts = client.get("/api/master/departments", headers=headers)
    mats = client.get("/api/master/materials", headers=headers)

    ward_id = wards.json()[0]["id"] if wards.status_code == 200 and wards.json() else 1
    dept_id = depts.json()[0]["id"] if depts.status_code == 200 and depts.json() else 1

    mat_ids = []
    if mats.status_code == 200 and mats.json():
        mat_ids = [m["id"] for m in mats.json()[:2]]

    # 1. Create application
    payload = {
        "applicant_name": "Test Citizen",
        "father_name": "Test Father",
        "current_address": "123 Main St, Mount Abu",
        "property_address": "456 Property Rd, Mount Abu",
        "title": "New Construction Test",
        "work_description": "Building a residential house",
        "is_agriculture_land": False,
        "property_usage": "DOMESTIC",
        "department_id": dept_id,
        "ward_id": ward_id,
        "type": "NEW",
        "description": "E2E test application",
        "material_requirements": [
            {"material_id": mid, "material_qty": 100} for mid in mat_ids
        ],
    }
    resp = client.post("/api/applications", json=payload, headers=headers)
    if resp.status_code != 200:
        report("Create application", False, f"{resp.status_code}: {resp.text}")
        return None
    app_data = resp.json()
    app_id = app_data["id"]
    report("Create application", True, f"id={app_id}, status={app_data['status']}")

    # 2. Upload document
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
    tmp.write("Test document content for AADHAAR.")
    tmp.close()
    try:
        with open(tmp.name, "rb") as f:
            resp = client.post(
                f"/api/applications/{app_id}/document",
                files={"document": ("aadhaar_test.txt", f, "text/plain")},
                data={"document_type": "AADHAAR"},
                headers=headers,
            )
        if resp.status_code == 200:
            report("Upload document", True, resp.json().get("path", ""))
        else:
            report("Upload document", False, f"{resp.status_code}: {resp.text}")
    finally:
        os.unlink(tmp.name)

    # 3. Add materials post-creation
    if mat_ids:
        extra_materials = [{"material_id": mat_ids[0], "material_qty": 50}]
        resp = client.post(
            f"/api/applications/{app_id}/materials",
            json=extra_materials,
            headers=headers,
        )
        report("Add materials", resp.status_code == 200,
               f"{resp.status_code}" if resp.status_code != 200 else "ok")

    # 4. Get single application
    resp = client.get(f"/api/applications/{app_id}", headers=headers)
    if resp.status_code == 200:
        d = resp.json()
        report("Get application by ID", True,
               f"materials={len(d.get('materials', []))}, docs={len(d.get('documents', []))}")
    else:
        report("Get application by ID", False, f"{resp.status_code}: {resp.text}")

    return app_id


def test_get_applications_citizen(client: httpx.Client, token: str):
    """Test GET /applications?flag=CITIZEN for a citizen user."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/applications", params={"flag": "CITIZEN"}, headers=headers)
    if resp.status_code == 200:
        report("GET applications flag=CITIZEN", True, f"count={len(resp.json())}")
    else:
        report("GET applications flag=CITIZEN", False, f"{resp.status_code}: {resp.text}")

    # Citizen should NOT be able to use ALL flag
    resp = client.get("/api/applications", params={"flag": "ALL"}, headers=headers)
    report("Citizen flag=ALL blocked", resp.status_code == 400,
           f"status={resp.status_code}")


def test_get_applications_authorities(client: httpx.Client):
    """Test GET /applications with various flags for authority roles."""
    # SUPERADMIN with ALL flag
    token = login_authority(client, "SUPERADMIN")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/applications", params={"flag": "ALL"}, headers=headers)
        report("SUPERADMIN flag=ALL", resp.status_code == 200,
               f"count={len(resp.json()) if resp.status_code == 200 else resp.text}")

    # NODAL_OFFICER
    token = login_authority(client, "NODAL_OFFICER")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/applications",
                          params={"flag": "NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION"},
                          headers=headers)
        report("NODAL_OFFICER flag=NEW_APP_NODAL_ACTION", resp.status_code == 200,
               f"count={len(resp.json()) if resp.status_code == 200 else resp.text}")

    # COMMISSIONER
    token = login_authority(client, "COMMISSIONER")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/applications",
                          params={"flag": "RENOVATION_REQUIRES_COMMISSIONER_FORWARD"},
                          headers=headers)
        report("COMMISSIONER flag=RENO_COMM_FWD", resp.status_code == 200,
               f"count={len(resp.json()) if resp.status_code == 200 else resp.text}")

    # JEN
    token = login_authority(client, "JEN")
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/applications",
                          params={"flag": "NEW_APPLICATION_REQUIRES_JEN_FIELD_INSPECTION"},
                          headers=headers)
        report("JEN flag=NEW_APP_JEN_INSPECTION", resp.status_code == 200,
               f"count={len(resp.json()) if resp.status_code == 200 else resp.text}")

        # JEN should NOT be able to use CITIZEN flag
        resp = client.get("/api/applications", params={"flag": "CITIZEN"}, headers=headers)
        report("JEN flag=CITIZEN blocked", resp.status_code == 400,
               f"status={resp.status_code}")


def test_comment_on_application(client: httpx.Client, citizen_token: str, app_id: int):
    """Test commenting on an application by citizen and authority."""
    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}

    # 1. Citizen comments on their own application
    resp = client.put(
        f"/api/applications/{app_id}/comment",
        json={"comment": "Please expedite my application"},
        headers=citizen_headers,
    )
    report("Citizen comment on own app", resp.status_code == 200,
           f"status={resp.status_code}")

    # 2. Authority (JEN) comments on the application
    jen_token = login_authority(client, "JEN")
    if jen_token:
        jen_headers = {"Authorization": f"Bearer {jen_token}"}
        resp = client.put(
            f"/api/applications/{app_id}/comment",
            json={"comment": "Inspection scheduled for next week"},
            headers=jen_headers,
        )
        report("JEN comment on application", resp.status_code == 200,
               f"status={resp.status_code}")

    # 3. Authority (NODAL_OFFICER) comments
    nodal_token = login_authority(client, "NODAL_OFFICER")
    if nodal_token:
        nodal_headers = {"Authorization": f"Bearer {nodal_token}"}
        resp = client.put(
            f"/api/applications/{app_id}/comment",
            json={"comment": "Application is under review"},
            headers=nodal_headers,
        )
        report("NODAL_OFFICER comment on application", resp.status_code == 200,
               f"status={resp.status_code}")

    # 4. GET comments – should return all 3 comments
    resp = client.get(
        f"/api/applications/{app_id}/comments",
        headers=citizen_headers,
    )
    ok = resp.status_code == 200
    comment_count = len(resp.json()) if ok else 0
    report("GET comments returns all", ok and comment_count == 3,
           f"count={comment_count}")

    # 5. Verify comment details
    if ok and comment_count >= 1:
        first_comment = resp.json()[0]
        has_fields = all(k in first_comment for k in ("id", "comment", "comment_by", "commenter_name"))
        report("Comment has expected fields", has_fields,
               f"fields={list(first_comment.keys())}")

    # 6. Citizen should NOT be able to comment on non-existent application
    resp = client.put(
        f"/api/applications/99999/comment",
        json={"comment": "This should fail"},
        headers=citizen_headers,
    )
    report("Citizen comment on non-existent app blocked", resp.status_code == 404,
           f"status={resp.status_code}")


def main():
    global passed, failed
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # Check health
    try:
        resp = client.get("/health")
        if resp.status_code != 200:
            print("Server not healthy. Is docker compose up?")
            sys.exit(1)
    except httpx.ConnectError:
        print("Cannot connect to server. Is docker compose up?")
        sys.exit(1)

    print("=" * 60)
    print("E2E TEST SUITE")
    print("=" * 60)

    # 1. Citizen login
    print("\n--- Citizen Auth ---")
    citizen_token = login_citizen(client)
    if not citizen_token:
        print("Cannot proceed without citizen token.")
        sys.exit(1)

    # 2. Application creation flow
    print("\n--- Application Creation Flow ---")
    app_id = test_citizen_application_flow(client, citizen_token)

    # 3. Comment on Application
    print("\n--- Comment on Application ---")
    test_comment_on_application(client, citizen_token, app_id)

    # 4. GET applications for citizen
    print("\n--- Citizen GET Applications ---")
    test_get_applications_citizen(client, citizen_token)

    # 5. Authority logins + GET applications
    print("\n--- Authority GET Applications ---")
    test_get_applications_authorities(client)

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
