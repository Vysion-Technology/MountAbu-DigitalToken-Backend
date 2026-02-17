"""
End-to-end test for the Token APIs.

Tests the full flow:
  1. Citizen creates application with materials
  2. Uploads required documents
  3. Submits application
  4. Nodal Officer approves (NEW flow)
  5. JEN creates inspection report
  6. Nodal Officer generates tokens (phases + phase materials)
  7. GET /api/tokens — citizen list (5-column response)
  8. GET /api/tokens?status=ACTIVE — status filter
  9. GET /api/tokens?search=TKN — search filter
 10. GET /api/tokens/{transport_code} — full token detail
 11. Naka incharge logs vehicle entry
 12. GET /api/tokens/{transport_code} — verify vehicle entries & material consumed
 13. GET /api/applications/{id}/tokens — tokens on application
 14. GET /api/applications/{id} — tokens embedded in application response

Prerequisites: docker compose up -d --build && python scripts/seed_users.py
Run: python scripts/test_token_flow.py
"""

import httpx
import os
import random
import sys
import tempfile

BASE_URL = "http://localhost:8000"
OTP = "123456"
# Use a random mobile so login/otp auto-creates a fresh CITIZEN user
CITIZEN_MOBILE = f"{random.randint(6000000000, 9999999998)}"

