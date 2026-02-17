"""Quick test: upload a file via media proxy, then download it via the proxy endpoint."""
import requests
import json

BASE = "http://localhost:8000"

# 1. Login
requests.post(f"{BASE}/auth/send-otp", json={"mobile": "9999999999"})
r = requests.post(f"{BASE}/auth/login/otp", json={"mobile": "9999999999", "otp": "123456"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Upload a test file via media proxy
files = {"file": ("test.txt", b"Hello from download proxy test!", "text/plain")}
data = {"category": "test", "entity_id": "1"}
r = requests.post(f"{BASE}/api/media/upload", headers=headers, files=files, data=data)
upload_resp = r.json()
print("Upload response:", json.dumps(upload_resp, indent=2))

# 3. The access_url should now be a backend proxy URL
access_url = upload_resp["access_url"]
print(f"\nAccess URL: {access_url}")
assert "/api/media/file/" in access_url, "access_url should be a backend proxy URL"
assert "token=" in access_url, "access_url should contain a signed token"

# 4. Download through the proxy
r = requests.get(access_url)
print(f"\nDownload status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type')}")
print(f"Content: {r.text}")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
assert r.text == "Hello from download proxy test!", f"Content mismatch: {r.text}"

# 5. Test expired/tampered token
tampered_url = access_url.replace("token=", "token=bad")
r = requests.get(tampered_url)
print(f"\nTampered token status: {r.status_code} (expected 403)")
assert r.status_code == 403, f"Expected 403, got {r.status_code}"

print("\n✅ Download proxy test PASSED")
