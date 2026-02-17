"""
End-to-end test script: Citizen creates and submits an application.

Steps:
  1. Generate random 10-digit mobile, send OTP, login (auto-registers if new)
  2. Setup SUPERADMIN, login, seed master data (wards, departments, roles, complaint categories, materials)
  3. Citizen: create application, upload documents via backend media proxy, submit application

Usage:
    python testscripts/create_application.py [--base-url http://localhost:8000]
"""

import os
import sys
import random
import string
import argparse
import mimetypes
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000"
DEV_OTP = "123456"
SUPERADMIN_MOBILE = "9999999999"
SUPERADMIN_USERNAME = "superadmin"
SUPERADMIN_PASSWORD = "SuperAdmin@123"

TESTDOCS_DIR = Path(__file__).resolve().parent.parent / "testdocs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _check(resp: requests.Response, context: str = ""):
    """Raise on non-2xx with a readable message."""
    if resp.ok:
        return
    detail = ""
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    raise RuntimeError(
        f"[{resp.status_code}] {context}: {detail}"
    )


def generate_mobile() -> str:
    """Random 10-digit Indian mobile starting with 6-9."""
    first = random.choice("6789")
    rest = "".join(random.choices(string.digits, k=9))
    return first + rest


# ===================================================================
# Auth helpers
# ===================================================================

def send_otp(base: str, mobile: str) -> dict:
    """POST /auth/send-otp"""
    print(f"  -> Sending OTP to {mobile} ...")
    resp = requests.post(_url(base, "/auth/send-otp"), json={"mobile": mobile})
    _check(resp, "send-otp")
    data = resp.json()
    print(f"     {data.get('message', 'OK')}")
    return data


def login_otp(base: str, mobile: str, otp: str = DEV_OTP) -> dict:
    """POST /auth/login/otp — auto-registers new users as CITIZEN."""
    print(f"  -> Logging in {mobile} via OTP ...")
    resp = requests.post(
        _url(base, "/auth/login/otp"), json={"mobile": mobile, "otp": otp}
    )
    _check(resp, "login/otp")
    data = resp.json()
    new = " (new user)" if data.get("is_new_user") else ""
    print(f"     Logged in! user_id={data['user_id']}, role={data['role']}{new}")
    return data


def login_password(base: str, username: str, password: str) -> dict:
    """POST /auth/login/password"""
    print(f"  -> Logging in with password (user={username}) ...")
    resp = requests.post(
        _url(base, "/auth/login/password"),
        json={"username": username, "password": password},
    )
    _check(resp, "login/password")
    data = resp.json()
    print(f"     Logged in! user_id={data['user_id']}, role={data['role']}")
    return data


# ===================================================================
# SuperAdmin helpers
# ===================================================================

def setup_superadmin(base: str) -> dict:
    """POST /superadmin/setup — idempotent."""
    print(f"  -> Setting up SUPERADMIN ({SUPERADMIN_USERNAME}) ...")
    resp = requests.post(
        _url(base, "/superadmin/setup"),
        json={
            "username": SUPERADMIN_USERNAME,
            "password": SUPERADMIN_PASSWORD,
            "mobile": SUPERADMIN_MOBILE,
        },
    )
    _check(resp, "superadmin/setup")
    data = resp.json()
    print(f"     {data.get('message', 'OK')}")
    return data


