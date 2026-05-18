from flask import Flask, request
import pandas as pd
import os

app = Flask(__name__)

VERIFY_TOKEN = "salma_school_2026"

DATA_FILE = "data/students.xlsx"
CERTIFICATES_FOLDER = "certificates"


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

        print("وصلت رسالة جديدة:")
        print(data)

        return "EVENT_RECEIVED", 200


@app.route("/test-students")
def test_students():

    df = pd.read_excel(DATA_FILE)

    result = []

    for index, row in df.iterrows():

        student_name = str(row["student_name"]).strip()
        guardian_phone = str(row["guardian_phone"]).strip()

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