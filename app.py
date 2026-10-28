import streamlit as st
import pymupdf
import re
from html import escape

st.set_page_config(page_title="دقّق | DAQQIQ - Beta")

language = st.radio("Language / اللغة", ["العربية", "English"], horizontal=True)
is_english = language == "English"

def tr(ar, en):
    return en if is_english else ar

st.markdown("""
<style>
.stApp {background-color: #F7F9FC; color: #102A43;}
h1, h2, h3 {color: #102A43 !important;}
.stButton > button {background-color: #E7BE70; color: #102A43; border-radius: 10px; border: none;}
</style>
""", unsafe_allow_html=True)

main_title = tr("افهم عقد عملك قبل التوقيع", "Understand your employment contract before signing")
main_description = tr("مساعد لمراجعة بنود عقود العمل السعودية", "An assistant for reviewing Saudi employment contract clauses")
header_html = """
<div style="background-color:#102A43; padding:35px; border-radius:16px; text-align:center;">
  <div style="color:#E7BE70; font-size:48px; font-weight:bold; padding:10px 0;">دقّق | DAQQIQ</div>
  <p style="color:white; font-size:20px;">__TITLE__</p>
  <p style="color:#DDE6EE; font-size:15px;">__DESCRIPTION__</p>
</div>
"""
st.markdown(header_html.replace("__TITLE__", escape(main_title)).replace("__DESCRIPTION__", escape(main_description)), unsafe_allow_html=True)
st.caption(tr("نسخة تجريبية تعليمية وليست استشارة قانونية", "Educational beta — not legal advice"))

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


NAME_EN = {
    "فترة التجربة": "Probation period",
    "ساعات العمل": "Working hours",
    "الإجازة السنوية": "Annual leave",
    "الراتب والبدلات": "Salary and allowances",
}
STATUS_EN = {
    "تعارض محتمل": "Potential conflict",
    "معلومات ناقصة": "Missing information",
    "تحتاج مراجعة": "Needs review",
    "لم يُرصد تجاوز للمدة": "No duration limit exceeded",
    "لم يُرصد تجاوز للحد المعتاد": "No usual limit exceeded",
    "تحتاج تحقق من مدة الخدمة": "Service length needs verification",
    "تم ذكر الراتب والبدلات، وتحتاج مراجعة": "Salary and allowances stated; review needed",
}

def english_details(item):
    name = item["name"]
    status = item["status"]
    numbers = re.findall(r"\d+", item["explanation"])
    if name == "فترة التجربة":
        days = numbers[0] if numbers else "?"
        issue = status == "تعارض محتمل"
        return (f"The probation period is {days} days. " + ("This exceeds 180 days." if issue else "This does not exceed 180 days."),
                "Request a revision of the probation period before signing." if issue else "Check the remaining probation terms.")
    if name == "ساعات العمل":
        daily, weekly = (numbers + ["?", "?"])[:2]
        return (f"The contract states {daily} hours per day and {weekly} hours per week. Legal exceptions may apply.",
                "Check the type of work and any applicable exceptions.")
    if name == "الإجازة السنوية":
        days = numbers[0] if numbers else "?"
        return (f"Annual leave is {days} days. The usual minimum is 21 days and may increase with length of service.",
                "Verify the annual leave entitlement based on length of service.")
    missing = status == "معلومات ناقصة"
    return (("The salary and allowances amounts are not clearly specified." if missing else
             "Salary and allowances are mentioned, but their completeness and accuracy need review."),
            "Ask for salary and allowances to be clarified in writing." if missing else
            "Review the amounts and confirm the parties' written agreement.")

st.markdown("### " + tr("ابدأ مراجعة عقدك", "Start reviewing your contract"))
st.write(tr("ارفع عقد العمل بصيغة PDF، وسنساعدك في فهم البنود التي تحتاج إلى مراجعة.",
            "Upload an employment contract as a PDF to review supported clauses."))
uploaded_file = st.file_uploader(tr("اختر ملف عقد العمل (PDF)", "Choose an employment contract (PDF)"), type=["pdf"])

