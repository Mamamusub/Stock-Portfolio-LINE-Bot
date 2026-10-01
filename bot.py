# --- 1. IMPORT LIBRARY ---
import os
import base64
import hashlib
import hmac
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort
import requests
import gspread
import json
import urllib.parse
# --- 2. SETTINGS (เอาของเดิมมา) ---
load_dotenv()

# Portfolio layout: CASH and TOTAL are excluded from stock loops.
FUND_COUNT = 1
STOCK_COUNT = 9
CASH_COUNT = 1
START_ROW_FUND = 3
START_ROW_STOCK = START_ROW_FUND + FUND_COUNT
CASH_ROW = START_ROW_STOCK + STOCK_COUNT
TOTAL_ROW = CASH_ROW + 1


CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

_required_configuration = {
    "LINE_CHANNEL_TOKEN": CHANNEL_TOKEN,
    "LINE_CHANNEL_SECRET": CHANNEL_SECRET,
    "GOOGLE_SHEET_URL": SHEET_URL,
    "GOOGLE_CREDENTIALS_FILE": CREDENTIALS_FILE,
}
_missing_configuration = [
    name for name, value in _required_configuration.items()
    if not value or not value.strip()
]
if _missing_configuration:
    raise RuntimeError(
        "Missing required environment variables: " + ", ".join(_missing_configuration)
    )

REQUEST_TIMEOUT = (5, 15)
logger = logging.getLogger(__name__)

# --- 3. สร้าง Web App ---
app = Flask(__name__)

# (ปรับ data_format ให้คอลัมน์ตรงกัน)

# (แสดง "Total" สำหรับทุกคำสั่ง ยกเว้น "สัดส่วน")

def get_portfolio_data(command):
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.worksheet("Summarize")

        # ... (ส่วน if command == "กำไร", "สัดส่วน", "จำนวนเงิน" เหมือนเดิม) ...
        if command == "กำไร":
            line_message_content = "--- สรุปกำไรพอร์ต ---\n"
            col1 = 'D'
            col2 = 'E'
            data_format = "{ticker:<8} : {val1:>10} ({val2:^8}%)"
        elif command == "สัดส่วน":
            line_message_content = "--- สรุปสัดส่วนพอร์ต ---\n"
            col1 = 'C'
            col2 = None
            data_format = "{ticker:<8} : {val1:>10}"
        elif command == "จำนวนเงิน":
            line_message_content = "--- สรุปจำนวนเงินลงทุน ---\n"
            col1 = 'B'
            col2 = None
            data_format = "{ticker:<8} : {val1:>10}"
        else:
            return f"Internal Error: ไม่รู้จักคำสั่ง {command}"

        # --- 3. Loop กองทุน (FUND) ---
        line_message_content += "\n--- ข้อมูลกองทุน ---\n"
        for i in range(FUND_COUNT):
            current_row = START_ROW_FUND + i
            # ... (โค้ดดึงข้อมูลเหมือนเดิม) ...
            ticker = worksheet.acell(f'A{current_row}').value
            val1 = worksheet.acell(f'{col1}{current_row}').value
            if col2:
                val2 = worksheet.acell(f'{col2}{current_row}').value
                data_line = data_format.format(ticker=ticker, val1=val1, val2=val2)
            else:
                data_line = data_format.format(ticker=ticker, val1=val1)
            line_message_content += data_line + "\n"

        # --- 4. Loop หุ้น (STOCK) ---
        line_message_content += f"\n--- ข้อมูลหุ้น ---\n"
        for i in range(STOCK_COUNT):
            current_row = START_ROW_STOCK + i
            # ... (โค้ดดึงข้อมูลเหมือนเดิม) ...
            ticker = worksheet.acell(f'A{current_row}').value
            val1 = worksheet.acell(f'{col1}{current_row}').value
            if col2:
                val2 = worksheet.acell(f'{col2}{current_row}').value
                data_line = data_format.format(ticker=ticker, val1=val1, val2=val2)
            else:
                data_line = data_format.format(ticker=ticker, val1=val1)
            line_message_content += data_line + "\n"

        if command != "สัดส่วน":
            line_message_content += "------------------------\n" # เพิ่มเส้นคั่น

            # ดึงข้อมูลจากแถว Total ที่คำนวณไว้
            ticker = worksheet.acell(f'A{TOTAL_ROW}').value # (ควรอ่านได้ "Total")
            val1 = worksheet.acell(f'{col1}{TOTAL_ROW}').value

            if col2: # (สำหรับ "กำไร")
                val2 = worksheet.acell(f'{col2}{TOTAL_ROW}').value
                data_line = data_format.format(ticker=ticker, val1=val1, val2=val2)
            else: # (สำหรับ "จำนวนเงิน")
                data_line = data_format.format(ticker=ticker, val1=val1)

            line_message_content += data_line + "\n"

        # --- 6. จบ ---
        line_message_content += "------------------------"
        return line_message_content

    except Exception:
        logger.error("Unable to read portfolio data.")
        return "เกิดข้อผิดพลาดตอนอ่าน GSheet กรุณาลองใหม่ภายหลัง"

