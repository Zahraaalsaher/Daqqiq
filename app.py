

import streamlit as st
import pymupdf
import re

st.set_page_config(page_title="دقّق | DAQQIQ - Beta")

st.title("دقّق | DAQQIQ")
st.write("مساعد لمراجعة عقود العمل السعودية")
st.caption("نسخة تجريبية تعليمية وليست استشارة قانونية")

def analyze_contract(text):
    rules = [
        {
            "name": "فترة التجربة",
            "pattern": r"probation period of\s+(\d+)\s+days",
            "reference": "المادة 53",
            "limit": 180
        },
        {
            "name": "ساعات العمل",
            "pattern": r"(\d+)\s+actual hours per day,\s*(\d+)\s+days per week",
            "reference": "المواد 98 و99 و100"
        },
        {
            "name": "الإجازة السنوية",
            "pattern": r"(\d+)\s+days of paid annual leave",
            "reference": "المادة 109",
            "limit": 21
        }
    ]

    results = []

    for rule in rules:
        match = re.search(rule["pattern"], text, re.I)

        if not match:
            continue

        name = rule["name"]

        if name == "فترة التجربة":
            days = int(match.group(1))
            issue = days > 180
            status = "تعارض محتمل" if issue else "لم يُرصد تجاوز للمدة"
            explanation = (
                f"مدة التجربة {days} يومًا، وتتجاوز 180 يومًا."
                if issue else
                f"مدة التجربة {days} يومًا، ولا تتجاوز 180 يومًا."
            )
            recommendation = (
                "اطلب تعديل مدة التجربة قبل التوقيع."
                if issue else
                "تحقق من بقية شروط فترة التجربة."
            )

        elif name == "ساعات العمل":
            daily = int(match.group(1))
            weekly = daily * int(match.group(2))
            issue = daily > 8 or weekly > 48
            status = "تحتاج مراجعة" if issue else "لم يُرصد تجاوز للحد المعتاد"
            explanation = (
                f"العقد يذكر {daily} ساعات يوميًا و{weekly} ساعة أسبوعيًا. "
                "قد تنطبق استثناءات نظامية."
            )
            recommendation = "تحقق من طبيعة العمل والاستثناءات المطبقة."

        else:
            days = int(match.group(1))
            issue = days < 21
            status = "تعارض محتمل" if issue else "تحتاج تحقق من مدة الخدمة"
            explanation = (
                f"الإجازة السنوية {days} يومًا. "
                "الحد الأدنى المعتاد 21 يومًا، وقد يزيد حسب مدة الخدمة."
            )
            recommendation = "تحقق من استحقاق الإجازة السنوية."

        results.append({
            "name": name,
            "status": status,
            "explanation": explanation,
            "recommendation": recommendation,
            "reference": rule["reference"]
        })

    if "salary and allowances" in text.lower():
        missing = any(
            phrase in text.lower()
            for phrase in ["determined later", "no amount is stated"]
        )
        results.append({
            "name": "الراتب والبدلات",
            "status": "معلومات ناقصة" if missing else "تم ذكر الراتب والبدلات، وتحتاج مراجعة",
            "explanation": (
                "لم يتم تحديد مبلغ الراتب والبدلات بوضوح."
                if missing else
                "وردت معلومات عن الراتب والبدلات في العقد، لكن يلزم التأكد من اكتمالها وصحتها."
            ),
            "recommendation": "اطلب توضيح الراتب والبدلات كتابةً." if missing else "راجع المبالغ المذكورة وتأكد من اتفاق الطرفين عليها كتابةً.",
            "reference": "المادة 52"
        })

    return results

def get_original_clause(text, name):
    keywords = {
        "فترة التجربة": "probation period",
        "ساعات العمل": "working hours",
        "الإجازة السنوية": "annual leave",
        "الراتب والبدلات": "salary and allowances"
    }

    keyword = keywords[name]
    pattern = (
        r"Clause\s+\d+\s*[-–—:]\s*.*?"
        r"(?=Clause\s+\d+\s*[-–—:]|EDUCATIONAL TEST ONLY|$)"
    )

    clauses = re.findall(pattern, text, re.I | re.S)

    for clause in clauses:
        if keyword in clause.lower():
            return clause.strip()

    return "تعذر تحديد نص البند الأصلي."

uploaded_file = st.file_uploader(
    "ارفعي عقد العمل بصيغة PDF",
    type=["pdf"]
)

if uploaded_file is not None:
    try:
        document = pymupdf.open(
            stream=uploaded_file.getvalue(),
            filetype="pdf"
        )
        text = "\n".join(page.get_text() for page in document)
        document.close()

        if not text.strip():
            st.warning("تعذر استخراج النص من ملف PDF.")
        else:
            st.success("تمت قراءة العقد بنجاح")
            results = analyze_contract(text)

            st.subheader("تقرير مراجعة العقد")

            if not results:
                st.warning("لم يتم التعرف على البنود المدعومة.")

            for item in results:
                with st.expander(item["name"], expanded=True):
                    st.write("**النص الأصلي:**")
                    st.write(get_original_clause(text, item["name"]))

                    st.write("**الحالة:**", item["status"])
                    st.write("**الشرح:**", item["explanation"])
                    st.write("**التوصية:**", item["recommendation"])
                    st.write("**المرجع:**", item["reference"])

            st.info(
                "هذا فحص أولي بقواعد محددة. عدم ظهور تنبيه "
                "لا يعني سلامة العقد، وقد توجد استثناءات نظامية."
            )

    except Exception:
        st.error("حدث خطأ أثناء قراءة العقد أو تحليله.")
