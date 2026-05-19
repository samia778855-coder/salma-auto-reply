from flask import Flask, request, send_from_directory
import pandas as pd
import os
import requests
from urllib.parse import quote
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "salma_school_2026"

DATA_FILE = "data/students.xlsx"
CERTIFICATES_FOLDER = "certificates"
BASE_URL = "https://salma-auto-reply.onrender.com"
LOG_FILE = "request_logs.csv"
DAILY_LIMIT = 5

WELCOME_MESSAGE = """مرحبًا بكم في خدمة الرد الآلي 
مدرسة سلمى بنت قيس للتعليم الأساسي (5-12) 🌷

للحصول على الشهادة:
يرجى إرسال اسم الطالبة كما هو في الشهادة."""

FOOTER_MESSAGE = "\n\nهذه الرسالة آلية من مدرسة سلمى بنت قيس للتعليم الأساسي (5-12)."


def normalize_phone(phone):
    phone = str(phone).strip()
    phone = phone.replace(" ", "").replace("+", "")

    if phone.startswith("968"):
        return phone

    if len(phone) == 8:
        return "968" + phone

    return phone


def load_students():
    df = pd.read_excel(DATA_FILE)
    df["student_name"] = df["student_name"].astype(str).str.strip()
    df["guardian_phone"] = df["guardian_phone"].apply(normalize_phone)
    return df


def send_whatsapp_text(to, body):
    access_token = os.getenv("ACCESS_TOKEN")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")

    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body}
    }

    response = requests.post(url, headers=headers, json=payload)
    print("حالة إرسال النص:", response.status_code)
    print(response.text)


def send_whatsapp_document(to, pdf_url, filename):
    access_token = os.getenv("ACCESS_TOKEN")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")

    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "link": pdf_url,
            "filename": filename
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print("حالة إرسال الشهادة:", response.status_code)
    print(response.text)
    return response.status_code


def log_request(student_name, phone, status):
    now = datetime.now()
    row = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "student_name": student_name,
        "phone": phone,
        "status": status
    }

    df = pd.DataFrame([row])

    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")


def daily_request_count(student_name):
    if not os.path.exists(LOG_FILE):
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv(LOG_FILE)

    count = df[
        (df["date"] == today) &
        (df["student_name"] == student_name) &
        (df["status"] == "sent")
    ]

    return len(count)


@app.route("/")
def home():
    return "سلمى بنت قيس للرد الآلي يعمل بنجاح"


@app.route("/certificate/<filename>")
def get_certificate(filename):
    return send_from_directory(CERTIFICATES_FOLDER, filename)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()

        try:
            value = data["entry"][0]["changes"][0]["value"]

            if "messages" in value:
                message = value["messages"][0]
                sender_phone = normalize_phone(message["from"])
                message_text = message["text"]["body"].strip()

                print("رقم المرسل:", sender_phone)
                print("نص الرسالة:", message_text)

                if message_text in ["مرحبا", "السلام عليكم", "السلام عليكم ورحمة الله", "اهلا", "أهلا", "هلا"]:
                    send_whatsapp_text(sender_phone, WELCOME_MESSAGE)
                    return "EVENT_RECEIVED", 200

                df = load_students()
                matched = df[df["student_name"] == message_text]

                print("عدد النتائج المطابقة:", len(matched))

                if matched.empty:
                    log_request(message_text, sender_phone, "not_found")
                    send_whatsapp_text(
                        sender_phone,
                        "عذرًا، لم يتم العثور على بيانات الطالبة. يرجى كتابة الاسم مطابقًا تمامًا كما هو في الشهادة."
                        + FOOTER_MESSAGE
                    )

                else:
                    student = matched.iloc[0]
                    student_name = student["student_name"]
                    guardian_phone = student["guardian_phone"]

                    print("رقم ولي الأمر المسجل:", guardian_phone)

                    if sender_phone != guardian_phone:
                        log_request(student_name, sender_phone, "rejected_phone")
                        send_whatsapp_text(
                            sender_phone,
                            "عذرًا، لا يمكن إرسال الشهادة لأن رقم واتساب المستخدم غير مسجل كرقم ولي أمر لهذه الطالبة."
                            + FOOTER_MESSAGE
                        )
                        return "EVENT_RECEIVED", 200

                    if daily_request_count(student_name) >= DAILY_LIMIT:
                        log_request(student_name, sender_phone, "daily_limit")
                        send_whatsapp_text(
                            sender_phone,
                            f"عذرًا، تم طلب شهادة الطالبة {student_name} أكثر من 5 مرات اليوم. يرجى المحاولة في يوم آخر."
                            + FOOTER_MESSAGE
                        )
                        return "EVENT_RECEIVED", 200

                    pdf_filename = student_name + ".pdf"
                    certificate_path = os.path.join(CERTIFICATES_FOLDER, pdf_filename)

                    if os.path.exists(certificate_path):
                        encoded_filename = quote(pdf_filename)
                        pdf_url = f"{BASE_URL}/certificate/{encoded_filename}"

                        send_whatsapp_text(
                            sender_phone,
                            f"مرحبًا ولي أمر الطالبة {student_name} 🌷\nتم التحقق من البيانات، وجارٍ إرسال الشهادة الإلكترونية."
                        )

                        status_code = send_whatsapp_document(
                            sender_phone,
                            pdf_url,
                            pdf_filename
                        )

                        if status_code == 200:
                            log_request(student_name, sender_phone, "sent")
                            send_whatsapp_text(
                                sender_phone,
                                "تم إرسال الشهادة الإلكترونية بنجاح 🌷\nمع تمنيات مدرسة سلمى بنت قيس لطالباتها مزيداً من التفوق والتميز."
                                + FOOTER_MESSAGE
                            )
                        else:
                            log_request(student_name, sender_phone, "send_failed")

                    else:
                        print("ملف الشهادة غير موجود:", pdf_filename)
                        log_request(student_name, sender_phone, "certificate_missing")
                        send_whatsapp_text(
                            sender_phone,
                            "تم التحقق من بياناتك، لكن ملف الشهادة غير موجود حاليًا. يرجى مراجعة إدارة المدرسة."
                            + FOOTER_MESSAGE
                        )

            else:
                print("وصل Webhook بدون رسالة مستخدم")

        except Exception as e:
            print("خطأ في قراءة الرسالة:", e)
            print(data)

        return "EVENT_RECEIVED", 200


@app.route("/test-students")
def test_students():
    df = load_students()
    result = []

    for index, row in df.iterrows():
        student_name = row["student_name"]
        guardian_phone = row["guardian_phone"]
        certificate_path = os.path.join(CERTIFICATES_FOLDER, student_name + ".pdf")

        result.append({
            "student_name": student_name,
            "guardian_phone": guardian_phone,
            "certificate_exists": os.path.exists(certificate_path)
        })

    return result


if __name__ == "__main__":
    app.run(debug=True)