AUTHORITIES = {
    "SUPERADMIN":    {"username": "admin",        "password": "admin123"},
    "NODAL_OFFICER": {"username": "nodal",        "password": "nodal123"},
    "COMMISSIONER":  {"username": "commissioner", "password": "comm123"},
    "JEN":           {"username": "jen",           "password": "jen123"},
    "NAKA_INCHARGE": {"username": "naka",          "password": "naka123"},
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
    suffix = f"  — {detail}" if detail else ""
    print(f"  [{icon}] {name}{suffix}")


# ── Auth helpers ──────────────────────────────────────────────────────────

def login_citizen(client: httpx.Client) -> str | None:
    client.post("/auth/send-otp", json={"mobile": CITIZEN_MOBILE})
    resp = client.post("/auth/login/otp", json={"mobile": CITIZEN_MOBILE, "otp": OTP})
    if resp.status_code != 200:
        report("Citizen login", False, resp.text)
        return None
    data = resp.json()
    report("Citizen login", True, f"user_id={data['user_id']}")
    return data["access_token"]


def login_authority(client: httpx.Client, role: str) -> str | None:
    creds = AUTHORITIES[role]
    resp = client.post("/auth/login/password", json=creds)
    if resp.status_code != 200:
        report(f"{role} login", False, f"{resp.status_code}: {resp.text}")
        return None
    data = resp.json()
    report(f"{role} login", True, f"user_id={data['user_id']}")
    return data["access_token"]


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Master data helpers ───────────────────────────────────────────────────

def ensure_master_data(client: httpx.Client, headers: dict) -> dict:
    """Ensure wards, departments, materials exist. Returns IDs."""
    ids = {}

    # Ward
    resp = client.get("/api/master/wards", headers=headers)
    if resp.status_code == 200 and resp.json():
        ids["ward_id"] = resp.json()[0]["id"]
    else:
        r = client.post("/api/master/wards",
                        json={"name": "Ward 3", "code": "W03", "type": "Ward", "status": True},
                        headers=headers)
        ids["ward_id"] = r.json()["id"] if r.status_code == 200 else 1

    # Department
    resp = client.get("/api/master/departments", headers=headers)
    if resp.status_code == 200 and resp.json():
        ids["dept_id"] = resp.json()[0]["id"]
    else:
        r = client.post("/api/master/departments",
                        json={"name": "Engineering", "code": "ENG", "type": "ULB", "status": True},
                        headers=headers)
        ids["dept_id"] = r.json()["id"] if r.status_code == 200 else 1

    # Materials — ensure at least 2
    resp = client.get("/api/master/materials", headers=headers)
    mats = resp.json() if resp.status_code == 200 else []
    if len(mats) < 2:
        for mat_spec in [("Cement", "bags"), ("Sand", "tons")]:
            r = client.post("/api/master/materials",
                            json={"name": mat_spec[0], "unit": mat_spec[1]},
                            headers=headers)
            if r.status_code == 200:
                mats.append(r.json())
        # Re-fetch
        resp = client.get("/api/master/materials", headers=headers)
        mats = resp.json() if resp.status_code == 200 else mats

    ids["mat1_id"] = mats[0]["id"]
    ids["mat2_id"] = mats[1]["id"] if len(mats) > 1 else mats[0]["id"]
    return ids


# ── Document upload helper ────────────────────────────────────────────────

def upload_doc(client: httpx.Client, app_id: int, doc_type: str, headers: dict) -> bool:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
    tmp.write(f"Test content for {doc_type}")
    tmp.close()
    try:
        with open(tmp.name, "rb") as f:
            resp = client.post(
                f"/api/applications/{app_id}/document",
                files={"document": (f"{doc_type.lower()}.txt", f, "text/plain")},
                data={"document_type": doc_type},
                headers=headers,
            )
        return resp.status_code == 200
    finally:
        os.unlink(tmp.name)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN TEST
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global passed, failed
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # Health check
    try:
        resp = client.get("/health")
        if resp.status_code != 200:
            print("Server not healthy. Run: docker compose up -d --build")
            sys.exit(1)
    except httpx.ConnectError:
        print("Cannot connect. Run: docker compose up -d --build")
        sys.exit(1)

    print("=" * 65)
    print("  TOKEN FLOW E2E TEST")
    print("=" * 65)

    # ── 1. Auth ───────────────────────────────────────────────────────
    print("\n─── Auth ─────────────────────────────────────────────")
    citizen_token = login_citizen(client)
    nodal_token = login_authority(client, "NODAL_OFFICER")
    jen_token = login_authority(client, "JEN")
    naka_token = login_authority(client, "NAKA_INCHARGE")
    if not all([citizen_token, nodal_token, jen_token, naka_token]):
        print("\nCannot proceed without all tokens. Did you run seed_users.py?")
        sys.exit(1)

    # ── 2. Ensure master data ─────────────────────────────────────────
    print("\n─── Master Data ──────────────────────────────────────")
    ids = ensure_master_data(client, hdr(nodal_token))
    report("Master data ready", True,
           f"ward={ids['ward_id']}, dept={ids['dept_id']}, mat1={ids['mat1_id']}, mat2={ids['mat2_id']}")

    # ── 3. Citizen creates application ────────────────────────────────
    print("\n─── Create Application (Citizen) ─────────────────────")
    app_payload = {
        "applicant_name": "Rajesh Patel",
        "father_name": "Mahesh Patel",
        "current_address": "House No. 27, Sunset Road, Mount Abu",
        "property_address": "House No. 27, Sunset Road, Near Nakki Lake, Mount Abu, District Sirohi, Rajasthan - 307501",
        "title": "New Construction - Residential",
        "work_description": "Construction of a 2-storey residential building",
        "is_agriculture_land": False,
        "property_usage": "DOMESTIC",
        "department_id": ids["dept_id"],
        "ward_id": ids["ward_id"],
        "type": "NEW",
        "description": "Token flow test application",
        "material_requirements": [
            {"material_id": ids["mat1_id"], "material_qty": 200},
            {"material_id": ids["mat2_id"], "material_qty": 20},
        ],
    }
    resp = client.post("/api/applications", json=app_payload, headers=hdr(citizen_token))
    ok = resp.status_code == 200
    report("Create application", ok, f"{resp.status_code}")
    if not ok:
        print(f"  ERROR: {resp.text}")
        sys.exit(1)
    app_id = resp.json()["id"]
    print(f"  Application ID: {app_id}")

    # ── 4. Upload required documents ──────────────────────────────────
    print("\n─── Upload Documents ─────────────────────────────────")
    for doc_type in ["AADHAAR", "PERMISSION_DOCUMENTS", "OWNERSHIP_DOCUMENTS"]:
        ok = upload_doc(client, app_id, doc_type, hdr(citizen_token))
        report(f"Upload {doc_type}", ok)

    # ── 5. Submit application ─────────────────────────────────────────
    print("\n─── Submit Application ───────────────────────────────")
    resp = client.put(f"/api/applications/{app_id}/submit", headers=hdr(citizen_token))
    report("Submit application", resp.status_code == 200, f"{resp.status_code}")
    if resp.status_code != 200:
        print(f"  ERROR: {resp.text}")

    # ── 6. Nodal Officer approves (NEW flow: SUBMITTED → APPROVED) ───
    print("\n─── Nodal Officer Approves ───────────────────────────")
    resp = client.put(
        f"/api/applications/{app_id}/action",
        json={"action": "APPROVE", "remarks": "All documents verified"},
        headers=hdr(nodal_token),
    )
    report("Nodal approve", resp.status_code == 200, f"{resp.status_code}")
    if resp.status_code != 200:
        print(f"  ERROR: {resp.text}")

    # ── 7. JEN creates inspection + material recommendations ──────────
    print("\n─── JEN Inspection Report ────────────────────────────")
    resp = client.post(
        f"/api/applications/{app_id}/inspection",
        json={
            "latitude": 24.5926,
            "longitude": 72.7156,
            "remarks": "Site inspection completed. Construction area verified.",
            "recommended_phases": 2,
            "phase_materials": [
                {"phase": 1, "material_id": ids["mat1_id"], "quantity": 100},
                {"phase": 1, "material_id": ids["mat2_id"], "quantity": 10},
                {"phase": 2, "material_id": ids["mat1_id"], "quantity": 100},
                {"phase": 2, "material_id": ids["mat2_id"], "quantity": 10},
            ],
        },
        headers=hdr(jen_token),
    )
    report("JEN inspection", resp.status_code == 200, f"{resp.status_code}")
    if resp.status_code != 200:
        print(f"  ERROR: {resp.text}")

    # ── 8. Nodal Officer generates tokens ─────────────────────────────
    print("\n─── Generate Tokens (Nodal Officer) ──────────────────")
    resp = client.put(
        f"/api/applications/{app_id}/action",
        json={
            "action": "GENERATE_TOKENS",
            "remarks": "Tokens generated after JEN inspection",
            "num_stages": 2,
            "phase_materials": [
                {"phase": 1, "material_id": ids["mat1_id"], "quantity": 100},
                {"phase": 1, "material_id": ids["mat2_id"], "quantity": 10},
                {"phase": 2, "material_id": ids["mat1_id"], "quantity": 100},
                {"phase": 2, "material_id": ids["mat2_id"], "quantity": 10},
            ],
        },
        headers=hdr(nodal_token),
    )
    report("Generate tokens", resp.status_code == 200, f"{resp.status_code}")
    if resp.status_code != 200:
        print(f"  ERROR: {resp.text}")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════
    #  TOKEN API TESTS
    # ═══════════════════════════════════════════════════════════════════

    # ── 9. GET /api/tokens — citizen token list ───────────────────────
    print("\n─── GET /api/tokens (List) ───────────────────────────")
    resp = client.get("/api/tokens", headers=hdr(citizen_token))
    ok = resp.status_code == 200
    tokens = resp.json() if ok else []
    report("GET /tokens returns 200", ok, f"count={len(tokens)}")

    if ok and tokens:
        # Verify only 5 fields + transport_code
        first = tokens[0]
        expected_fields = {"transport_code", "token_number", "application_number",
                           "remaining_quantity_pct", "valid_till", "status"}
        actual_fields = set(first.keys())
        report("Token list has exactly 6 fields",
               actual_fields == expected_fields,
               f"actual={sorted(actual_fields)}")

        report("token_number format TKN-...", first["token_number"].startswith("TKN-"),
               first["token_number"])
        report("application_number format APP-...", first["application_number"].startswith("APP-"),
               first["application_number"])
        report("status is ACTIVE or PENDING", first["status"] in ("ACTIVE", "PENDING"),
               first["status"])
        report("remaining_quantity_pct is number",
               isinstance(first["remaining_quantity_pct"], (int, float)) or first["remaining_quantity_pct"] is None,
               str(first["remaining_quantity_pct"]))

        # Save transport codes for detail tests
        transport_codes = [t["transport_code"] for t in tokens]
        active_tokens = [t for t in tokens if t["status"] == "ACTIVE"]
        active_tc = active_tokens[0]["transport_code"] if active_tokens else transport_codes[0]
    else:
        transport_codes = []
        active_tc = None

    # ── 10. GET /api/tokens?status=ACTIVE — status filter ─────────────
    print("\n─── GET /api/tokens?status=ACTIVE ────────────────────")
    resp = client.get("/api/tokens", params={"status": "ACTIVE"}, headers=hdr(citizen_token))
    ok = resp.status_code == 200
    filtered = resp.json() if ok else []
    all_active = all(t["status"] == "ACTIVE" for t in filtered) if filtered else True
    report("Status filter returns 200", ok, f"count={len(filtered)}")
    report("All returned tokens are ACTIVE", all_active)

    # ── 11. GET /api/tokens?search=TKN — search filter ────────────────
    print("\n─── GET /api/tokens?search=TKN ───────────────────────")
    resp = client.get("/api/tokens", params={"search": "TKN"}, headers=hdr(citizen_token))
    ok = resp.status_code == 200
    search_results = resp.json() if ok else []
    report("Search filter returns 200", ok, f"count={len(search_results)}")
    if search_results:
        all_match = all("TKN" in t["token_number"] for t in search_results)
        report("All results contain 'TKN'", all_match)

    # ── 12. GET /api/tokens/{transport_code} — full detail ────────────
    print("\n─── GET /api/tokens/{transport_code} (Detail) ────────")
    if active_tc:
        resp = client.get(f"/api/tokens/{active_tc}", headers=hdr(citizen_token))
        ok = resp.status_code == 200
        report("GET token detail returns 200", ok, f"status={resp.status_code}")

        if ok:
            detail = resp.json()
            # Header fields
            report("Has transport_code", detail.get("transport_code") == active_tc)
            report("Has token_number", "token_number" in detail and detail["token_number"].startswith("TKN-"),
                   detail.get("token_number"))
            report("Has status", "status" in detail, detail.get("status"))
            report("Has valid_from", "valid_from" in detail)
            report("Has valid_till", "valid_till" in detail)

            # Application info
            report("Has application_id", "application_id" in detail, str(detail.get("application_id")))
            report("Has application_number", detail.get("application_number", "").startswith("APP-"),
                   detail.get("application_number"))
            report("Has applicant_name", detail.get("applicant_name") == "Rajesh Patel",
                   detail.get("applicant_name"))
            report("Has property_address", bool(detail.get("property_address")),
                   detail.get("property_address", "")[:50])
            report("Has property_usage", detail.get("property_usage") == "DOMESTIC",
                   detail.get("property_usage"))
            report("Has application_type", detail.get("application_type") == "NEW",
                   detail.get("application_type"))

            # Authority info
            auth = detail.get("authority", {})
            report("Has authority.issued_by", bool(auth.get("issued_by")),
                   auth.get("issued_by"))
            report("Has authority.issued_on", bool(auth.get("issued_on")),
                   str(auth.get("issued_on")))
            report("Has authority.token_generated_from", bool(auth.get("token_generated_from")),
                   auth.get("token_generated_from"))

            # Materials
            materials = detail.get("materials", [])
            report("Has materials", len(materials) > 0, f"count={len(materials)}")
            if materials:
                mat = materials[0]
                mat_fields = {"material_id", "material_name", "unit",
                              "approved_quantity", "consumed_quantity", "remaining_quantity"}
                report("Material has expected fields",
                       mat_fields.issubset(set(mat.keys())),
                       f"fields={sorted(mat.keys())}")
                report("consumed_quantity is 0 initially", mat["consumed_quantity"] == 0)
                report("remaining = approved (no entries yet)",
                       mat["remaining_quantity"] == mat["approved_quantity"])

            report("Has remaining_quantity_pct",
                   isinstance(detail.get("remaining_quantity_pct"), (int, float)),
                   str(detail.get("remaining_quantity_pct")))

            # Vehicle entries (should be empty initially)
            entries = detail.get("vehicle_entries", [])
            report("vehicle_entries is empty initially", len(entries) == 0,
                   f"count={len(entries)}")
    else:
        report("SKIP token detail (no transport code)", False, "no active tokens found")

    # ── 13. Invalid transport code → 400 ──────────────────────────────
    print("\n─── Invalid transport code ───────────────────────────")
    resp = client.get("/api/tokens/INVALID_CODE_XYZ", headers=hdr(citizen_token))
    report("Invalid transport code returns 400", resp.status_code == 400,
           f"status={resp.status_code}")

    # ── 14. Naka logs a vehicle entry ─────────────────────────────────
    print("\n─── Naka Vehicle Entry ───────────────────────────────")
    if active_tc:
        resp = client.post(
            f"/api/naka/{active_tc}/entry",
            json={
                "material_id": ids["mat1_id"],
                "quantity_brought": 50,
                "vehicle_number": "RJ24 AB 4587",
                "remarks": "First delivery of cement",
            },
            headers=hdr(naka_token),
        )
        report("Naka entry POST", resp.status_code == 200, f"{resp.status_code}")
        if resp.status_code != 200:
            print(f"  ERROR: {resp.text}")

        # Second entry
        resp = client.post(
            f"/api/naka/{active_tc}/entry",
            json={
                "material_id": ids["mat2_id"],
                "quantity_brought": 3,
                "vehicle_number": "RJ38 EF 6671",
                "remarks": "Sand delivery",
            },
            headers=hdr(naka_token),
        )
        report("Naka entry POST (2nd)", resp.status_code == 200, f"{resp.status_code}")

    # ── 15. GET token detail again — verify vehicle entries & consumed ─
    print("\n─── Verify Token Detail After Naka Entries ───────────")
    if active_tc:
        resp = client.get(f"/api/tokens/{active_tc}", headers=hdr(citizen_token))
        ok = resp.status_code == 200
        if ok:
            detail = resp.json()

            # Vehicle entries should now have 2
            entries = detail.get("vehicle_entries", [])
            report("vehicle_entries has 2 entries", len(entries) == 2,
                   f"count={len(entries)}")

            if entries:
                entry = entries[0]
                entry_fields = {"id", "vehicle_number", "material_name",
                                "quantity_entered", "entry_at"}
                report("Vehicle entry has expected fields",
                       entry_fields.issubset(set(entry.keys())),
                       f"fields={sorted(entry.keys())}")
                report("vehicle_number is present", bool(entry.get("vehicle_number")),
                       entry.get("vehicle_number"))

            # Materials should show consumed quantities
            materials = detail.get("materials", [])
            mat1 = next((m for m in materials if m["material_id"] == ids["mat1_id"]), None)
            if mat1:
                report("Cement consumed_quantity is 50", mat1["consumed_quantity"] == 50,
                       f"consumed={mat1['consumed_quantity']}")
                report("Cement remaining = approved - consumed",
                       mat1["remaining_quantity"] == mat1["approved_quantity"] - 50,
                       f"remaining={mat1['remaining_quantity']}")

            mat2 = next((m for m in materials if m["material_id"] == ids["mat2_id"]), None)
            if mat2:
                report("Sand consumed_quantity is 3", mat2["consumed_quantity"] == 3,
                       f"consumed={mat2['consumed_quantity']}")

            # remaining_quantity_pct should be < 100 now
            pct = detail.get("remaining_quantity_pct")
            report("remaining_quantity_pct < 100", pct is not None and pct < 100,
                   f"pct={pct}")
        else:
            report("GET token detail after entries", False, f"status={resp.status_code}")

    # ── 16. GET /api/applications/{id}/tokens ─────────────────────────
    print("\n─── GET /api/applications/{id}/tokens ────────────────")
    resp = client.get(f"/api/applications/{app_id}/tokens", headers=hdr(citizen_token))
    ok = resp.status_code == 200
    app_tokens = resp.json() if ok else []
    report("Application tokens returns 200", ok, f"count={len(app_tokens)}")
    if app_tokens:
        report("Has 2 tokens (2 phases)", len(app_tokens) == 2, f"count={len(app_tokens)}")

    # ── 17. GET /api/applications/{id} — tokens in response ──────────
    print("\n─── Application Detail with Tokens ───────────────────")
    resp = client.get(f"/api/applications/{app_id}", headers=hdr(citizen_token))
    ok = resp.status_code == 200
    if ok:
        app_data = resp.json()
        embedded_tokens = app_data.get("tokens", [])
        report("Application has 'tokens' field", "tokens" in app_data)
        report("Embedded tokens count matches", len(embedded_tokens) == 2,
               f"count={len(embedded_tokens)}")
        if embedded_tokens:
            report("Embedded token has transport_code",
                   bool(embedded_tokens[0].get("transport_code")))
            report("Embedded token has token_number",
                   embedded_tokens[0].get("token_number", "").startswith("TKN-"),
                   embedded_tokens[0].get("token_number"))
    else:
        report("GET application detail", False, f"status={resp.status_code}")

    # ── 18. NAKA_INCHARGE cannot access /tokens ───────────────────────
    print("\n─── Access Control ───────────────────────────────────")
    resp = client.get("/api/tokens", headers=hdr(naka_token))
    report("NAKA cannot GET /tokens", resp.status_code == 403,
           f"status={resp.status_code}")

    if active_tc:
        resp = client.get(f"/api/tokens/{active_tc}", headers=hdr(naka_token))
        report("NAKA cannot GET /tokens/{tc}", resp.status_code == 403,
               f"status={resp.status_code}")

    # ═══════════════════════════════════════════════════════════════════
    #  SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 65)
    print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 65)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
