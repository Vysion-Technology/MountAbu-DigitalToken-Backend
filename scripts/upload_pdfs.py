import asyncio
import httpx
import os
import mimetypes

# Configuration
BASE_URL = "http://localhost:8000/api"
PDF_DIR = "PDFs"


async def upload_pdf(client, app_id, file_path):
    filename = os.path.basename(file_path)
    print(f"Uploading {filename}...")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/pdf"

    try:
        with open(file_path, "rb") as f:
            files = {"document": (filename, f, mime_type)}
            # We must specify a document type. Since these are generic PDFs,
            # we'll map them or default to SUPPORTING_DOCUMENTS.
            # Actually, let's just use SUPPORTING_DOCUMENTS for all for this bulk tool
            data = {"document_type": "SUPPORTING_DOCUMENTS"}

            resp = await client.post(
                f"/applications/{app_id}/document", files=files, data=data
            )

            if resp.status_code == 200:
                print(f"Success: {filename}")
            else:
                print(f"Failed {filename}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error uploading {filename}: {e}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Upload PDFs to an application.")
    parser.add_argument("app_id", help="Application ID to upload to")
    parser.add_argument(
        "paths",
        nargs="*",
        help="File or Directory paths to upload. Defaults to 'PDFs' directory if not matched.",
    )
    parser.add_argument(
        "--mobile", default="9301871952", help="Mobile number for authentication"
    )

    args = parser.parse_args()

    app_id = args.app_id
    mobile = args.mobile

    # Determine paths to upload
    targets = []
    if not args.paths:
        # Default to PDFs dir if it exists
        if os.path.exists("PDFs"):
            targets.append("PDFs")
        else:
            print("No paths provided and 'PDFs' directory not found.")
            return
    else:
        targets = args.paths

    # Auth first to get token
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Login
        print(f"Logging in with {mobile}...")
        # Send OTP first just in case
        await client.post("/auth/send-otp", json={"mobile": mobile})

        resp = await client.post(
            "/auth/login/otp", json={"mobile": mobile, "otp": "123456"}
        )
        if resp.status_code != 200:
            # Try signup if login fails
            resp = await client.post(
                "/auth/signup",
                json={"mobile": mobile, "otp": "123456", "name": "Auto User"},
            )

        if resp.status_code != 200:
            print(f"Auth failed: {resp.text}")
            return

        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Now upload files
        async with httpx.AsyncClient(
            base_url=BASE_URL, headers=headers, timeout=60.0
        ) as app_client:
            for target in targets:
                if os.path.isdir(target):
                    print(f"Scanning directory: {target}")
                    for filename in os.listdir(target):
                        if filename.lower().endswith(".pdf"):
                            await upload_pdf(
                                app_client, app_id, os.path.join(target, filename)
                            )
                elif os.path.isfile(target):
                    await upload_pdf(app_client, app_id, target)
                else:
                    print(f"Target not found: {target}")


if __name__ == "__main__":
    asyncio.run(main())
