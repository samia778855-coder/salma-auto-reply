from flask import Flask, request
import pandas as pd
import os

app = Flask(__name__)

VERIFY_TOKEN = "salma_school_2026"

DATA_FILE = "data/students.xlsx"
CERTIFICATES_FOLDER = "certificates"


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


@app.route("/")
def home():
    return "سلمى بنت قيس للرد الالي يعمل بنجاح"


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

                df = load_students()

                matched = df[df["student_name"] == message_text]

                if matched.empty:
                    print("لم يتم العثور على الطالبة في ملف Excel")
                else:
                    student = matched.iloc[0]
                    guardian_phone = student["guardian_phone"]

                    if sender_phone == guardian_phone:
                        print("تم التحقق الأمني بنجاح")
                        print("يسمح بإرسال الشهادة")
                    else:
                        print("رفض الطلب: رقم المرسل غير مطابق لرقم ولي الأمر")
                        print("رقم ولي الأمر المسجل:", guardian_phone)

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

        certificate_path = os.path.join(
            CERTIFICATES_FOLDER,
            student_name + ".pdf"
        )

        result.append({
            "student_name": student_name,
            "guardian_phone": guardian_phone,
            "certificate_exists": os.path.exists(certificate_path)
        })

    return result


if __name__ == "__main__":
    app.run(debug=True)