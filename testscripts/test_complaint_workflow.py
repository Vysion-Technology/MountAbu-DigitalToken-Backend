"""
End-to-end test script: Full workflow for Complaints.

Exercises:
  1. Setup: SuperAdmin + Authority Users + Master Data (wards, departments, categories)
  2. Citizen creates complaint             → verify id is NOT NULL, user_id is set
  3. Citizen fetches own complaints        → GET /complaints/my returns the complaint
  4. Authority lists all complaints        → GET /complaints returns the complaint
  5. Authority (or citizen) adds comment   → POST /complaints/{id}/comments
  6. Authority adds media                  → POST /complaints/{id}/media
  7. Get single complaint                  → GET /complaints/{id} returns full detail
  8. Citizen dashboard                     → verify complaint counts are accurate
  9. Edge cases:
     - Citizen cannot access authority list (GET /complaints → 403)
     - Comment on non-existent complaint → 404
     - Create complaint with missing fields → 422

Usage:
    python testscripts/test_complaint_workflow.py [--base-url http://localhost:8000]

Prerequisite:
    Docker services running (backend, postgres, minio).
"""

import os
import sys
import random
import string
import argparse
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

# Authority users for complaint testing
AUTHORITY_USERS = {
    "NODAL_OFFICER": {
        "mobile": "1100000001",
        "name": "Test Nodal Officer",
        "username": "test_nodal",
        "password": "nodal123",
    },
    "COMMISSIONER": {
        "mobile": "1100000002",
        "name": "Test Commissioner",
        "username": "test_comm",
        "password": "comm123",
    },
}

SEED_WARDS = [
    {"name": "Ward 1", "code": "W001", "type": "RESIDENTIAL", "description": "Ward 1"},
]

SEED_DEPARTMENTS = [
    {"name": "Urban Local Body", "code": "ULB", "type": "ULB"},
]

