"""
End-to-end test script: Full workflow for NEW and RENOVATION applications.

Exercises:
  NEW flow:
    1. Citizen creates & submits application     (PENDING -> SUBMITTED)
    2. Nodal Officer approves                    (SUBMITTED -> APPROVED)
    3. JEN creates inspection report             (APPROVED)
    4. Nodal Officer generates tokens (3 phases) (APPROVED -> TOKEN_GENERATED)
    5. Naka Incharge logs materials for phase 1  (naka entry)
    6. Nodal Officer completes phase 1           (activates phase 2)

  RENOVATION flow:
    1. Citizen creates & submits renovation app  (PENDING -> SUBMITTED)
    2. Commissioner forwards to departments      (SUBMITTED -> FORWARDED)
    3. JEN, ATP, Land, Legal each comment        (dept review comments)
    4. Commissioner approves                     (FORWARDED -> APPROVED)
    5. JEN creates inspection report             (APPROVED)
    6. Nodal Officer generates tokens (2 phases) (APPROVED -> TOKEN_GENERATED)

  Edge cases (NEW flow):
    - Nodal Officer objects -> citizen responds -> Nodal re-approves
    - Attempt invalid transition (reject APPROVED app)
    - Naka entry exceeding quantity limit

Usage:
    python testscripts/test_workflow.py [--base-url http://localhost:8000]

Prerequisite:
    Run create_application.py first (or this script will seed its own data).
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
SUPERADMIN_USERNAME = "superadmin"
SUPERADMIN_PASSWORD = "SuperAdmin@123"
SUPERADMIN_MOBILE = "9999999999"

TESTDOCS_DIR = Path(__file__).resolve().parent.parent / "testdocs"

# Authority users that will be created via /superadmin/users
AUTHORITY_USERS = {
    "NODAL_OFFICER": {"mobile": "1100000001", "name": "Test Nodal Officer", "username": "test_nodal", "password": "nodal123"},
    "COMMISSIONER":  {"mobile": "1100000002", "name": "Test Commissioner",  "username": "test_comm",  "password": "comm123"},
    "JEN":           {"mobile": "1100000003", "name": "Test JEN",           "username": "test_jen",   "password": "jen123"},
    "NAKA_INCHARGE": {"mobile": "1100000004", "name": "Test Naka Incharge", "username": "test_naka",  "password": "naka123"},
    "DEPT_LAND":     {"mobile": "1100000005", "name": "Test Dept Land",     "username": "test_land",  "password": "land123"},
    "DEPT_LEGAL":    {"mobile": "1100000006", "name": "Test Dept Legal",    "username": "test_legal", "password": "legal123"},
    "DEPT_ATP":      {"mobile": "1100000007", "name": "Test Dept ATP",      "username": "test_atp",   "password": "atp123"},
}

SEED_MATERIALS = [
    {"name": "Cement", "unit": "bags"},
    {"name": "Steel", "unit": "kg"},
    {"name": "Bricks", "unit": "pieces"},
    {"name": "Sand", "unit": "cubic_ft"},
    {"name": "Wood", "unit": "cubic_ft"},
    {"name": "Paint", "unit": "litres"},
]

SEED_WARDS = [
    {"name": "Ward 1", "code": "W001", "type": "RESIDENTIAL", "description": "Ward 1"},
]

SEED_DEPARTMENTS = [
    {"name": "Urban Local Body", "code": "ULB", "type": "ULB"},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _check(resp: requests.Response, context: str = ""):
    if resp.ok:
        return
    detail = ""
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    raise RuntimeError(f"[{resp.status_code}] {context}: {detail}")


def _expect_error(resp: requests.Response, expected_status: int, context: str = ""):
    """Assert that the response is an expected error."""
    if resp.status_code == expected_status:
        try:
            detail = resp.json().get("detail", "")
        except Exception:
            detail = resp.text[:100]
        print(f"     Expected error ({expected_status}): {detail}")
        return
    raise RuntimeError(
        f"Expected {expected_status} for '{context}' but got {resp.status_code}: {resp.text[:200]}"
    )


def generate_mobile() -> str:
    first = random.choice("6789")
    rest = "".join(random.choices(string.digits, k=9))
    return first + rest


# ===================================================================
# Auth helpers
# ===================================================================

def send_otp(base: str, mobile: str):
    resp = requests.post(_url(base, "/auth/send-otp"), json={"mobile": mobile})
    _check(resp, "send-otp")


def login_otp(base: str, mobile: str, otp: str = DEV_OTP) -> dict:
    """POST /auth/login/otp — auto-registers new users as CITIZEN."""
    resp = requests.post(
        _url(base, "/auth/login/otp"), json={"mobile": mobile, "otp": otp}
    )
    _check(resp, "login/otp")
    return resp.json()


def login_password(base: str, username: str, password: str) -> dict:
    resp = requests.post(
        _url(base, "/auth/login/password"),
        json={"username": username, "password": password},
    )
    _check(resp, f"login/password ({username})")
    return resp.json()


def get_citizen_token(base: str) -> tuple[str, int]:
    """Create a random citizen and return (token, user_id)."""
    mobile = generate_mobile()
    send_otp(base, mobile)
    data = login_otp(base, mobile)
    return data["access_token"], data["user_id"]


# ===================================================================
# SuperAdmin & authority user setup
# ===================================================================

def setup_superadmin(base: str) -> str:
    """Setup superadmin and return token."""
    requests.post(
        _url(base, "/superadmin/setup"),
        json={"username": SUPERADMIN_USERNAME, "password": SUPERADMIN_PASSWORD, "mobile": SUPERADMIN_MOBILE},
    )
    data = login_password(base, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
    return data["access_token"]


def create_authority_user(base: str, admin_token: str, role: str, info: dict) -> str:
    """Create an authority user and return their token."""
    # Try to create; may already exist
    resp = requests.post(
        _url(base, "/superadmin/users"),
        json={
            "mobile": info["mobile"],
            "name": info["name"],
            "role": role,
            "username": info["username"],
            "password": info["password"],
        },
        headers=_headers(admin_token),
    )
    # Login regardless
    data = login_password(base, info["username"], info["password"])
    return data["access_token"]


def setup_all_authorities(base: str, admin_token: str) -> dict[str, str]:
    """Create all authority users and return {role: token}."""
    tokens = {}
    for role, info in AUTHORITY_USERS.items():
        tokens[role] = create_authority_user(base, admin_token, role, info)
    return tokens


# ===================================================================
# Master-data seeding
# ===================================================================

def _seed_generic(base: str, token: str, list_path: str, create_path: str,
                  items: list[dict], key_field: str = "code") -> list[dict]:
    resp = requests.get(_url(base, list_path))
    _check(resp, f"GET {list_path}")
    existing = resp.json()
    existing_keys = set()
    for item in existing:
        existing_keys.add(item.get(key_field, item.get("name", "")))
    for item in items:
        item_key = item.get(key_field, item.get("name", ""))
        if item_key in existing_keys:
            continue
        requests.post(_url(base, create_path), json=item, headers=_headers(token))
    # Re-fetch
    resp = requests.get(_url(base, list_path))
    _check(resp, f"GET {list_path}")
    return resp.json()


def seed_master_data(base: str, admin_token: str) -> dict:
    wards = _seed_generic(base, admin_token, "/api/master/wards", "/api/master/wards", SEED_WARDS)
    departments = _seed_generic(base, admin_token, "/api/master/departments", "/api/master/departments", SEED_DEPARTMENTS)
    materials = _seed_generic(base, admin_token, "/api/master/materials", "/api/master/materials", SEED_MATERIALS, "name")
    return {"wards": wards, "departments": departments, "materials": materials}


# ===================================================================
# Application helpers
# ===================================================================

def create_application(base: str, token: str, ward_id: int, dept_id: int,
                       material_ids: list[int], app_type: str = "NEW") -> dict:
    payload = {
        "applicant_name": "Workflow Test Citizen",
        "father_name": "Test Father",
        "email": "workflow_test@example.com",
        "current_address": "123, Test Street, Mount Abu",
        "property_address": "456, Property Lane, Mount Abu",
        "title": f"{app_type} Construction Permit",
        "work_description": f"{app_type.lower()} construction of residential house",
        "contractor_name": "ABC Constructions",
        "is_agriculture_land": False,
        "property_usage": "DOMESTIC",
        "department_id": dept_id,
        "ward_id": ward_id,
        "type": app_type,
        "description": f"Test {app_type.lower()} application",
        "material_requirements": [
            {"material_id": mid, "material_qty": random.randint(50, 200)}
            for mid in material_ids[:3]
        ],
    }
    resp = requests.post(_url(base, "/api/applications"), json=payload, headers=_headers(token))
    _check(resp, "create application")
    return resp.json()


def upload_required_docs(base: str, token: str, app_id: int):
    """Upload the three required documents to the application."""
    doc_map = {
        "AADHAAR.pdf": "AADHAAR",
        "OWNERSHIP.pdf": "OWNERSHIP_DOCUMENTS",
        "PAN.pdf": "PERMISSION_DOCUMENTS",
    }
    for filename, doc_type in doc_map.items():
        file_path = TESTDOCS_DIR / filename
        if not file_path.exists():
            # Create a dummy file if testdocs don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"%PDF-1.4 dummy content for " + filename.encode())
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/pdf"
        with open(file_path, "rb") as f:
            resp = requests.post(
                _url(base, f"/api/applications/{app_id}/document"),
                files={"document": (filename, f, content_type)},
                data={"document_type": doc_type},
                headers=_headers(token),
            )
        _check(resp, f"upload {doc_type}")


def submit_application(base: str, token: str, app_id: int) -> dict:
    resp = requests.put(_url(base, f"/api/applications/{app_id}/submit"), headers=_headers(token))
    _check(resp, "submit")
    return resp.json()


def get_application(base: str, token: str, app_id: int) -> dict:
    resp = requests.get(_url(base, f"/api/applications/{app_id}"), headers=_headers(token))
    _check(resp, "get application")
    return resp.json()


def workflow_action(base: str, token: str, app_id: int, action: str,
                    remarks: str = None, num_stages: int = None,
                    phase_materials: list = None) -> dict:
    """PUT /api/applications/{id}/action"""
    payload: dict = {"action": action}
    if remarks:
        payload["remarks"] = remarks
    if num_stages is not None:
        payload["num_stages"] = num_stages
    if phase_materials is not None:
        payload["phase_materials"] = phase_materials
    resp = requests.put(
        _url(base, f"/api/applications/{app_id}/action"),
        json=payload,
        headers=_headers(token),
    )
    return resp


def comment_on_application(base: str, token: str, app_id: int,
                           comment: str, comment_type: str = "GENERAL",
                           media_paths: list = None) -> dict:
    payload: dict = {"comment": comment, "comment_type": comment_type}
    if media_paths:
        payload["media_paths"] = media_paths
    resp = requests.put(
        _url(base, f"/api/applications/{app_id}/comment"),
        json=payload,
        headers=_headers(token),
    )
    _check(resp, "comment")
    return resp.json()


def create_inspection(base: str, token: str, app_id: int,
                      remarks: str = "Site inspected, all clear",
                      recommended_phases: int = None,
                      phase_materials: list = None) -> dict:
    payload: dict = {
        "latitude": 24.5926,
        "longitude": 72.7156,
        "remarks": remarks,
    }
    if recommended_phases is not None:
        payload["recommended_phases"] = recommended_phases
    if phase_materials is not None:
        payload["phase_materials"] = phase_materials
    resp = requests.post(
        _url(base, f"/api/applications/{app_id}/inspection"),
        json=payload,
        headers=_headers(token),
    )
    _check(resp, "inspection")
    return resp.json()


def create_naka_entry(base: str, token: str, transport_code: str,
                      material_id: int, quantity: int,
                      vehicle_number: str = None) -> requests.Response:
    payload: dict = {
        "material_id": material_id,
        "quantity_brought": quantity,
    }
    if vehicle_number:
        payload["vehicle_number"] = vehicle_number
    resp = requests.post(
        _url(base, f"/api/naka/{transport_code}/entry"),
        json=payload,
        headers=_headers(token),
    )
    return resp


def get_phases(base: str, token: str, app_id: int) -> list:
    resp = requests.get(
        _url(base, f"/api/applications/{app_id}/phases"),
        headers=_headers(token),
    )
    _check(resp, "get phases")
    return resp.json()


def complete_phase(base: str, token: str, app_id: int, phase: int) -> dict:
    resp = requests.put(
        _url(base, f"/api/applications/{app_id}/phases/{phase}/complete"),
        headers=_headers(token),
    )
    _check(resp, f"complete phase {phase}")
    return resp.json()


# ===================================================================
# Test: NEW application full workflow
# ===================================================================

def test_new_application_workflow(base: str, citizen_token: str, tokens: dict,
                                  master: dict) -> int:
    """Test the full NEW application workflow. Returns application ID."""

    print("\n" + "=" * 60)
    print("  TEST: NEW Application Workflow")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]
    material_ids = [m["id"] for m in master["materials"]]

    # ── Step 1: Citizen creates & submits ─────────────────────────────────
    print("\n--- Step 1: Citizen creates & submits application ---")
    app = create_application(base, citizen_token, ward_id, dept_id, material_ids, "NEW")
    app_id = app["id"]
    print(f"  Created application id={app_id}, status={app['status']}")
    assert app["status"] == "PENDING"

    upload_required_docs(base, citizen_token, app_id)
    submit_application(base, citizen_token, app_id)
    app = get_application(base, citizen_token, app_id)
    assert app["status"] == "SUBMITTED", f"Expected SUBMITTED, got {app['status']}"
    print(f"  Application submitted. status={app['status']}")

    # ── Step 2: Nodal Officer approves ────────────────────────────────────
    print("\n--- Step 2: Nodal Officer approves ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "APPROVE",
                           remarks="Application looks good, approved for inspection")
    _check(resp, "nodal approve")
    print(f"  {resp.json()['message']}")

    app = get_application(base, tokens["NODAL_OFFICER"], app_id)
    assert app["status"] == "APPROVED", f"Expected APPROVED, got {app['status']}"
    print(f"  status={app['status']}")

    # ── Step 3: JEN creates inspection report ─────────────────────────────
    print("\n--- Step 3: JEN creates inspection report ---")
    # JEN inspects and recommends 3 phases with specific materials per phase
    phase_mats = []
    for phase_num in range(1, 4):
        for mid in material_ids[:3]:
            phase_mats.append({
                "phase": phase_num,
                "material_id": mid,
                "quantity": random.randint(10, 50),
            })

    create_inspection(base, tokens["JEN"], app_id,
                      remarks="Site inspection complete. Land is clear, no encroachments.",
                      recommended_phases=3,
                      phase_materials=phase_mats)
    print("  Inspection report created with recommended_phases=3")

    # ── Step 4: Nodal Officer generates tokens (3 phases) ─────────────────
    print("\n--- Step 4: Nodal Officer generates tokens (3 phases) ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "GENERATE_TOKENS",
                           remarks="Generating tokens for 3 phases",
                           num_stages=3)
    # phase_materials already created by JEN inspection — GENERATE_TOKENS deduplicates
    _check(resp, "generate tokens")
    print(f"  {resp.json()['message']}")

    app = get_application(base, tokens["NODAL_OFFICER"], app_id)
    assert app["status"] == "TOKEN_GENERATED", f"Expected TOKEN_GENERATED, got {app['status']}"
    print(f"  status={app['status']}")

    # ── Step 5: Check phases ──────────────────────────────────────────────
    print("\n--- Step 5: Verify phases ---")
    phases = get_phases(base, tokens["NODAL_OFFICER"], app_id)
    print(f"  {len(phases)} phases created:")
    for p in phases:
        print(f"    Phase {p['phase']}: {p['status']} (activated_at={p.get('activated_at')})")
    assert len(phases) == 3
    assert phases[0]["status"] == "ACTIVE", f"Phase 1 should be ACTIVE, got {phases[0]['status']}"
    assert phases[1]["status"] == "PENDING", f"Phase 2 should be PENDING, got {phases[1]['status']}"

    # ── Step 6: Naka logs materials for phase 1 ──────────────────────────
    print("\n--- Step 6: Naka Incharge logs material entry for phase 1 ---")
    first_mat_id = material_ids[0]
    # Find what quantity was allocated for phase 1, material 0
    allocated_qty = None
    for pm in phase_mats:
        if pm["phase"] == 1 and pm["material_id"] == first_mat_id:
            allocated_qty = pm["quantity"]
            break
    assert allocated_qty is not None

    # Get transport code for phase 1 from phases response
    phase1_transport_code = phases[0]["transport_code"]
    assert phase1_transport_code, "Phase 1 should have a transport_code"

    # Log a valid entry
    half_qty = max(1, allocated_qty // 2)
    resp = create_naka_entry(base, tokens["NAKA_INCHARGE"], phase1_transport_code,
                             first_mat_id, half_qty, vehicle_number="RJ-25-AB-1234")
    _check(resp, "naka entry")
    print(f"  Logged {half_qty}/{allocated_qty} of material {first_mat_id}")

    # Test: exceeding quantity limit
    print("\n--- Step 6b: Test exceeding naka quantity limit ---")
    remaining = allocated_qty - half_qty
    over_qty = remaining + 100  # way too much
    resp = create_naka_entry(base, tokens["NAKA_INCHARGE"], phase1_transport_code,
                             first_mat_id, over_qty)
    _expect_error(resp, 400, "naka entry over limit")
    print(f"  Correctly rejected over-limit entry ({over_qty} > remaining {remaining})")

    # ── Step 7: Nodal completes phase 1 -> phase 2 activates ─────────────
    print("\n--- Step 7: Nodal Officer completes phase 1 ---")
    complete_phase(base, tokens["NODAL_OFFICER"], app_id, 1)
    phases = get_phases(base, tokens["NODAL_OFFICER"], app_id)
    assert phases[0]["status"] == "COMPLETED", f"Phase 1 should be COMPLETED"
    assert phases[1]["status"] == "ACTIVE", f"Phase 2 should now be ACTIVE"
    print(f"  Phase 1: {phases[0]['status']}, Phase 2: {phases[1]['status']}, Phase 3: {phases[2]['status']}")

    print(f"\n  ✅ NEW workflow test PASSED (app_id={app_id})")
    return app_id


# ===================================================================
# Test: NEW application with OBJECTION flow
# ===================================================================

def test_objection_flow(base: str, citizen_token: str, tokens: dict, master: dict) -> int:
    """Test objection -> citizen response -> re-approval flow."""

    print("\n" + "=" * 60)
    print("  TEST: Objection & Re-approval Flow (NEW)")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]
    material_ids = [m["id"] for m in master["materials"]]

    # Create + submit
    print("\n--- Create & submit application ---")
    app = create_application(base, citizen_token, ward_id, dept_id, material_ids, "NEW")
    app_id = app["id"]
    upload_required_docs(base, citizen_token, app_id)
    submit_application(base, citizen_token, app_id)
    print(f"  Application {app_id} submitted")

    # Nodal Officer objects
    print("\n--- Nodal Officer raises objection ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "OBJECT",
                           remarks="Property documents seem unclear, please re-upload")
    _check(resp, "object")
    app = get_application(base, tokens["NODAL_OFFICER"], app_id)
    assert app["status"] == "OBJECTED", f"Expected OBJECTED, got {app['status']}"
    print(f"  status={app['status']}")

    # Citizen responds with a comment
    print("\n--- Citizen responds to objection ---")
    comment_on_application(base, citizen_token, app_id,
                           "I have re-verified my documents. They are correct.",
                           comment_type="OBJECTION_RESPONSE")
    print("  Citizen response added")

    # Nodal Officer re-approves
    print("\n--- Nodal Officer re-approves ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "APPROVE",
                           remarks="Documents verified after citizen response")
    _check(resp, "re-approve")
    app = get_application(base, tokens["NODAL_OFFICER"], app_id)
    assert app["status"] == "APPROVED", f"Expected APPROVED, got {app['status']}"
    print(f"  status={app['status']}")

    # Test: invalid transition (try to FORWARD a NEW application — not allowed)
    print("\n--- Test: Invalid transition (FORWARD on NEW app) ---")
    resp = workflow_action(base, tokens["COMMISSIONER"], app_id, "FORWARD",
                           remarks="Trying to forward a NEW application")
    _expect_error(resp, 400, "invalid FORWARD on NEW")

    print(f"\n  ✅ Objection flow test PASSED (app_id={app_id})")
    return app_id


# ===================================================================
# Test: RENOVATION application full workflow
# ===================================================================

def test_renovation_workflow(base: str, citizen_token: str, tokens: dict,
                              master: dict) -> int:
    """Test the full RENOVATION application workflow."""

    print("\n" + "=" * 60)
    print("  TEST: RENOVATION Application Workflow")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]
    material_ids = [m["id"] for m in master["materials"]]

    # ── Step 1: Citizen creates & submits ─────────────────────────────────
    print("\n--- Step 1: Citizen creates & submits RENOVATION application ---")
    app = create_application(base, citizen_token, ward_id, dept_id, material_ids, "RENOVATION")
    app_id = app["id"]
    print(f"  Created renovation app id={app_id}")

    upload_required_docs(base, citizen_token, app_id)
    submit_application(base, citizen_token, app_id)
    app = get_application(base, citizen_token, app_id)
    assert app["status"] == "SUBMITTED"
    print(f"  status={app['status']}")

    # ── Step 2: Commissioner forwards to departments ──────────────────────
    print("\n--- Step 2: Commissioner forwards to departments ---")
    resp = workflow_action(base, tokens["COMMISSIONER"], app_id, "FORWARD",
                           remarks="Forwarding to all departments for review")
    _check(resp, "commissioner forward")
    app = get_application(base, tokens["COMMISSIONER"], app_id)
    assert app["status"] == "FORWARDED", f"Expected FORWARDED, got {app['status']}"
    print(f"  status={app['status']}")

    # ── Step 3: Each department adds review comments ──────────────────────
    print("\n--- Step 3: Department reviews ---")
    dept_comments = [
        ("JEN",       "Site is suitable for renovation. Structural integrity verified."),
        ("DEPT_ATP",  "ATP clearance: No encroachment detected on adjoining roads."),
        ("DEPT_LAND", "Land records verified. Title is clean."),
        ("DEPT_LEGAL","Legal clearance: No pending disputes on this property."),
    ]
    for role, comment_text in dept_comments:
        comment_on_application(base, tokens[role], app_id, comment_text,
                               comment_type="DEPT_REVIEW")
        print(f"  {role}: commented")

    # ── Step 4: Commissioner approves after reviews ───────────────────────
    print("\n--- Step 4: Commissioner approves ---")
    resp = workflow_action(base, tokens["COMMISSIONER"], app_id, "APPROVE",
                           remarks="All department reviews positive, approved")
    _check(resp, "commissioner approve")
    app = get_application(base, tokens["COMMISSIONER"], app_id)
    assert app["status"] == "APPROVED", f"Expected APPROVED, got {app['status']}"
    print(f"  status={app['status']}")

    # ── Step 5: JEN inspection ────────────────────────────────────────────
    print("\n--- Step 5: JEN inspection ---")
    phase_mats = []
    for phase_num in range(1, 3):
        for mid in material_ids[:3]:
            phase_mats.append({
                "phase": phase_num,
                "material_id": mid,
                "quantity": random.randint(20, 60),
            })

    create_inspection(base, tokens["JEN"], app_id,
                      remarks="Renovation site inspected. Existing structure is sound.",
                      recommended_phases=2,
                      phase_materials=phase_mats)
    print("  Inspection report created with recommended_phases=2")

    # ── Step 6: Nodal Officer generates tokens (2 phases) ─────────────────
    print("\n--- Step 6: Nodal Officer generates tokens (2 phases) ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "GENERATE_TOKENS",
                           remarks="Generating tokens for renovation (2 phases)",
                           num_stages=2,
                           phase_materials=phase_mats)
    _check(resp, "generate tokens")

    app = get_application(base, tokens["NODAL_OFFICER"], app_id)
    assert app["status"] == "TOKEN_GENERATED", f"Expected TOKEN_GENERATED, got {app['status']}"
    print(f"  status={app['status']}")

    phases = get_phases(base, tokens["NODAL_OFFICER"], app_id)
    assert len(phases) == 2
    print(f"  {len(phases)} phases: Phase1={phases[0]['status']}, Phase2={phases[1]['status']}")

    print(f"\n  ✅ RENOVATION workflow test PASSED (app_id={app_id})")
    return app_id


# ===================================================================
# Test: Edge case — invalid transitions
# ===================================================================

def test_invalid_transitions(base: str, citizen_token: str, tokens: dict, master: dict):
    """Test that invalid workflow transitions are rejected."""

    print("\n" + "=" * 60)
    print("  TEST: Invalid Transition Checks")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]
    material_ids = [m["id"] for m in master["materials"]]

    # Create a PENDING application (not yet submitted)
    app = create_application(base, citizen_token, ward_id, dept_id, material_ids, "NEW")
    app_id = app["id"]
    print(f"\n  Created PENDING app id={app_id}")

    # Try to approve a PENDING app (should fail — only SUBMITTED can be approved)
    print("\n--- Test: Approve PENDING app ---")
    upload_required_docs(base, citizen_token, app_id)
    # Don't submit! Try to approve while still PENDING
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "APPROVE")
    _expect_error(resp, 400, "approve PENDING")

    # Submit it
    submit_application(base, citizen_token, app_id)

    # Try unauthorized role (JEN trying to approve NEW SUBMITTED — not allowed)
    print("\n--- Test: JEN tries to approve NEW SUBMITTED app ---")
    resp = workflow_action(base, tokens["JEN"], app_id, "APPROVE")
    _expect_error(resp, 400, "JEN approve NEW")

    # Try GENERATE_TOKENS on SUBMITTED (should fail — must be APPROVED first)
    print("\n--- Test: Generate tokens on SUBMITTED app ---")
    resp = workflow_action(base, tokens["NODAL_OFFICER"], app_id, "GENERATE_TOKENS",
                           num_stages=2)
    _expect_error(resp, 400, "tokens on SUBMITTED")

    # Naka entry on non-TOKEN_GENERATED app — use a bogus transport code.
    # The endpoint should reject it with 400 (invalid/tampered code).
    print("\n--- Test: Naka entry with invalid transport code ---")
    resp = create_naka_entry(base, tokens["NAKA_INCHARGE"], "bogus-code",
                             material_ids[0], 10)
    _expect_error(resp, 400, "naka with invalid code")

    print(f"\n  ✅ Invalid transition tests PASSED")


# ===================================================================
# Main
# ===================================================================

def run(base_url: str):
    print("=" * 60)
    print("  E2E Workflow Test Suite")
    print(f"  Base URL: {base_url}")
    print("=" * 60)

    # ── Setup ─────────────────────────────────────────────────────────────
    print("\n=== Setup: SuperAdmin + Authority Users + Master Data ===")

    admin_token = setup_superadmin(base_url)
    print(f"  SuperAdmin token obtained")

    tokens = setup_all_authorities(base_url, admin_token)
    print(f"  Authority tokens: {list(tokens.keys())}")

    master = seed_master_data(base_url, admin_token)
    print(f"  Master data: {len(master['wards'])} wards, "
          f"{len(master['departments'])} depts, {len(master['materials'])} materials")

    # Create 2 citizen tokens (one for NEW, one for RENOVATION)
    citizen_token_1, _ = get_citizen_token(base_url)
    citizen_token_2, _ = get_citizen_token(base_url)
    citizen_token_3, _ = get_citizen_token(base_url)
    citizen_token_4, _ = get_citizen_token(base_url)
    print(f"  Citizen tokens obtained")

    # ── Run tests ─────────────────────────────────────────────────────────
    results = {}

    try:
        results["new_workflow"] = test_new_application_workflow(
            base_url, citizen_token_1, tokens, master
        )
    except Exception as e:
        print(f"\n  ❌ NEW workflow FAILED: {e}")
        results["new_workflow"] = f"FAILED: {e}"

    try:
        results["objection_flow"] = test_objection_flow(
            base_url, citizen_token_2, tokens, master
        )
    except Exception as e:
        print(f"\n  ❌ Objection flow FAILED: {e}")
        results["objection_flow"] = f"FAILED: {e}"

    try:
        results["renovation_workflow"] = test_renovation_workflow(
            base_url, citizen_token_3, tokens, master
        )
    except Exception as e:
        print(f"\n  ❌ RENOVATION workflow FAILED: {e}")
        results["renovation_workflow"] = f"FAILED: {e}"

    try:
        test_invalid_transitions(base_url, citizen_token_4, tokens, master)
        results["invalid_transitions"] = "PASSED"
    except Exception as e:
        print(f"\n  ❌ Invalid transition tests FAILED: {e}")
        results["invalid_transitions"] = f"FAILED: {e}"

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        if isinstance(result, int):
            status = f"✅ PASSED (app_id={result})"
        elif result == "PASSED":
            status = "✅ PASSED"
        else:
            status = f"❌ {result}"
            all_passed = False
        print(f"  {test_name:30s} {status}")

    print("=" * 60)
    if all_passed:
        print("  🎉 ALL TESTS PASSED")
    else:
        print("  ⚠️  SOME TESTS FAILED")
    print("=" * 60)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E Workflow Test Suite")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", DEFAULT_BASE_URL),
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    try:
        results = run(args.base_url)
        # Exit with error code if any test failed
        failed = any(isinstance(v, str) and "FAILED" in v for v in results.values())
        sys.exit(1 if failed else 0)
    except Exception as exc:
        print(f"\n❌ TEST SUITE CRASHED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