# --- 5. ฟังก์ชันส่งข้อความ "ตอบกลับ" (Reply API) ---

# (มันสามารถส่ง "รายการ" ของข้อความได้ เช่น text, image)

def send_reply(reply_token, messages_list):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_TOKEN}'
    }
    payload = {
        'replyToken': reply_token,
        'messages': messages_list  # <-- รับ "รายการ" ของข้อความ
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status() # <-- ตรวจสอบ Error (เช่น 401, 403)

        logger.info("LINE reply accepted.")
    except requests.exceptions.RequestException:
        logger.error("LINE reply request failed.")
    except Exception:
        logger.error("Unable to prepare LINE reply.")

# --- 6. ทางเข้าสำหรับ LINE (Webhook) ---
# นี่คือ URL ที่เราตั้งใน LINE Developers (เช่น /webhook)

def get_percent_data_for_chart():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.worksheet("Summarize")

        labels = []
        data = []

        # --- Loop กองทุน ---
        for i in range(FUND_COUNT):
            current_row = START_ROW_FUND + i
            labels.append(worksheet.acell(f'A{current_row}').value)
            percent_str = worksheet.acell(f'C{current_row}').value
            data.append(float(percent_str.strip(' %')))

        # --- Loop หุ้น ---
        for i in range(STOCK_COUNT):
            current_row = START_ROW_STOCK + i
            labels.append(worksheet.acell(f'A{current_row}').value)
            percent_str = worksheet.acell(f'C{current_row}').value
            data.append(float(percent_str.strip(' %')))

        return labels, data

    except Exception:
        logger.error("Unable to read chart data.")
        return None, None

# (แสดงผลเป็น % และซ่อน Total)

# (เป็นกราฟวงกลมเต็ม ไม่มี่รูตรงกลาง, แสดง %, และไม่มี Total)

def get_pie_chart_url(labels, data):
    # สร้าง config ของกราฟวงกลม
    chart_config = {
        "type": "pie", # --- (!!! แก้ไขตรงนี้: เปลี่ยนเป็น pie !!!) ---
        "data": {
            "labels": labels,
            "datasets": [{
                "data": data,
                "backgroundColor": [ # (ตัวอย่างสี - QuickChart จะสุ่มให้ถ้าไม่กำหนด)
                    "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                    "#FF9900", "#C9CBCF", "#6A5ACD", "#CD5C5C", "#20B2AA"
                ]
            }]
        },
        "options": {
            "plugins": {
                "datalabels": { # แสดงตัวเลข % บนกราฟ
                    "color": "#fff",
                    "font": { # ปรับขนาดตัวอักษร
                        "size": 14,
                        "weight": "bold"
                    },
                    "formatter": "(value, context) => { return context.chart.data.labels[context.dataIndex] + '\\n' + value + '%' }",
                    "anchor": "center",
                    "align": "center",
                }
            }
        }
    }

    # แปลง config เป็น URL ที่ปลอดภัย
    config_string = json.dumps(chart_config)
    encoded_config = urllib.parse.quote(config_string)

    # นี่คือ URL รูปภาพ (https) ที่เราจะส่งให้ LINE
    return f"https://quickchart.io/chart?width=500&height=300&c={encoded_config}&bg=transparent"

# (รองรับการส่งกราฟวงกลม)

# (สร้าง "รายการ" ข้อความ แล้วส่งทีเดียวตอนท้าย)

def handle_text_event(reply_token, user_message):
    messages_to_send = []

    # --- (ตรรกะ if/elif) ---
    if user_message in ["สรุป", "กำไร", "profit"]:
        command_to_run = "กำไร"
    elif user_message in ["สัดส่วน", "percent"]:
        command_to_run = "สัดส่วน"
    elif user_message in ["จำนวนเงิน", "invested"]:
        command_to_run = "จำนวนเงิน"
    elif user_message == "สวัสดี":
        command_to_run = "สวัสดี"
    elif user_message in ["menu", "เมนู"]:
        command_to_run = "menu"
    else:
        command_to_run = "ไม่รู้จัก"

    # --- (จบตรรกะ) ---

    # --- ทำงานตามคำสั่ง ---

    if command_to_run == "สวัสดี":
        reply_text = "สวัสดีครับ! พิมพ์ 'Menu' เพื่อดูรายการคำสั่งครับ"
        messages_to_send.append({'type': 'text', 'text': reply_text})

    elif command_to_run == "menu":
        reply_text = (
            "--- 📖 รายการคำสั่ง (Menu) 📖 ---\n\n"
            "➡️ Profit / กำไร / สรุป\n"
            "    (ดูสรุปกำไร)\n\n"
            "➡️ Percent / สัดส่วน\n"
            "    (ดูข้อมูลสัดส่วนพอร์ตและกราฟ)\n\n"
            "➡️ Invested / จำนวนเงิน\n"
            "    (ดูเงินลงทุน)\n\n"
            "➡️ Menu / เมนู\n"
            "    (แสดงรายการคำสั่งนี้)"
        )
        messages_to_send.append({'type': 'text', 'text': reply_text})

    elif command_to_run == "ไม่รู้จัก":
        reply_text = f"ไม่เข้าใจคำสั่ง '{user_message}'\nพิมพ์ 'Menu' เพื่อดูรายการคำสั่งครับ"
        messages_to_send.append({'type': 'text', 'text': reply_text})

    elif command_to_run == "สัดส่วน":
        # --- A. สร้างข้อความ "Text" ---
        text_data = get_portfolio_data("สัดส่วน")
        if text_data:
            messages_to_send.append({'type': 'text', 'text': text_data})

        # --- B. สร้างข้อความ "Image" ---
        labels, data = get_percent_data_for_chart()
        if labels and data:
            chart_url = get_pie_chart_url(labels, data)
            messages_to_send.append({
                'type': 'image',
                'originalContentUrl': chart_url,
                'previewImageUrl': chart_url
            })

        if not text_data and not labels:
            messages_to_send.append({'type': 'text', 'text': 'เกิดข้อผิดพลาดในการดึงข้อมูล "สัดส่วน"'})

    else:
        # (ถ้าเป็น "กำไร" หรือ "จำนวนเงิน")
        command_to_run_text = command_to_run
        reply_text = get_portfolio_data(command_to_run_text)
        if reply_text:
            messages_to_send.append({'type': 'text', 'text': reply_text})
        else:
            messages_to_send.append({'type': 'text', 'text': 'เกิดข้อผิดพลาดในการดึงข้อมูล'})

    # --- (ส่ง "List ข้อความ" ทั้งหมดในครั้งเดียว) ---
    if messages_to_send:
        send_reply(reply_token, messages_to_send)

@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data(cache=True)
    signature = request.headers.get("X-Line-Signature")
    expected_signature = base64.b64encode(
        hmac.new(CHANNEL_SECRET.encode("utf-8"), raw_body, hashlib.sha256).digest()
    )
    if not signature or not hmac.compare_digest(
        expected_signature, signature.encode("utf-8")
    ):
        logger.warning("Webhook signature rejected.")
        abort(403)

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        logger.warning("Malformed webhook payload.")
        abort(400)

    for event in data["events"]:
        if not isinstance(event, dict) or event.get("type") != "message":
            continue
        message = event.get("message")
        if not isinstance(message, dict) or message.get("type") != "text":
            continue
        text = message.get("text")
        reply_token = event.get("replyToken")
        if not isinstance(text, str) or not isinstance(reply_token, str) or not reply_token:
            continue
        try:
            handle_text_event(reply_token, text.strip().lower())
        except Exception:
            logger.error("Unable to process text event.")
            send_reply(reply_token, [{
                "type": "text",
                "text": "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่ภายหลัง",
            }])

    return "OK", 200