if uploaded_file is not None:
    try:
        document = pymupdf.open(stream=uploaded_file.getvalue(), filetype="pdf")
        text = "\n".join(page.get_text() for page in document)
        document.close()

        if not text.strip():
            st.warning(tr("تعذر استخراج النص من ملف PDF. قد يكون الملف مصورًا.",
                          "Could not extract text from this PDF. It may be a scanned document."))
        else:
            st.success(tr("تمت قراءة العقد بنجاح", "Contract text extracted successfully"))
            results = analyze_contract(text)
            safe_count = sum(item["status"].startswith("لم يُرصد") for item in results)
            issue_count = sum(item["status"] in ["تعارض محتمل", "معلومات ناقصة"] for item in results)
            review_count = len(results) - safe_count - issue_count

            col1, col2, col3 = st.columns(3)
            col1.metric(tr("لم يُرصد تجاوز", "No limit exceeded"), safe_count)
            col2.metric(tr("تحتاج مراجعة", "Needs review"), review_count)
            col3.metric(tr("تنبيهات محتملة", "Potential alerts"), issue_count)

            report_heading = tr("تقرير مراجعة العقد", "Contract review report")
            report_html = """
<div style="background-color:#102A43; padding:16px; border-radius:10px; text-align:center; margin-top:20px;">
  <div style="color:#E7BE70; font-size:28px; font-weight:bold;">__REPORT__</div>
</div>
"""
            st.markdown(report_html.replace("__REPORT__", escape(report_heading)), unsafe_allow_html=True)

            if not results:
                st.warning(tr("لم يتم التعرف على البنود المدعومة.", "No supported clauses were identified."))

            for item in results:
                name = NAME_EN.get(item["name"], item["name"]) if is_english else item["name"]
                status = STATUS_EN.get(item["status"], item["status"]) if is_english else item["status"]
                explanation, recommendation = english_details(item) if is_english else (item["explanation"], item["recommendation"])
                with st.expander(name, expanded=False):
                    st.write("**" + tr("النص الأصلي:", "Original clause:") + "**")
                    clause = get_original_clause(text, item["name"])
                    if is_english and clause == "تعذر تحديد نص البند الأصلي.":
                        clause = "Original clause could not be identified."
                    st.write(clause)
                    if item["status"].startswith("لم يُرصد"):
                        st.success(tr("الحالة: ", "Status: ") + status)
                    elif item["status"] in ["تعارض محتمل", "معلومات ناقصة"]:
                        st.error(tr("الحالة: ", "Status: ") + status)
                    else:
                        st.warning(tr("الحالة: ", "Status: ") + status)
                    st.write("**" + tr("الشرح:", "Explanation:") + "**", explanation)
                    st.write("**" + tr("التوصية:", "Recommendation:") + "**", recommendation)
                    reference = item["reference"]
                    if is_english:
                        reference = reference.replace("المواد", "Articles").replace("المادة", "Article").replace(" و", " and ")
                    st.write("**" + tr("المرجع:", "Reference:") + "**", reference)

            # Ask DAQQIQ: transparent, contract-grounded Q&A for supported clauses only.
            st.markdown("---")
            st.markdown("### " + tr("اسأل دقّق", "Ask DAQQIQ"))
            st.write(tr(
                "اسأل عن بند في العقد المرفوع: فترة التجربة، ساعات العمل، الإجازة السنوية أو الراتب والبدلات.",
                "Ask about a clause in your uploaded contract: probation, working hours, annual leave, or salary and allowances."
            ))
            with st.form("ask_daqqiq_form"):
                question = st.text_input(
                    tr("سؤالك عن العقد", "Your question about the contract"),
                    placeholder=tr("مثال: هل فترة التجربة في عقدي تحتاج مراجعة؟",
                                   "Example: Does my probation clause need review?")
                )
                ask_submitted = st.form_submit_button(tr("اسأل دقّق", "Ask DAQQIQ"))

            if ask_submitted:
                q = question.strip().lower()
                topic_keywords = {
                    "فترة التجربة": ["تجرب", "اختبار", "probation", "trial period"],
                    "ساعات العمل": ["ساع", "دوام", "عمل يوم", "working hour", "work hour", "hours per", "overtime"],
                    "الإجازة السنوية": ["إجاز", "اجاز", "عطلة", "annual leave", "vacation", "holiday"],
                    "الراتب والبدلات": ["راتب", "رواتب", "أجر", "اجر", "بدل", "salary", "wage", "allowance", "pay"],
                }
                topics = [name for name, keywords in topic_keywords.items()
                          if any(keyword in q for keyword in keywords)]
                if not q:
                    st.warning(tr("اكتب سؤالك أولًا.", "Please enter a question."))
                elif len(topics) > 1:
                    st.info(tr("سؤالك يتناول أكثر من بند. اسأل عن بند واحد في كل مرة.",
                               "Your question mentions multiple clauses. Please ask about one at a time."))
                elif not topics:
                    st.info(tr(
                        "هذا السؤال خارج نطاق النسخة التجريبية. أقدر أشرح فقط البنود الأربعة المدعومة بعد تحليلها من العقد.",
                        "This question is outside the beta scope. I can only explain the four supported clauses when identified in the contract."
                    ))
                else:
                    topic = topics[0]
                    matching = next((item for item in results if item["name"] == topic), None)
                    if matching is None:
                        st.warning(tr(
                            "لم أتعرف على هذا البند في النص المستخرج من عقدك. هذا لا يعني أنه غير موجود أو سليم؛ راجعه يدويًا.",
                            "This clause was not identified in the extracted contract text. It may still be present; please review it manually."
                        ))
                    else:
                        shown_name = NAME_EN.get(topic, topic) if is_english else topic
                        shown_status = STATUS_EN.get(matching["status"], matching["status"]) if is_english else matching["status"]
                        explanation, recommendation = (english_details(matching) if is_english
                                                       else (matching["explanation"], matching["recommendation"]))
                        st.markdown("**" + shown_name + "**")
                        st.write("**" + tr("نتيجة الفحص:", "Review status:") + "** " + shown_status)
                        st.write("**" + tr("الشرح:", "Explanation:") + "** " + explanation)
                        st.write("**" + tr("الخطوة المقترحة:", "Suggested next step:") + "** " + recommendation)
                        reference = matching["reference"]
                        if is_english:
                            reference = reference.replace("المواد", "Articles").replace("المادة", "Article").replace(" و", " and ")
                        st.caption(tr("مرجع مذكور للمراجعة (لم يتم التحقق من سريانه آليًا): ",
                                      "Reference for manual verification (not automatically checked for currency): ") + reference)
                        st.caption(tr(
                            "الإجابة مبنية على قواعد الفحص وبيانات العقد المستخرجة، وليست محادثة ذكاء اصطناعي أو فتوى قانونية.",
                            "This answer comes from rule-based analysis of extracted contract text, not an AI legal opinion."
                        ))

            st.info(tr("هذا فحص أولي بقواعد محددة. عدم ظهور تنبيه لا يعني سلامة العقد، وقد توجد استثناءات نظامية.",
                       "This is a preliminary rule-based check. No alert does not mean the contract is legally compliant; exceptions may apply."))
    except Exception:
        st.error(tr("حدث خطأ أثناء قراءة العقد أو تحليله.", "An error occurred while reading or analyzing the contract."))
