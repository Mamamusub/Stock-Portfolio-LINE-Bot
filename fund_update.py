## SETTING
import os
from dotenv import load_dotenv
import gspread
import requests

load_dotenv()

# Portfolio layout: CASH and TOTAL are excluded from stock loops.
FUND_COUNT = 1
STOCK_COUNT = 9
CASH_COUNT = 1
START_ROW_FUND = 3
START_ROW_STOCK = START_ROW_FUND + FUND_COUNT
CASH_ROW = START_ROW_STOCK + STOCK_COUNT
TOTAL_ROW = CASH_ROW + 1


# --- (1) G-SHEET SETTING ---
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

# --- (2) LINE SETTING ---
CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN")
YOUR_USER_ID = os.getenv("LINE_USER_ID")

## CONNECTION
try:
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    sh = gc.open_by_url(SHEET_URL)
    worksheet = sh.worksheet('Summarize')
    print(f"เชื่อมต่อสำเร็จ! เข้าถึงแท็บ: '{worksheet.title}'")

except Exception:
    print(f"---!!! เกิดข้อผิดพลาดตอนเชื่อมต่อ GSheet !!!---")
    exit()

# --- 3. อ่านข้อมูลสำคัญจาก Sheet ---

width = 50
print("\n--- เริ่มอ่านข้อมูลพอร์ต (สรุปกำไร) ---".center(width))

FUND_PROFIT = {}
STOCK_PROFIT = {}

line_message_content = f"--- สรุปตอนตลาดปิด ---\n"

try:

    # --- 2. Loop อ่านข้อมูลกองทุน (FUND) ---
    print("\n--- ข้อมูลกองทุน (กำไร) ---".center(width))
    line_message_content += "\n--- ข้อมูลกองทุน (กำไร) ---\n"

    for i in range(FUND_COUNT):
        current_row = START_ROW_FUND + i

        ticker = worksheet.acell(f'A{current_row}').value
        profit_thb = worksheet.acell(f'D{current_row}').value
        profit_percent = worksheet.acell(f'E{current_row}').value

        FUND_PROFIT[ticker] = {'profit_thb': profit_thb, 'profit_percent': profit_percent}
        data_line = f"{ticker:<8} : {profit_thb:>8} ({profit_percent:^8}%)"

        print(data_line)
        line_message_content += data_line + "\n"

    # --- 3. Loop อ่านข้อมูลหุ้น (STOCK) ---
    print(f"\n--- ข้อมูลหุ้น (กำไร) ---".center(width))
    line_message_content += "\n--- ข้อมูลหุ้น (กำไร) ---\n"

    for i in range(STOCK_COUNT):
        current_row = START_ROW_STOCK + i

        ticker = worksheet.acell(f'A{current_row}').value
        profit_thb = worksheet.acell(f'D{current_row}').value
        profit_percent = worksheet.acell(f'E{current_row}').value

        STOCK_PROFIT[ticker] = {'profit_thb': profit_thb, 'profit_percent': profit_percent}
        data_line = f"{ticker:<8} : {profit_thb:>8} ({profit_percent:^8}%)"

        print(data_line)
        line_message_content += data_line + "\n"
    line_message_content += "------------------------"

    print("\n--- อ่านข้อมูลสำเร็จ ---".center(width))

except Exception:
    print(f"---!!! เกิดข้อผิดพลาดตอนอ่านข้อมูล !!!---")
    line_message_content = "เกิดข้อผิดพลาดตอนอ่าน GSheet กรุณาลองใหม่ภายหลัง"
# --- 4. ส่งแจ้งเตือนไปที่ LINE ---
print("\n--- กำลังส่ง LINE ---".center(width))

try:
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_TOKEN}'
    }

    payload = {
        'to': YOUR_USER_ID,
        'messages': [
            {
                'type': 'text',
                'text': line_message_content # (ใช้ข้อความ "สรุปกำไร" ที่เราสร้างไว้)
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=(5, 15))
    response.raise_for_status()

    print("--- ส่ง LINE สำเร็จ! ---".center(width))

except Exception:
    print(f"---!!! เกิดข้อผิดพลาดตอนส่ง LINE !!!---")