def get_superadmin_token(base: str) -> str:
    """Login as superadmin and return access_token."""
    data = login_password(base, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
    return data["access_token"]


# ===================================================================
# Master-data seeding (idempotent — checks before creating)
# ===================================================================

SEED_WARDS = [
    {"name": "Ward 1", "code": "W001", "type": "RESIDENTIAL", "description": "Ward 1 - Residential"},
    {"name": "Ward 2", "code": "W002", "type": "COMMERCIAL", "description": "Ward 2 - Commercial"},
    {"name": "Ward 3", "code": "W003", "type": "MIXED", "description": "Ward 3 - Mixed"},
]

SEED_DEPARTMENTS = [
    {"name": "Urban Local Body", "code": "ULB", "type": "ULB"},
    {"name": "Town Planning", "code": "TP", "type": "ULB"},
    {"name": "Revenue", "code": "REV", "type": "ULB"},
]

SEED_ROLES = [
    {"name": "Super Admin", "code": "SUPERADMIN"},
    {"name": "Nodal Officer", "code": "NODAL_OFFICER"},
    {"name": "Commissioner", "code": "COMMISSIONER"},
    {"name": "Citizen", "code": "CITIZEN"},
    {"name": "Naka Incharge", "code": "NAKA_INCHARGE"},
    {"name": "Department Land", "code": "DEPT_LAND"},
    {"name": "Department Legal", "code": "DEPT_LEGAL"},
    {"name": "Department ATP", "code": "DEPT_ATP"},
    {"name": "Junior Engineer", "code": "JEN"},
]

SEED_COMPLAINT_CATEGORIES = [
    {"name": "Road Damage", "description": "Potholes, broken roads"},
    {"name": "Water Supply", "description": "Water supply issues"},
    {"name": "Electricity", "description": "Streetlight and power issues"},
    {"name": "Sanitation", "description": "Garbage and cleanliness issues"},
    {"name": "Encroachment", "description": "Illegal encroachment"},
]

SEED_MATERIALS = [
    {"name": "Cement", "unit": "bags"},
    {"name": "Steel", "unit": "kg"},
    {"name": "Bricks", "unit": "pieces"},
    {"name": "Sand", "unit": "cubic_ft"},
    {"name": "Wood", "unit": "cubic_ft"},
    {"name": "Paint", "unit": "litres"},
]


def _seed_generic(
    base: str,
    token: str,
    list_path: str,
    create_path: str,
    items: list[dict],
    key_field: str = "code",
    entity_name: str = "item",
) -> list[dict]:
    """Generic idempotent seeder: list existing, create missing, return all."""
    resp = requests.get(_url(base, list_path))
    _check(resp, f"GET {list_path}")
    existing = resp.json()

    existing_keys = set()
    for item in existing:
        if key_field in item:
            existing_keys.add(item[key_field])
        elif "name" in item:
            existing_keys.add(item["name"])

    created_count = 0
    for item in items:
        item_key = item.get(key_field, item.get("name", ""))
        if item_key in existing_keys:
            continue
        resp = requests.post(
            _url(base, create_path), json=item, headers=_headers(token)
        )
        if resp.ok:
            created_count += 1
        else:
            # might already exist from code-level uniqueness
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text
            print(f"     WARN creating {entity_name} '{item_key}': {resp.status_code} {detail}")

    # Re-fetch full list
    resp = requests.get(_url(base, list_path))
    _check(resp, f"GET {list_path}")
    all_items = resp.json()
    print(f"     {entity_name}: {created_count} created, {len(all_items)} total")
    return all_items


def seed_master_data(base: str, token: str) -> dict:
    """Seed all master data. Returns dict with lists of each entity."""
    print("\n=== Seeding Master Data ===")

    print("  -> Wards ...")
    wards = _seed_generic(base, token, "/api/master/wards", "/api/master/wards", SEED_WARDS, "code", "wards")

    print("  -> Departments ...")
    departments = _seed_generic(base, token, "/api/master/departments", "/api/master/departments", SEED_DEPARTMENTS, "code", "departments")

    print("  -> Roles ...")
    roles = _seed_generic(base, token, "/api/master/roles", "/api/master/roles", SEED_ROLES, "code", "roles")

    print("  -> Complaint Categories ...")
    categories = _seed_generic(base, token, "/api/master/complaint-categories", "/api/master/complaint-categories", SEED_COMPLAINT_CATEGORIES, "name", "complaint categories")

    print("  -> Materials ...")
    materials = _seed_generic(base, token, "/api/master/materials", "/api/master/materials", SEED_MATERIALS, "name", "materials")

    return {
        "wards": wards,
        "departments": departments,
        "roles": roles,
        "complaint_categories": categories,
        "materials": materials,
    }


# ===================================================================
# Application helpers
# ===================================================================

def create_application(
    base: str,
    token: str,
    ward_id: int,
    department_id: int,
    material_ids: list[int],
) -> dict:
    """POST /api/applications — Create a NEW application."""
    print("\n=== Creating Application ===")
    payload = {
        "applicant_name": "Test Citizen",
        "father_name": "Test Father",
        "email": "testcitizen@example.com",
        "current_address": "123, Test Street, Mount Abu, Rajasthan",
        "property_address": "456, Property Lane, Mount Abu, Rajasthan",
        "title": "New Construction Permit",
        "work_description": "Construction of a residential house on plot no. 456",
        "contractor_name": "ABC Constructions",
        "is_agriculture_land": False,
        "property_usage": "DOMESTIC",
        "department_id": department_id,
        "ward_id": ward_id,
        "type": "NEW",
        "description": "Application for new construction permit in Ward 1",
        "material_requirements": [
            {"material_id": mid, "material_qty": random.randint(10, 100)}
            for mid in material_ids[:3]  # pick up to 3 materials
        ],
    }
    resp = requests.post(
        _url(base, "/api/applications"), json=payload, headers=_headers(token)
    )
    _check(resp, "create application")
    app = resp.json()
    print(f"  -> Application created! id={app['id']}, status={app['status']}")
    return app


def upload_media(
    base: str,
    file_path: Path,
    category: str = "application",
    entity_id: Optional[int] = None,
) -> dict:
    """POST /api/media/upload — upload file through the backend (proxied to MinIO)."""
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    data = {"category": category}
    if entity_id:
        data["entity_id"] = str(entity_id)
    with open(file_path, "rb") as f:
        resp = requests.post(
            _url(base, "/api/media/upload"),
            files={"file": (file_path.name, f, content_type)},
            data=data,
        )
    _check(resp, "media/upload")
    return resp.json()


def upload_document_to_application(
    base: str,
    token: str,
    application_id: int,
    file_path: Path,
    document_type: str,
) -> dict:
    """Upload a document to an application using multipart form upload."""
    print(f"  -> Uploading {file_path.name} as {document_type} ...")
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        resp = requests.post(
            _url(base, f"/api/applications/{application_id}/document"),
            files={"document": (file_path.name, f, content_type)},
            data={"document_type": document_type},
            headers=_headers(token),
        )
    _check(resp, f"upload document {file_path.name}")
    data = resp.json()
    print(f"     Uploaded: {data.get('message', 'OK')} -> {data.get('path', '')}")
    return data


def upload_via_media_proxy(
    base: str,
    token: str,
    application_id: int,
    file_path: Path,
    document_type: str,
) -> dict:
    """
    Upload a file using the backend media proxy:
      1. POST file to /api/media/upload (backend proxies to MinIO)
      2. Attach document record to application
    """
    print(f"  -> Uploading {file_path.name} as {document_type} (via media proxy) ...")

    # Step 1: Upload file through backend proxy
    media = upload_media(base, file_path, category="application", entity_id=application_id)
    print(f"     Uploaded to MinIO: {media['object_key']}")

    # Step 2: Attach document record to application
    with open(file_path, "rb") as f:
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        resp = requests.post(
            _url(base, f"/api/applications/{application_id}/document"),
            files={"document": (file_path.name, f, content_type)},
            data={"document_type": document_type},
            headers=_headers(token),
        )
    _check(resp, f"attach document {file_path.name}")
    data = resp.json()
    print(f"     Attached: {data.get('message', 'OK')}")
    return data


def submit_application(base: str, token: str, application_id: int) -> dict:
    """PUT /api/applications/{id}/submit — transition PENDING -> SUBMITTED."""
    print(f"\n=== Submitting Application {application_id} ===")
    resp = requests.put(
        _url(base, f"/api/applications/{application_id}/submit"),
        headers=_headers(token),
    )
    _check(resp, "submit application")
    data = resp.json()
    print(f"  -> {data.get('message', 'OK')}")
    return data


def get_application(base: str, token: str, application_id: int) -> dict:
    """GET /api/applications/{id}"""
    resp = requests.get(
        _url(base, f"/api/applications/{application_id}"),
        headers=_headers(token),
    )
    _check(resp, "get application")
    return resp.json()


# ===================================================================
# Main flow
# ===================================================================

def run(base_url: str):
    print("=" * 60)
    print("  E2E Test: Citizen Application Creation & Submission")
    print(f"  Base URL: {base_url}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # STEP 1: Citizen auth (send OTP -> login, auto-registers if new)
    # ------------------------------------------------------------------
    print("\n=== Step 1: Citizen Authentication ===")
    citizen_mobile = generate_mobile()
    print(f"  Generated mobile: {citizen_mobile}")

    send_otp(base_url, citizen_mobile)
    token_data = login_otp(base_url, citizen_mobile)

    citizen_token = token_data["access_token"]
    citizen_user_id = token_data["user_id"]
    print(f"  Citizen token obtained. user_id={citizen_user_id}")

    # ------------------------------------------------------------------
    # STEP 2: Setup SUPERADMIN & seed master data
    # ------------------------------------------------------------------
    print("\n=== Step 2: SuperAdmin Setup & Master Data ===")
    setup_superadmin(base_url)
    admin_token = get_superadmin_token(base_url)
    master = seed_master_data(base_url, admin_token)

    # Pick first ward, first department, all material ids
    ward_id = master["wards"][0]["id"]
    department_id = master["departments"][0]["id"]
    material_ids = [m["id"] for m in master["materials"]]

    print(f"\n  Using ward_id={ward_id}, department_id={department_id}")
    print(f"  Available material IDs: {material_ids}")

    # ------------------------------------------------------------------
    # STEP 3: Create application as citizen
    # ------------------------------------------------------------------
    app = create_application(
        base_url, citizen_token, ward_id, department_id, material_ids
    )
    app_id = app["id"]

    # ------------------------------------------------------------------
    # STEP 4: Upload documents
    # ------------------------------------------------------------------
    print("\n=== Step 4: Uploading Documents ===")

    # Map testdocs files to document types
    doc_map = {
        "AADHAAR.pdf": "AADHAAR",
        "OWNERSHIP.pdf": "OWNERSHIP_DOCUMENTS",
        "PAN.pdf": "PERMISSION_DOCUMENTS",       # PAN used as permission doc for testing
        "PHOTO.jpg": "APPLICANT_PHOTO",
    }

    for filename, doc_type in doc_map.items():
        file_path = TESTDOCS_DIR / filename
        if not file_path.exists():
            print(f"  !! File not found: {file_path}, skipping {doc_type}")
            continue
        try:
            upload_via_media_proxy(base_url, citizen_token, app_id, file_path, doc_type)
        except Exception as e:
            print(f"  !! Media proxy upload failed ({e}), falling back to direct upload")
            upload_document_to_application(base_url, citizen_token, app_id, file_path, doc_type)

    # ------------------------------------------------------------------
    # STEP 5: Verify application has documents, then submit
    # ------------------------------------------------------------------
    print("\n=== Step 5: Verify Documents & Submit ===")
    app_details = get_application(base_url, citizen_token, app_id)
    doc_types_present = [d["document_type"] for d in app_details.get("documents", [])]
    print(f"  Document types on application: {doc_types_present}")

    required = {"AADHAAR", "PERMISSION_DOCUMENTS", "OWNERSHIP_DOCUMENTS"}
    missing = required - set(doc_types_present)
    if missing:
        print(f"  WARNING: Missing required docs for submission: {missing}")
        print("  Attempting submit anyway to test validation ...")

    submit_application(base_url, citizen_token, app_id)

    # ------------------------------------------------------------------
    # STEP 6: Verify final state
    # ------------------------------------------------------------------
    print("\n=== Step 6: Final Verification ===")
    final_app = get_application(base_url, citizen_token, app_id)
    print(f"  Application ID : {final_app['id']}")
    print(f"  Status         : {final_app['status']}")
    print(f"  Type           : {final_app['type']}")
    print(f"  Applicant      : {final_app['applicant_name']}")
    print(f"  Documents      : {len(final_app.get('documents', []))}")
    print(f"  Materials      : {len(final_app.get('materials', []))}")

    assert final_app["status"] == "SUBMITTED", (
        f"Expected SUBMITTED but got {final_app['status']}"
    )

    print("\n" + "=" * 60)
    print("  ✅ TEST PASSED — Application created and submitted!")
    print("=" * 60)

    return {
        "citizen_token": citizen_token,
        "citizen_user_id": citizen_user_id,
        "admin_token": admin_token,
        "application_id": app_id,
        "master_data": master,
    }


# ===================================================================
# CLI entry point
# ===================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E: Create & submit application")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", DEFAULT_BASE_URL),
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    try:
        result = run(args.base_url)
    except Exception as exc:
        print(f"\n❌ TEST FAILED: {exc}")
        sys.exit(1)
