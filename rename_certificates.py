import fitz
import os
import re

folder = "certificates"

def clean_filename(name):

    name = name.strip()

    # حذف الرموز غير المسموحة
    name = re.sub(r'[\\/*?:"<>|]', "", name)

    # تحويل الفراغات إلى _
    name = re.sub(r"\s+", "_", name)

    return name

for filename in os.listdir(folder):

    if filename.lower().endswith(".pdf"):

        filepath = os.path.join(folder, filename)

        pdf = fitz.open(filepath)

        text = ""

        for page in pdf:
            text += page.get_text()

        pdf.close()

        lines = text.split("\n")

        student_name = None

        for line in lines:

            line = line.strip()

            # البحث عن سطر عربي طويل
            arabic_letters = re.findall(r'[\u0600-\u06FF]', line)

            if len(arabic_letters) > 15:

                # استبعاد الأسطر غير المطلوبة
                excluded_words = [
                    "سلطنة",
                    "المدرسة",
                    "الفصل",
                    "الصف",
                    "وزارة",
                    "التعليم",
                    "محافظة",
                    "كشف",
                    "درجات"
                ]

                if not any(word in line for word in excluded_words):

                    student_name = line
                    break

        if student_name:

            clean_name = clean_filename(student_name)

            new_path = os.path.join(folder, f"{clean_name}.pdf")

            if filepath != new_path:
                os.rename(filepath, new_path)

            print(f"تمت إعادة التسمية: {filename} → {clean_name}.pdf")

        else:

            print(f"لم يتم العثور على اسم عربي داخل: {filename}")