import streamlit as st
import pymupdf
import re

st.set_page_config(page_title="دقّق | DAQQIQ")

st.title("دقّق | DAQQIQ")
st.write("مساعد لمراجعة عقود العمل السعودية")
st.caption("نسخة تجريبية تعليمية - مراجعة أولية وليست استشارة قانونية")

def analyze_contract(text):
    results = []

    probation = re.search(
        r"probation period of\s+(\d+)\s+days",
        text, re.I
    )
    if probation:
        days = int(probation.group(1))
        results.append((
            "فترة التجربة",
            "تعارض محتمل" if days > 180 else "لم يُرصد تجاوز للمدة",
            "المادة 53"
        ))

    hours = re.search(
        r"(\d+)\s+actual hours per day,\s*(\d+)\s+days per week",
        text, re.I
    )
    if hours:
        daily = int(hours.group(1))
        weekly = daily * int(hours.group(2))
        results.append((
            "ساعات العمل",
            "تحتاج مراجعة" if daily > 8 or weekly > 48 else "لم يُرصد تجاوز للحد المعتاد",
            "المواد 98 و99 و100"
        ))

    leave = re.search(
        r"(\d+)\s+days of paid annual leave",
        text, re.I
    )
    if leave:
        days = int(leave.group(1))
        results.append((
            "الإجازة السنوية",
            "تعارض محتمل" if days < 21 else "تحتاج تحقق من مدة الخدمة",
            "المادة 109"
        ))

    if "salary and allowances" in text.lower():
        missing = any(
            phrase in text.lower()
            for phrase in ["determined later", "no amount is stated"]
        )
        results.append((
            "الراتب والبدلات",
            "معلومات ناقصة" if missing else "تحتاج مراجعة يدوية",
            "المادة 52"
        ))

    return results

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
        contract_text = "\n".join(
            page.get_text() for page in document
        )
        document.close()

        if not contract_text.strip():
            st.warning("تعذر استخراج النص. قد يكون الملف ممسوحًا ضوئيًا.")
        else:
            st.success("تمت قراءة العقد بنجاح")
            st.subheader("نتائج مراجعة العقد")

            results = analyze_contract(contract_text)

            if results:
                for name, status, reference in results:
                    with st.expander(name, expanded=True):
                        st.write("الحالة:", status)
                        st.write("المرجع:", reference)
            else:
                st.warning("لم يتم التعرف على البنود المدعومة.")

            st.info(
                "عدم ظهور تنبيه لا يعني أن العقد سليم نظاميًا. "
                "الفحص الحالي يعتمد على عبارات محددة."
            )

    except Exception as error:
        st.error("تعذر قراءة الملف أو تحليله.")
