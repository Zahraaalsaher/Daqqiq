

import streamlit as st
import pymupdf
import re

st.set_page_config(page_title="دقّق | DAQQIQ - Beta")

language = st.radio(
    "Language",
    ["Arabic", "English"],
    horizontal=True
)
st.markdown("""
<style>
.stApp {
    background-color: #F7F9FC;
    color: #102A43;
}

h1, h2, h3 {
    color: #102A43 !important;
}

.stButton > button {
    background-color: #E7BE70;
    color: #102A43;
    border-radius: 10px;
    border: none;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<div style="background-color:#102A43; padding:35px;
            border-radius:16px; text-align:center; direction:rtl;">
    <div style="color:#E7BE70; font-size:48px; font-weight:bold; text-align:center; padding:10px 0;">
    دقّق | DAQQIQ
</div>
    <p style="color:white; font-size:20px;">
        افهم عقد عملك قبل التوقيع
    </p>
    <p style="color:#DDE6EE; font-size:15px;">
        مساعد ذكي لمراجعة بنود عقود العمل السعودية
    </p>
</div>
""", unsafe_allow_html=True)

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

st.markdown("### ابدأ مراجعة عقدك")
st.write("ارفع عقد العمل بصيغة PDF، وسنساعدك في فهم البنود التي تحتاج إلى مراجعة.")

uploaded_file = st.file_uploader(
    "اختر ملف عقد العمل (PDF)",
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
            safe_count = sum(
                item["status"].startswith("لم يُرصد")
                for item in results
            )

            issue_count = sum(
                item["status"] in ["تعارض محتمل", "معلومات ناقصة"]
                for item in results
            )

            review_count = len(results) - safe_count - issue_count

            col1, col2, col3 = st.columns(3)

            col1.metric("لم يُرصد تجاوز", safe_count)
            col2.metric("تحتاج مراجعة", review_count)
            col3.metric("تنبيهات محتملة", issue_count)
            st.markdown("""
<div style="background-color:#102A43; padding:16px;
            border-radius:10px; text-align:center; margin-top:20px;">
    <div style="color:#E7BE70; font-size:28px; font-weight:bold; text-align:center;">
    تقرير مراجعة العقد
</div>
</div>
""", unsafe_allow_html=True)

            if not results:
                st.warning("لم يتم التعرف على البنود المدعومة.")

            for item in results:
                with st.expander(item["name"], expanded=False):
                    st.write("**النص الأصلي:**")
                    st.write(get_original_clause(text, item["name"]))

                    if item["status"].startswith("لم يُرصد"):
                        st.success("الحالة: " + item["status"])
                    elif item["status"] in ["تعارض محتمل", "معلومات ناقصة"]:
                        st.error("الحالة: " + item["status"])
                    else:
                        st.warning("الحالة: " + item["status"])
                    st.write("**الشرح:**", item["explanation"])
                    st.write("**التوصية:**", item["recommendation"])
                    st.write("**المرجع:**", item["reference"])

            st.info(
                "هذا فحص أولي بقواعد محددة. عدم ظهور تنبيه "
                "لا يعني سلامة العقد، وقد توجد استثناءات نظامية."
            )

    except Exception:
        st.error("حدث خطأ أثناء قراءة العقد أو تحليله.")
