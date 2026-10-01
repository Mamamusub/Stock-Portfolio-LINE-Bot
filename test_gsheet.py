import os
from dotenv import load_dotenv
import gspread
import sys

load_dotenv()
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
# ------------------------------------

print(f"--- กำลังทดสอบ gspread (Python {sys.version.split()[0]}) ---")

try:
    # 1. ทดสอบการเชื่อมต่อ Service Account
    print("Reading the configured service account credential file...")
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    print("...อ่านไฟล์ .json สำเร็จ")

    # 2. ทดสอบการเปิด Sheet
    print("กำลังเปิด Google Sheet ที่กำหนดไว้")
    sh = gc.open_by_url(SHEET_URL)
    print("...เปิด Sheet สำเร็จ")

    # 3. ทดสอบการอ่านข้อมูล
    worksheet = sh.worksheet("Summarize")
    cell_data = worksheet.acell('A3').value # (ลองอ่านเซลล์ A3)
    print("...อ่านข้อมูลสำเร็จ")

    print("\n--- ✅ [SUCCESS] ---")
    print(f"ข้อมูลตัวอย่างจาก A3: {cell_data}")
    print("--- การเชื่อมต่อ GSheet ของคุณสมบูรณ์แบบ! ---")

except gspread.exceptions.SpreadsheetNotFound:
    print("\n--- [ERROR] ---")
    print("Spreadsheet not found or inaccessible.")
    print("Check the configured spreadsheet URL and share the spreadsheet with the service account.")

except PermissionError:
    print("\n--- [ERROR] ---")
    print("Access denied to the spreadsheet or credential file.")
    print("Share the spreadsheet with the service account and check credential file read permissions.")

except FileNotFoundError:
    print("\n--- [ERROR] ---")
    print("The service account credential file was not found.")
    print("Check that GOOGLE_CREDENTIALS_FILE points to an existing credential JSON file.")

except gspread.exceptions.APIError as error:
    print("\n--- [ERROR] ---")
    if error.code == 403:
        print("Google Sheets/API access denied.")
        print("Check spreadsheet sharing, service account permissions, and required API access.")
    elif error.code == 404:
        print("Spreadsheet or requested Google Sheets resource not found or inaccessible.")
        print("Check the configured spreadsheet URL and service account access.")
    else:
        print("A Google Sheets/API request failed.")
        print("Check API availability, quotas, and service account configuration.")

except Exception:
    print("\n--- [ERROR] ---")
    print("The Google Sheets connection test failed.")
    print("Check the spreadsheet configuration, credential file format, and network connectivity.")