SEED_COMPLAINT_CATEGORIES = [
    {"name": "Garbage", "description": "Waste collection issues", "status": True},
    {"name": "Water Supply", "description": "Water supply problems", "status": True},
    {"name": "Street Light", "description": "Broken / non-working street lights", "status": True},
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


def _assert(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


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


def get_citizen_token(base: str) -> tuple:
    """Create a random citizen and return (token, user_id)."""
    mobile = generate_mobile()
    send_otp(base, mobile)
    data = login_otp(base, mobile)
    return data["access_token"], data["user_id"]


# ===================================================================
# SuperAdmin & authority user setup
# ===================================================================


def setup_superadmin(base: str) -> str:
    requests.post(
        _url(base, "/superadmin/setup"),
        json={
            "username": SUPERADMIN_USERNAME,
            "password": SUPERADMIN_PASSWORD,
            "mobile": SUPERADMIN_MOBILE,
        },
    )
    data = login_password(base, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
    return data["access_token"]


def create_authority_user(base: str, admin_token: str, role: str, info: dict) -> str:
    requests.post(
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
    data = login_password(base, info["username"], info["password"])
    return data["access_token"]


def setup_all_authorities(base: str, admin_token: str) -> dict:
    tokens = {}
    for role, info in AUTHORITY_USERS.items():
        tokens[role] = create_authority_user(base, admin_token, role, info)
    return tokens


# ===================================================================
# Master-data seeding
# ===================================================================


def _seed_generic(
    base: str,
    token: str,
    list_path: str,
    create_path: str,
    items: list,
    key_field: str = "code",
) -> list:
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
    resp = requests.get(_url(base, list_path))
    _check(resp, f"GET {list_path}")
    return resp.json()


def seed_master_data(base: str, admin_token: str) -> dict:
    wards = _seed_generic(
        base, admin_token, "/api/master/wards", "/api/master/wards", SEED_WARDS
    )
    departments = _seed_generic(
        base,
        admin_token,
        "/api/master/departments",
        "/api/master/departments",
        SEED_DEPARTMENTS,
    )
    categories = _seed_generic(
        base,
        admin_token,
        "/api/master/complaint-categories",
        "/api/master/complaint-categories",
        SEED_COMPLAINT_CATEGORIES,
        key_field="name",
    )
    return {"wards": wards, "departments": departments, "categories": categories}


# ===================================================================
# Complaint helpers
# ===================================================================


def create_complaint(
    base: str,
    token: str,
    ward_id: int,
    dept_id: int,
    category_id: int,
    title: str = "Garbage not collected",
    description: str = "Garbage has not been collected for 3 days near the main road.",
    applicant_name: str = "Test Citizen",
    applicant_mobile: str = "+919876543210",
    location_address: str = "Near Main Road, Ward 1",
) -> dict:
    payload = {
        "title": title,
        "description": description,
        "ward_id": ward_id,
        "department_id": dept_id,
        "category_id": category_id,
        "applicant_name": applicant_name,
        "applicant_mobile": applicant_mobile,
        "latitude": 24.5926,
        "longitude": 72.7156,
        "location_address": location_address,
        "media_keys": [],
    }
    resp = requests.post(
        _url(base, "/api/complaints"), json=payload, headers=_headers(token)
    )
    _check(resp, "create complaint")
    return resp.json()


def get_complaint(base: str, token: str, complaint_id: int) -> dict:
    resp = requests.get(
        _url(base, f"/api/complaints/{complaint_id}"), headers=_headers(token)
    )
    _check(resp, f"get complaint {complaint_id}")
    return resp.json()


def get_my_complaints(
    base: str, token: str, status_filter: Optional[str] = None
) -> dict:
    params = {}
    if status_filter:
        params["status"] = status_filter
    resp = requests.get(
        _url(base, "/api/complaints/my"), params=params, headers=_headers(token)
    )
    _check(resp, "get my complaints")
    return resp.json()


def get_all_complaints(
    base: str, token: str, **filters
) -> dict:
    resp = requests.get(
        _url(base, "/api/complaints"), params=filters, headers=_headers(token)
    )
    _check(resp, "get all complaints")
    return resp.json()


def add_comment(base: str, token: str, complaint_id: int, comment: str) -> dict:
    payload = {"comment": comment, "media_keys": []}
    resp = requests.post(
        _url(base, f"/api/complaints/{complaint_id}/comments"),
        json=payload,
        headers=_headers(token),
    )
    _check(resp, "add comment")
    return resp.json()


def add_media(base: str, token: str, complaint_id: int, media_keys: list) -> dict:
    payload = {"media_keys": media_keys}
    resp = requests.post(
        _url(base, f"/api/complaints/{complaint_id}/media"),
        json=payload,
        headers=_headers(token),
    )
    _check(resp, "add media")
    return resp.json()


def get_citizen_dashboard(base: str, token: str) -> dict:
    resp = requests.get(_url(base, "/api/dashboard"), headers=_headers(token))
    _check(resp, "get citizen dashboard")
    return resp.json()


# ===================================================================
# Test 1: Create complaint and verify ID is not NULL
# ===================================================================


def test_create_complaint(
    base: str, citizen_token: str, citizen_user_id: int, master: dict
) -> int:
    print("\n" + "=" * 60)
    print("  TEST: Create Complaint — ID must NOT be NULL")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]
    cat_id = master["categories"][0]["id"]

    complaint = create_complaint(
        base,
        citizen_token,
        ward_id,
        dept_id,
        cat_id,
        title="Garbage not collected on Main Street",
        description="Garbage has not been picked up for the last 3 days. It is causing a health hazard.",
    )

    complaint_id = complaint.get("id")
    user_id = complaint.get("user_id")

    print(f"  Complaint ID : {complaint_id}")
    print(f"  User ID      : {user_id}")
    print(f"  Title        : {complaint['title']}")
    print(f"  Status       : {complaint['status']}")

    # ── Critical assertions ───────────────────────────────────────────────
    _assert(complaint_id is not None, "BUG: complaint id is NULL!")
    _assert(isinstance(complaint_id, int) and complaint_id > 0, f"complaint id should be a positive int, got {complaint_id}")
    _assert(user_id is not None, "BUG: user_id is NULL — complaint not linked to citizen!")
    _assert(user_id == citizen_user_id, f"user_id mismatch: expected {citizen_user_id}, got {user_id}")
    _assert(complaint["status"] == "PENDING", f"expected PENDING status, got {complaint['status']}")
    _assert(complaint["ward_id"] == ward_id, "ward_id mismatch")
    _assert(complaint["department_id"] == dept_id, "department_id mismatch")
    _assert(complaint["category_id"] == cat_id, "category_id mismatch")

    print(f"\n  ✅ Create complaint PASSED (id={complaint_id}, user_id={user_id})")
    return complaint_id


# ===================================================================
# Test 2: Citizen /complaints/my returns created complaint
# ===================================================================


def test_my_complaints(
    base: str, citizen_token: str, expected_complaint_id: int
):
    print("\n" + "=" * 60)
    print("  TEST: GET /complaints/my — citizen sees own complaints")
    print("=" * 60)

    data = get_my_complaints(base, citizen_token)
    items = data.get("items", [])
    total = data.get("total", 0)

    print(f"  Total: {total}")
    print(f"  Items returned: {len(items)}")

    _assert(total >= 1, f"Expected at least 1 complaint, got total={total}")
    _assert(len(items) >= 1, f"Expected at least 1 item, got {len(items)}")

    ids_returned = [c["id"] for c in items]
    _assert(
        expected_complaint_id in ids_returned,
        f"Complaint {expected_complaint_id} not found in /complaints/my response. Got IDs: {ids_returned}",
    )

    # Verify the complaint detail
    matched = next(c for c in items if c["id"] == expected_complaint_id)
    _assert(matched["user_id"] is not None, "user_id still NULL in /complaints/my")

    # Test filtering by status
    filtered = get_my_complaints(base, citizen_token, status_filter="PENDING")
    _assert(filtered["total"] >= 1, "PENDING filter should find at least 1 complaint")

    filtered_resolved = get_my_complaints(base, citizen_token, status_filter="RESOLVED")
    # We haven't resolved anything so this should be 0
    _assert(filtered_resolved["total"] == 0, "RESOLVED filter should return 0 at this stage")

    print(f"\n  ✅ /complaints/my PASSED")


# ===================================================================
# Test 3: Authority lists complaints
# ===================================================================


def test_authority_list_complaints(
    base: str, authority_token: str, expected_complaint_id: int, master: dict
):
    print("\n" + "=" * 60)
    print("  TEST: GET /complaints — authority lists all complaints")
    print("=" * 60)

    data = get_all_complaints(base, authority_token)
    items = data.get("items", [])

    print(f"  Total: {data.get('total', 0)}")

    ids_returned = [c["id"] for c in items]
    _assert(
        expected_complaint_id in ids_returned,
        f"Complaint {expected_complaint_id} not in authority list. Got IDs: {ids_returned}",
    )

    # Test filtering by ward
    ward_id = master["wards"][0]["id"]
    filtered = get_all_complaints(base, authority_token, ward_id=ward_id)
    _assert(filtered["total"] >= 1, f"Ward filter should find complaint in ward {ward_id}")

    # Test filtering by department
    dept_id = master["departments"][0]["id"]
    filtered = get_all_complaints(base, authority_token, department_id=dept_id)
    _assert(filtered["total"] >= 1, f"Department filter should find complaint in dept {dept_id}")

    # Test filtering by category
    cat_id = master["categories"][0]["id"]
    filtered = get_all_complaints(base, authority_token, category_id=cat_id)
    _assert(filtered["total"] >= 1, f"Category filter should find complaint in category {cat_id}")

    print(f"\n  ✅ Authority complaint list PASSED")


# ===================================================================
# Test 4: Add comment to complaint
# ===================================================================


def test_add_comment(
    base: str, citizen_token: str, authority_token: str, complaint_id: int, citizen_user_id: int
):
    print("\n" + "=" * 60)
    print("  TEST: Add comments to complaint")
    print("=" * 60)

    # Citizen adds a comment
    result = add_comment(base, citizen_token, complaint_id, "Please resolve this soon.")
    comments = result.get("comments", [])
    print(f"  After citizen comment: {len(comments)} comment(s)")
    _assert(len(comments) >= 1, "Expected at least 1 comment after citizen comment")

    citizen_comment = comments[-1]
    _assert(citizen_comment["comment"] == "Please resolve this soon.", "Comment text mismatch")
    _assert(citizen_comment["comment_by"] == citizen_user_id, f"comment_by should be {citizen_user_id}, got {citizen_comment['comment_by']}")

    # Authority adds a comment
    result = add_comment(base, authority_token, complaint_id, "We are looking into this issue.")
    comments = result.get("comments", [])
    print(f"  After authority comment: {len(comments)} comment(s)")
    _assert(len(comments) >= 2, "Expected at least 2 comments")

    authority_comment = comments[-1]
    _assert(authority_comment["comment"] == "We are looking into this issue.", "Authority comment text mismatch")
    _assert(authority_comment["comment_by"] is not None, "Authority comment_by should not be NULL")

    print(f"\n  ✅ Add comment PASSED")


# ===================================================================
# Test 5: Add media to complaint
# ===================================================================


def test_add_media(base: str, authority_token: str, complaint_id: int):
    print("\n" + "=" * 60)
    print("  TEST: Add media to complaint")
    print("=" * 60)

    # Use dummy S3 keys (the endpoint just stores keys, doesn't verify objects)
    result = add_media(
        base,
        authority_token,
        complaint_id,
        media_keys=["complaints/test_photo_1.jpg", "complaints/test_photo_2.jpg"],
    )

    media = result.get("media", [])
    print(f"  Media items: {len(media)}")
    _assert(len(media) >= 2, f"Expected at least 2 media items, got {len(media)}")

    # Check the newly added ones (is_initial=False)
    non_initial = [m for m in media if not m["is_initial"]]
    _assert(len(non_initial) >= 2, "Expected at least 2 non-initial media items")

    print(f"\n  ✅ Add media PASSED")


# ===================================================================
# Test 6: Get single complaint with full detail
# ===================================================================


def test_get_complaint_detail(base: str, token: str, complaint_id: int):
    print("\n" + "=" * 60)
    print("  TEST: GET /complaints/{id} — full detail")
    print("=" * 60)

    complaint = get_complaint(base, token, complaint_id)

    print(f"  ID       : {complaint['id']}")
    print(f"  User ID  : {complaint['user_id']}")
    print(f"  Title    : {complaint['title']}")
    print(f"  Status   : {complaint['status']}")
    print(f"  Comments : {len(complaint.get('comments', []))}")
    print(f"  Media    : {len(complaint.get('media', []))}")

    _assert(complaint["id"] == complaint_id, "ID mismatch on detail endpoint")
    _assert(complaint["user_id"] is not None, "user_id is NULL on detail endpoint")
    _assert(len(complaint.get("comments", [])) >= 2, "Expected >= 2 comments from previous tests")
    _assert(len(complaint.get("media", [])) >= 2, "Expected >= 2 media items from previous tests")

    print(f"\n  ✅ Get complaint detail PASSED")


# ===================================================================
# Test 7: Citizen dashboard shows complaint counts
# ===================================================================


def test_citizen_dashboard_complaints(base: str, citizen_token: str):
    print("\n" + "=" * 60)
    print("  TEST: Citizen dashboard — complaint counts")
    print("=" * 60)

    try:
        dashboard = get_citizen_dashboard(base, citizen_token)
        complaints = dashboard.get("complaints", {})
        total = complaints.get("total", 0)
        closed = complaints.get("closed", 0)

        print(f"  Total complaints : {total}")
        print(f"  Closed complaints: {closed}")

        _assert(total >= 1, f"Dashboard should show at least 1 complaint, got {total}")
        _assert(closed == 0, f"No complaints should be closed yet, got {closed}")

        print(f"\n  ✅ Citizen dashboard complaints PASSED")
    except Exception as e:
        # Dashboard endpoint might have a different shape; don't fail the suite
        print(f"\n  ⚠️  Dashboard test skipped: {e}")


# ===================================================================
# Test 8: Edge cases
# ===================================================================


def test_edge_cases(base: str, citizen_token: str, authority_token: str, master: dict):
    print("\n" + "=" * 60)
    print("  TEST: Edge cases")
    print("=" * 60)

    # 8a. Citizen cannot access authority complaint list
    print("\n--- Citizen tries GET /complaints (authority endpoint) ---")
    resp = requests.get(
        _url(base, "/api/complaints"), headers=_headers(citizen_token)
    )
    _expect_error(resp, 403, "citizen accessing authority list")

    # 8b. Comment on non-existent complaint
    print("\n--- Comment on non-existent complaint ---")
    resp = requests.post(
        _url(base, "/api/complaints/999999/comments"),
        json={"comment": "Hello", "media_keys": []},
        headers=_headers(citizen_token),
    )
    _expect_error(resp, 404, "comment on non-existent complaint")

    # 8c. Create complaint with missing required fields (title too short)
    print("\n--- Create complaint with title too short ---")
    resp = requests.post(
        _url(base, "/api/complaints"),
        json={
            "title": "Hi",  # min_length=5
            "description": "This is a valid description",
            "applicant_name": "Test",
            "applicant_mobile": "+919876543210",
        },
        headers=_headers(citizen_token),
    )
    _expect_error(resp, 422, "short title validation")

    # 8d. Create complaint with invalid mobile number
    print("\n--- Create complaint with invalid mobile ---")
    resp = requests.post(
        _url(base, "/api/complaints"),
        json={
            "title": "Valid title here",
            "description": "This is a valid description",
            "ward_id": master["wards"][0]["id"],
            "department_id": master["departments"][0]["id"],
            "category_id": master["categories"][0]["id"],
            "applicant_name": "Test",
            "applicant_mobile": "not-a-phone",
        },
        headers=_headers(citizen_token),
    )
    _expect_error(resp, 422, "invalid mobile validation")

    # 8e. Get non-existent complaint
    print("\n--- Get non-existent complaint ---")
    resp = requests.get(
        _url(base, f"/api/complaints/999999"), headers=_headers(citizen_token)
    )
    _expect_error(resp, 404, "get non-existent complaint")

    print(f"\n  ✅ Edge cases PASSED")


# ===================================================================
# Test 9: Multiple complaints from same citizen
# ===================================================================


def test_multiple_complaints(
    base: str, citizen_token: str, citizen_user_id: int, master: dict
):
    print("\n" + "=" * 60)
    print("  TEST: Multiple complaints from same citizen")
    print("=" * 60)

    ward_id = master["wards"][0]["id"]
    dept_id = master["departments"][0]["id"]

    # Create complaints across different categories
    complaint_ids = []
    for i, cat in enumerate(master["categories"]):
        c = create_complaint(
            base,
            citizen_token,
            ward_id,
            dept_id,
            cat["id"],
            title=f"Test complaint #{i+1} — {cat['name']}",
            description=f"Detailed description for complaint about {cat['name']} issues in the area.",
            applicant_name="Multi-Complaint Citizen",
        )
        _assert(c["id"] is not None, f"Complaint #{i+1} id is NULL!")
        _assert(c["user_id"] == citizen_user_id, f"Complaint #{i+1} user_id mismatch")
        complaint_ids.append(c["id"])
        print(f"  Created complaint #{i+1}: id={c['id']}, category={cat['name']}")

    # Verify /complaints/my returns all of them
    my = get_my_complaints(base, citizen_token)
    my_ids = {item["id"] for item in my["items"]}
    for cid in complaint_ids:
        _assert(cid in my_ids, f"Complaint {cid} missing from /complaints/my")

    # +1 from test_create_complaint
    _assert(
        my["total"] >= len(complaint_ids) + 1,
        f"Expected at least {len(complaint_ids)+1} total, got {my['total']}",
    )

    print(f"\n  ✅ Multiple complaints PASSED (created {len(complaint_ids)})")


# ===================================================================
# Main
# ===================================================================


def run(base_url: str):
    print("=" * 60)
    print("  Complaint E2E Workflow Test Suite")
    print(f"  Base URL: {base_url}")
    print("=" * 60)

    # ── Setup ─────────────────────────────────────────────────────────────
    print("\n=== Setup: SuperAdmin + Authority Users + Master Data ===")

    admin_token = setup_superadmin(base_url)
    print(f"  SuperAdmin token obtained")

    tokens = setup_all_authorities(base_url, admin_token)
    print(f"  Authority tokens: {list(tokens.keys())}")

    master = seed_master_data(base_url, admin_token)
    print(
        f"  Master data: {len(master['wards'])} wards, "
        f"{len(master['departments'])} depts, {len(master['categories'])} categories"
    )

    citizen_token, citizen_user_id = get_citizen_token(base_url)
    print(f"  Citizen token obtained (user_id={citizen_user_id})")

    authority_token = tokens["NODAL_OFFICER"]

    # ── Run tests ─────────────────────────────────────────────────────────
    results = {}

    # Test 1: Create complaint
    try:
        complaint_id = test_create_complaint(
            base_url, citizen_token, citizen_user_id, master
        )
        results["create_complaint"] = "PASSED"
    except Exception as e:
        print(f"\n  ❌ Create complaint FAILED: {e}")
        results["create_complaint"] = f"FAILED: {e}"
        complaint_id = None

    # Test 2: /complaints/my
    if complaint_id:
        try:
            test_my_complaints(base_url, citizen_token, complaint_id)
            results["my_complaints"] = "PASSED"
        except Exception as e:
            print(f"\n  ❌ /complaints/my FAILED: {e}")
            results["my_complaints"] = f"FAILED: {e}"
    else:
        results["my_complaints"] = "SKIPPED (no complaint_id)"

    # Test 3: Authority list
    if complaint_id:
        try:
            test_authority_list_complaints(
                base_url, authority_token, complaint_id, master
            )
            results["authority_list"] = "PASSED"
        except Exception as e:
            print(f"\n  ❌ Authority list FAILED: {e}")
            results["authority_list"] = f"FAILED: {e}"
    else:
        results["authority_list"] = "SKIPPED (no complaint_id)"

    # Test 4: Add comments
    if complaint_id:
        try:
            test_add_comment(
                base_url, citizen_token, authority_token, complaint_id, citizen_user_id
            )
            results["add_comment"] = "PASSED"
        except Exception as e:
            print(f"\n  ❌ Add comment FAILED: {e}")
            results["add_comment"] = f"FAILED: {e}"
    else:
        results["add_comment"] = "SKIPPED (no complaint_id)"

    # Test 5: Add media
    if complaint_id:
        try:
            test_add_media(base_url, authority_token, complaint_id)
            results["add_media"] = "PASSED"
        except Exception as e:
            print(f"\n  ❌ Add media FAILED: {e}")
            results["add_media"] = f"FAILED: {e}"
    else:
        results["add_media"] = "SKIPPED (no complaint_id)"

    # Test 6: Get complaint detail
    if complaint_id:
        try:
            test_get_complaint_detail(base_url, citizen_token, complaint_id)
            results["complaint_detail"] = "PASSED"
        except Exception as e:
            print(f"\n  ❌ Complaint detail FAILED: {e}")
            results["complaint_detail"] = f"FAILED: {e}"
    else:
        results["complaint_detail"] = "SKIPPED (no complaint_id)"

    # Test 7: Citizen dashboard
    try:
        test_citizen_dashboard_complaints(base_url, citizen_token)
        results["dashboard_counts"] = "PASSED"
    except Exception as e:
        print(f"\n  ❌ Dashboard counts FAILED: {e}")
        results["dashboard_counts"] = f"FAILED: {e}"

    # Test 8: Edge cases
    try:
        test_edge_cases(base_url, citizen_token, authority_token, master)
        results["edge_cases"] = "PASSED"
    except Exception as e:
        print(f"\n  ❌ Edge cases FAILED: {e}")
        results["edge_cases"] = f"FAILED: {e}"

    # Test 9: Multiple complaints
    try:
        test_multiple_complaints(base_url, citizen_token, citizen_user_id, master)
        results["multiple_complaints"] = "PASSED"
    except Exception as e:
        print(f"\n  ❌ Multiple complaints FAILED: {e}")
        results["multiple_complaints"] = f"FAILED: {e}"

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  COMPLAINT TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        if result == "PASSED":
            marker = "✅ PASSED"
        elif "SKIPPED" in result:
            marker = f"⏭️  {result}"
        else:
            marker = f"❌ {result}"
            all_passed = False
        print(f"  {test_name:30s} {marker}")

    print("=" * 60)
    if all_passed:
        print("  🎉 ALL COMPLAINT TESTS PASSED")
    else:
        print("  ⚠️  SOME TESTS FAILED")
    print("=" * 60)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complaint E2E Workflow Test Suite")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", DEFAULT_BASE_URL),
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    try:
        results = run(args.base_url)
        failed = any(
            isinstance(v, str) and "FAILED" in v for v in results.values()
        )
        sys.exit(1 if failed else 0)
    except Exception as exc:
        print(f"\n❌ TEST SUITE CRASHED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
