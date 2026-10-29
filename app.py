import streamlit as st
import pymupdf
import re
import io
from datetime import date
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
with st.expander(tr("نطاق الخدمة والخصوصية", "Scope and privacy")):
    st.write(tr("دقّق يفحص أربعة موضوعات فقط في عقود العمل السعودية: التجربة، ساعات العمل، الإجازة السنوية، والراتب والبدلات. يعتمد على مطابقة نصوص وقواعد أولية؛ لا يصدر حكمًا قانونيًا ولا يتحقق تلقائيًا من آخر تحديثات الأنظمة.",
                "DAQQIQ screens four topics in Saudi employment contracts: probation, working hours, annual leave, and salary/allowances. It uses preliminary text-matching rules, not legal judgments or live legal updates."))
    st.write(tr("يُحلَّل الملف أثناء جلسة التطبيق. لا يتضمن هذا الكود قاعدة بيانات لحفظ العقود ولا يرسل محتوى العقد إلى نموذج ذكاء اصطناعي خارجي. مع ذلك، تتم معالجة الملف على خادم الاستضافة، لذا لا ترفعي عقودًا حقيقية تتضمن بيانات شخصية حساسة إلى هذه النسخة التجريبية.",
                "The file is processed during the app session. This code has no contract database and does not send contract text to an external AI model. However, the hosting server processes the upload: do not upload real contracts containing sensitive personal data to this beta."))
    st.write(tr("المراجع المذكورة للتوجيه إلى المراجعة اليدوية فقط، وليست نصوصًا نظامية تم استرجاعها أو التحقق من سريانها آليًا.",
                "Cited article numbers are pointers for manual review, not live-retrieved or automatically verified legal texts."))


def ocr_readability_score(text, language):
    """Heuristic for choosing OCR script; not a legal accuracy/confidence score."""
    if not text.strip():
        return -1
    arabic = len(re.findall(r"[\u0621-\u064a]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if language == "eng":
        words = ["contract", "clause", "probation", "working", "hours", "annual", "leave", "salary", "employee", "employer"]
        return latin * 1.5 - arabic * 2 + sum(30 for w in words if re.search(r"\b" + w + r"\b", text, re.I))
    words = ["العقد", "البند", "التجرب", "العمل", "الاجاز", "الراتب", "الموظف", "السنوي", "ساعات"]
    normalized = normalize_text(text)
    return arabic * 1.5 - latin * 2 + sum(30 for w in words if w in normalized)


def extract_pdf_with_ocr(pdf_bytes):
    """Read text PDFs directly; try both Arabic and English OCR for scanned pages."""
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages, ocr_pages, failed_pages = [], [], []
    try:
        for index, page in enumerate(document):
            raw_text = page.get_text(sort=True).strip()
            if len(raw_text) >= 40:
                pages.append(raw_text)
                continue

            candidates = []
            for lang in ("eng", "ara"):
                try:
                    tp = page.get_textpage_ocr(language=lang, dpi=300, full=True)
                    # sort=False preserves Arabic reading order better in our test.
                    recognized = page.get_text(textpage=tp, sort=False).strip()
                    if recognized:
                        candidates.append((ocr_readability_score(recognized, lang), recognized, lang))
                except Exception:
                    pass

            if candidates:
                _, recognized, chosen_language = max(candidates, key=lambda item: item[0])
                if len(recognized) > len(raw_text):
                    pages.append(recognized)
                    ocr_pages.append(index + 1)
                else:
                    pages.append(raw_text)
            else:
                pages.append(raw_text)
                failed_pages.append(index + 1)
    finally:
        document.close()
    return "\n".join(pages), ocr_pages, failed_pages, len(pages)


def normalize_text(text):
    """Normalize Arabic digits and common orthographic variants for matching only."""
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    text = text.translate(digits)
    text = re.sub(r"[\u064b-\u065f\u0670ـ]", "", text)
    return text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


TOPICS = ["فترة التجربة", "ساعات العمل", "الإجازة السنوية", "الراتب والبدلات"]
REFERENCES = {"فترة التجربة": "المادة 53", "ساعات العمل": "المواد 98 و99 و100",
              "الإجازة السنوية": "المادة 109", "الراتب والبدلات": "المادة 52"}
# Curated, offline reference index: article pointers, NOT live law text or full RAG.
# The official landing pages are provided for manual checking of amendments.
SOURCE_INDEX = {
    "فترة التجربة": {
        "articles": "53",
        "ar": "راجعي شروط فترة التجربة ومدتها وطريقة الاتفاق عليها في النظام الساري.",
        "en": "Check the probation terms, duration and agreement requirements in the current law.",
    },
    "ساعات العمل": {
        "articles": "98–100",
        "ar": "راجعي ساعات العمل والاستثناءات والراحة بحسب طبيعة العمل والنظام الساري.",
        "en": "Check working-hour limits, exceptions and rest requirements under current law.",
    },
    "الإجازة السنوية": {
        "articles": "109",
        "ar": "راجعي الحد الأدنى للإجازة السنوية وتأثير مدة الخدمة في النظام الساري.",
        "en": "Check annual leave entitlements and the effect of length of service under current law.",
    },
    "الراتب والبدلات": {
        "articles": "52",
        "ar": "راجعي توثيق الأجر والبدلات وشروط العقد المكتوبة في النظام الساري.",
        "en": "Check the written wage and allowance terms against current contract requirements.",
    },
}
# Verified official topic-specific entry points (checked 2026-10-29).
# These are manual source links, not automatically retrieved or validated law.
TOPIC_SOURCE_URLS = {
    "فترة التجربة": "https://www.hrsd.gov.sa/علاقات-العمل",
    "ساعات العمل": "https://www.hrsd.gov.sa/en/شروط-العمل-وظروفه",
    "الإجازة السنوية": "https://www.hrsd.gov.sa/en/شروط-العمل-وظروفه",
    "الراتب والبدلات": "https://www.hrsd.gov.sa/علاقات-العمل",
}
OFFICIAL_LAW_URL = "https://www.hrsd.gov.sa/sites/default/files/2025-05/hrsd.pdf"

OFFICIAL_SOURCES = {
    "HRSD": "https://www.hrsd.gov.sa/",
    "Bureau of Experts": "https://laws.boe.gov.sa/",
}


def retrieve_reference(topic):
    """Deterministic retrieval from a four-entry local index, not LLM/RAG."""
    return SOURCE_INDEX.get(topic)


HEADINGS = {
    "فترة التجربة": [r"(?:ل?فترة)\s*(?:ال)?تجرب[هة]?", r"التجرب[هة]?\s*فترة", r"مدة\s*(?:ال)?تجرب[هة]?", r"ةبرجت\s+ةرتفل?", r"probation", r"trial period"],
    "ساعات العمل": [r"ساعات\s*العمل", r"working hours", r"hours per day", r"ساعات\s*يومي"],
    "الإجازة السنوية": [r"الاجازة\s*السنوي", r"اجازة\s*سنوي", r"annual leave"],
    "الراتب والبدلات": [r"الراتب", r"البدلات", r"salary", r"allowances", r"wages"],
}


def analyze_contract(text, scanned=False):
    """Conservative four-topic screening; never infer legal compliance from OCR."""
    normalized = normalize_text(text)
    results = []
    for name in TOPICS:
        found = any(re.search(pattern, normalized, re.I) for pattern in HEADINGS[name])
        status = "لم يتم التعرف على البند"
        explanation = "لم تتمكن قواعد الاستخراج من تحديد هذا البند من النص المتاح."
        recommendation = "راجعي العقد الأصلي يدويًا. عدم التعرف لا يعني غياب البند."
        if found:
            status = "تم العثور على البند ويحتاج مراجعة"
            explanation = "تم التعرف على موضوع البند، لكن لم يتم التحقق من تفاصيله أو أرقامه."
            recommendation = "راجعي النص الأصلي والأرقام قبل اتخاذ أي قرار."

        if found and not scanned:
            # Only accept numbers close to recognizable, unambiguous phrases in selectable text.
            if name == "فترة التجربة":
                m = re.search(r"(?:probation period(?: of| is|:)?|فترة التجرب[هة]\s*(?:لمدة|مدتها)?|مدة التجرب[هة])\s*(?:of|is|:)?\s*(\d{1,3})\s*(?:days?|يوم)", normalized, re.I)
                if m:
                    days = int(m.group(1))
                    status = "تعارض محتمل" if days > 180 else "لم يُرصد تجاوز للمدة"
                    explanation = f"مدة التجربة المذكورة {days} يومًا. " + ("تتجاوز 180 يومًا." if days > 180 else "لا تتجاوز 180 يومًا؛ راجعي بقية الشروط.")
                    recommendation = "تحققي من تطبيق النص النظامي الحالي والاستثناءات على العقد."
            elif name == "ساعات العمل":
                m = re.search(r"(\d{1,2})\s*(?:actual )?hours per day[,;\s]+(\d{1,2})\s*days per week", normalized, re.I)
                if m:
                    daily, days_per_week = map(int, m.groups())
                    if 0 < daily <= 24 and 0 < days_per_week <= 7:
                        weekly = daily * days_per_week
                        status = "تحتاج مراجعة" if daily > 8 or weekly > 48 else "لم يُرصد تجاوز للحد المعتاد"
                        explanation = f"العقد يذكر {daily} ساعات يوميًا و{weekly} ساعة أسبوعيًا؛ قد تنطبق استثناءات."
                        recommendation = "تحققي من نوع العمل والاستثناءات والأنظمة السارية."
            elif name == "الإجازة السنوية":
                m = re.search(r"(?:annual leave(?: of| is|:)?|اجازة سنوية(?: مدتها|:)?|الاجازة السنوية(?: مدتها|:)?)[\s\S]{0,24}?(\d{1,3})\s*(?:days?|يوم)|(\d{1,3})\s*days of paid annual leave", normalized, re.I)
                if m:
                    days = int(next(v for v in m.groups() if v is not None))
                    status = "تعارض محتمل" if days < 21 else "تحتاج تحقق من مدة الخدمة"
                    explanation = f"الإجازة المذكورة {days} يومًا؛ الحد الأدنى المعتاد 21 يومًا وقد يختلف الاستحقاق حسب مدة الخدمة."
                    recommendation = "راجعي الاستحقاق وفق مدة الخدمة والنظام الساري."
            elif name == "الراتب والبدلات":
                if re.search(r"determined later|no amount is stated|يحدد لاحقا", normalized, re.I):
                    status = "معلومات ناقصة"
                    explanation = "وردت صياغة تفيد أن مبلغ الراتب لم يُحدد بوضوح."
                    recommendation = "اطلبي تحديد المبلغ والبدلات كتابةً."
                else:
                    explanation = "ورد ذكر الراتب أو البدلات؛ يلزم التحقق من المبالغ والتفاصيل في الأصل."
        elif found and scanned:
            explanation = "رُصد عنوان أو كلمات من هذا البند في صفحة مصورة، لكن أرقام OCR غير موثوقة ولا يجوز استخدامها للحكم على العقد."
            recommendation = "قارني الأرقام والنص مع صورة العقد الأصلي يدويًا."

        results.append({"name": name, "status": status, "explanation": explanation,
                        "recommendation": recommendation, "reference": REFERENCES[name]})
    return results


def get_original_clause(text, name):
    """Extract a short original-text snippet, stopping at the next clause heading."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        norm = normalize_text(line)
        if any(re.search(pattern, norm, re.I) for pattern in HEADINGS[name]):
            # OCR sometimes merges the next heading onto the same line.
            snippet = " ".join(lines[i:i + 3]).strip()
            next_headings = [
                r"Clause\s+\d+\s*[-–—:]",
                r"البند\s+(?:الاول|الثاني|الثالث|الرابع|الخامس|الاولى|الثانى)\s*[:：-]?",
            ]
            # Remove any next heading, but preserve the first heading at the start.
            for pattern in next_headings:
                matches = list(re.finditer(pattern, normalize_text(snippet), re.I))
                for match in matches:
                    if match.start() > 2:
                        snippet = snippet[:match.start()].rstrip()
                        break
            return snippet[:700]
    return "تعذر تحديد نص البند الأصلي."



def improve_ocr_excerpt(excerpt, topic=None):
    """Tentative display cleanup for known reversed OCR clauses, not legal extraction.

    Never infer numbers or rewrite the raw OCR evidence.
    """
    # The OCR engine can put a *normal* heading before reversed body text.
    # Remove only a recognized heading from the tentative display, not the raw text.
    heading = re.compile(
        r"^\s*البند\s+(?:الاول|الثاني|الثانى|الثالث|الرابع|الخامس)"
        r"\s*[:：-]?\s*(?:فترة\s*التجرب[هة]?|ساعات\s*العمل|"
        r"الاجازة\s*السنوي[هة]?|الراتب\s*والبدلات)\s*",
        re.I,
    )
    cleaned = heading.sub("", normalize_text(excerpt), count=1).strip()
    # Keep the original letters (including hamza) for display where possible.
    original_cleaned = re.sub(
        r"^\s*البند\s+(?:الأول|الاول|الثاني|الثانى|الثالث|الرابع|الخامس)"
        r"\s*[:：-]?\s*(?:فترة\s*التجرب[هة]?|ساعات\s*العمل|"
        r"الإجازة\s*السنوي[هة]?|الاجازة\s*السنوي[هة]?|الراتب\s*والبدلات)\s*",
        "", excerpt, count=1, flags=re.I,
    ).strip()

    # Working-hours OCR: display a conservative readable paraphrase only when
    # the recognized text contains the expected working-hours wording.
    # Both quantities remain unverified, including letter-like OCR digits.
    if topic == "ساعات العمل" and re.search(r"ساعات\s*العمل|ساعات\s*يومي", normalize_text(excerpt)) and re.search(r"الاسبوع|الأسبوع", excerpt):
        return ("تكون ساعات العمل الفعلية [رقم غير مؤكد] ساعات يوميًا، "
                "لمدة [رقم غير مؤكد] أيام في الأسبوع."), True

    # Some PDF OCR outputs mix right-to-left and left-to-right runs.
    # Reconstruct only lines with distinctive backwards phrases; otherwise
    # leave them alone rather than pretending we corrected the OCR.
    if re.search(r"ةبرجت\s+ةرتفل", cleaned):
        tentative = original_cleaned[::-1]
    elif re.search(r"ةعوفدم\s+ةيونس\s+ةزاج", cleaned):
        tentative = original_cleaned[::-1]
    elif re.search(r"يرهشلا\s+بتارلا", cleaned):
        # Mixed-direction salary OCR is unreliable. Preserve only the
        # recognizable phrase and do not claim to reconstruct the full line.
        currency = " ريال سعودي" if re.search(r"ريال\s+سعودي", excerpt) else ""
        tentative = "إجمالي الراتب الشهري: [رقم غير مؤكد]" + currency
    else:
        return excerpt, False

    # Remove heading debris that appears after reversing a merged OCR line.
    tentative = re.sub(
        r"\s*(?:ةيونسلا\s+ةزاجإلا|ةيونسلا\s+ةزاجالا)\s*[:：]?\s*"
        r"(?:ثلاثلا\s+دنبلا)?\s*$", "", tentative
    )
    # Numeric OCR in a scan is not trustworthy, including reversed digits.
    tentative = re.sub(r"[0-9٠-٩۰-۹]+", "[رقم غير مؤكد]", tentative)
    tentative = re.sub(r"[\"“”'«»]+(?=\s*\[رقم غير مؤكد\])", "", tentative)
    tentative = re.sub(r"يومً\s+ا", "يومًا", tentative)
    tentative = re.sub(r"\s+", " ", tentative).strip(" .")
    if not tentative:
        return excerpt, False
    return tentative + ".", True


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
    "تم العثور على البند ويحتاج مراجعة": "Clause found; manual review required",
    "لم يتم التعرف على البند": "Clause not identified",
}

def english_details(item):
    name = item["name"]
    status = item["status"]
    if status == "تم العثور على البند ويحتاج مراجعة":
        return ("A related clause was found, but its wording or numbers have not been verified.",
                "Check the original PDF manually before relying on these findings.")
    if status == "لم يتم التعرف على البند":
        return ("The extraction rules could not identify this clause in the available text. It may be worded differently or appear in an image.",
                "Check the original contract manually; absence of an alert does not establish compliance.")
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

with st.expander(tr("المصادر النظامية ونطاق الاسترجاع", "Legal sources and retrieval scope")):
    st.write(tr(
        "هذه مكتبة مرجعية محلية صغيرة تربط كل بند برقم المادة وملاحظة إرشادية. لا تسترجع نص النظام مباشرة، ولا تتابع تحديثاته، ولا تستخدم نموذجًا توليديًا؛ لذلك ليست RAG كاملة.",
        "This is a small offline reference index linking each clause to article numbers and review notes. It does not fetch live law, track amendments, or use a generative model; it is not full RAG."
    ))
    for topic, source in SOURCE_INDEX.items():
        label = NAME_EN.get(topic, topic) if is_english else topic
        st.write("**" + label + " — " + tr("المادة/المواد: ", "Article(s): ") + source["articles"] + "**")
        st.caption(source["en"] if is_english else source["ar"])
        st.markdown("[" + tr("القسم الرسمي المرتبط بالبند", "Official section for this topic") + "](" + TOPIC_SOURCE_URLS[topic] + ")")
    st.markdown("[" + tr("نظام العمل — المصدر الرسمي", "Labor Law — official source") + "](" + OFFICIAL_LAW_URL + ")")
    st.caption(tr("الروابط للمراجعة اليدوية، وليست تحققًا آليًا من سريان النصوص.", "Links are for manual review, not automatic verification of legal currency."))

# Explain the difference between rule-based alerts and legal conclusions.
with st.expander(tr("كيف يفسّر دقّق النتائج؟", "How DAQQIQ interprets findings")):
    st.markdown(tr(
        "**تعارض محتمل:** رصدت قاعدة الفحص رقمًا قد يتعارض مع حد معتاد؛ لا يعني ذلك إثبات مخالفة قانونية.\n\n"
        "**يحتاج مراجعة:** البند موجود، لكن تفسيره يعتمد على شروط أخرى أو استثناءات أو مدة الخدمة.\n\n"
        "**معلومات ناقصة أو غير مؤكدة:** لا تتوفر تفاصيل كافية، أو قد يكون OCR أخطأ في قراءة النص والأرقام.\n\n"
        "**لم يُرصد تجاوز:** لم تكتشف القاعدة تجاوزًا في الجزء الذي استطاعت قراءته؛ هذا لا يعني أن العقد سليم قانونيًا.\n\n"
        "**لم يتم التعرف على البند:** قد يكون البند بصياغة مختلفة أو داخل جدول أو صورة، وليس بالضرورة غائبًا.",
        "**Potential conflict:** A rule detected a number that may exceed a usual threshold; this does not establish a legal violation.\n\n"
        "**Needs review:** The clause may depend on additional terms, exceptions, or length of service.\n\n"
        "**Missing or unverified information:** Details are insufficient, or OCR may have misread words and numbers.\n\n"
        "**No limit exceeded:** No issue was detected by the applicable rule in the readable text; this does not establish legal compliance.\n\n"
        "**Clause not identified:** The clause may use different wording or appear in a table or image; it is not necessarily absent."
    ))
    st.info(tr(
        "يجب قراءة البند في سياق العقد الكامل والتحقق من النظام الساري والاستثناءات قبل اتخاذ قرار.",
        "Read each clause in the context of the full contract and verify current law and exceptions before making a decision."
    ))

st.markdown("### " + tr("ابدأ مراجعة عقدك", "Start reviewing your contract"))
st.write(tr("ارفع عقد العمل بصيغة PDF، وسنساعدك في فهم البنود التي تحتاج إلى مراجعة.",
            "Upload an employment contract as a PDF to review supported clauses."))
uploaded_file = st.file_uploader(tr("اختر ملف عقد العمل (PDF)", "Choose an employment contract (PDF)"), type=["pdf"])

if uploaded_file is not None:
    try:
        with st.spinner(tr("جاري استخراج النص ومحاولة قراءة الصفحات المصورة...", "Extracting text and checking scanned pages with OCR...")):
            text, ocr_pages, failed_pages, total_pages = extract_pdf_with_ocr(uploaded_file.getvalue())
        st.caption(tr(f"صفحات الملف: {total_pages} | صفحات OCR: {len(ocr_pages)}",
                      f"PDF pages: {total_pages} | OCR pages: {len(ocr_pages)}"))
        if ocr_pages:
            st.info(tr("تم استخدام OCR لقراءة الصفحات: " + ", ".join(map(str, ocr_pages)) + ". راجعي النص المستخرج لأن OCR قد يخطئ في الأرقام والجداول.",
                       "OCR was used on pages: " + ", ".join(map(str, ocr_pages)) + ". Verify extracted numbers and tables; OCR can make mistakes."))
        if failed_pages:
            st.warning(tr("تعذرت قراءة بعض الصفحات أو لم يظهر فيها نص كافٍ: " + ", ".join(map(str, failed_pages)) + ". لا تعتمدي على نتائج هذه الصفحات دون مراجعة.",
                          "Some pages could not be read reliably: " + ", ".join(map(str, failed_pages)) + ". Review those pages manually."))

        if not text.strip():
            st.warning(tr("تعذر استخراج النص من ملف PDF. قد يكون الملف مصورًا.",
                          "Could not extract text from this PDF. It may be a scanned document."))
        else:
            st.success(tr("اكتملت محاولة استخراج النص", "Text extraction attempt completed"))
            # Conservative: if any page used OCR, avoid numeric compliance claims.
            results = analyze_contract(text, scanned=bool(ocr_pages))
            if ocr_pages:
                st.warning(tr(
                    "تنبيه: نتائج الصفحات المصورة غير مؤكدة بسبب احتمال أخطاء OCR في الأرقام وترتيب الكلمات. قارني كل نتيجة بالعقد الأصلي قبل الاعتماد عليها.",
                    "Warning: Scanned-page findings are unverified because OCR may misread numbers or word order. Check each finding against the original PDF."
                ))
            safe_count = sum(item["status"].startswith("لم يُرصد") for item in results)
            issue_count = sum(item["status"] in ["تعارض محتمل", "معلومات ناقصة"] for item in results)
            missing_count = sum(item["status"] == "لم يتم التعرف على البند" for item in results)
            review_count = len(results) - safe_count - issue_count - missing_count

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(tr("لم يُرصد تجاوز", "No limit exceeded"), safe_count)
            col2.metric(tr("تحتاج مراجعة", "Needs review"), review_count)
            col3.metric(tr("تنبيهات محتملة", "Potential alerts"), issue_count)
            col4.metric(tr("لم يُتعرف عليه", "Not identified"), missing_count)

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
                    st.write("**" + tr("النص المستخرج من العقد:", "Extracted contract text:") + "**")
                    clause = get_original_clause(text, item["name"])
                    if ocr_pages and clause != "تعذر تحديد نص البند الأصلي.":
                        improved, was_reversed = improve_ocr_excerpt(clause, item["name"])
                        if was_reversed:
                            st.caption(tr(
                                "قراءة مبدئية لتحسين ترتيب الكلمات؛ الأرقام غير مؤكدة ويجب مراجعة صورة العقد:",
                                "Tentative OCR word-order correction; numbers are unverified. Check the original PDF:"
                            ))
                            st.write(improved)
                        else:
                            st.caption(tr(
                                "نص مستخرج آليًا وغير مؤكد؛ قارنيه بصورة العقد:",
                                "Unverified OCR text; compare with the original PDF:"
                            ))
                            st.write(clause)
                        with st.expander(tr("عرض نص OCR الخام", "Show raw OCR text"), expanded=False):
                            st.code(clause, language=None)
                    else:
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
                        reference = "Articles 98–100" if item["name"] == "ساعات العمل" else reference.replace("المواد", "Articles").replace("المادة", "Article").replace(" و", " and ")
                    st.write("**" + tr("المرجع:", "Reference:") + "**", reference)
                    st.caption(tr("للتحقق يدويًا من النص النظامي وتحديثاته: ", "Manually check the legal text and updates: "))
                    st.markdown("[" + tr("القسم الرسمي المرتبط بالموضوع", "Relevant HRSD legal section") + "](" + TOPIC_SOURCE_URLS[item["name"]] + ") · [" + tr("نظام العمل وتعديلاته", "Labor Law and amendments") + "](" + OFFICIAL_LAW_URL + ")")
                    st.caption(tr("رابط رسمي للمراجعة اليدوية فقط؛ لم يتحقق دقّق آليًا من سريان النص أو انطباق الاستثناءات.", "Official source for manual verification only; DAQQIQ has not automatically checked current applicability or exceptions."))

            st.caption(tr("التصنيف يصف ما رصدته قواعد الفحص فقط؛ لا يثبت صحة العقد أو مخالفته.",
                          "Statuses describe rule-based findings only; they do not establish legal compliance or violation."))

            st.markdown("### " + tr("جودة استخراج الملف", "PDF extraction quality"))
            st.caption(tr("عدد أحرف النص المستخرج: ", "Extracted text characters: ") + str(len(text)))
            with st.expander(tr("عرض النص المستخرج", "Show extracted text")):
                st.text_area(
                    tr("النص الذي قرأه دقّق", "Text read by DAQQIQ"),
                    value=text,
                    height=300
                )
            if len(text.strip()) < 200:
                st.warning(tr("النص المستخرج قصير؛ ربما يحتوي الملف على صور أو جداول لم تُقرأ بدقة. لا تعتمد على النتيجة وحدها.",
                              "Very little text was extracted; scans or tables may not have been read correctly. Do not rely on this result alone."))
            st.caption(tr("تدعم النسخة محاولة قراءة الصفحات المصورة باستخدام OCR، وقد تخطئ في الكلمات والأرقام العربية؛ تحققي من النص الأصلي.",
                          "This beta attempts OCR on scanned pages. Arabic words and numbers may be misread; verify against the original."))

            report_lines = [tr("تقرير دقّق التجريبي", "DAQQIQ beta report"), tr("التاريخ: ", "Date: ") + str(date.today()),
                            tr("فحص أولي وليس رأيًا قانونيًا", "Preliminary screening, not legal advice"), ""]
            for item in results:
                label = NAME_EN.get(item["name"], item["name"]) if is_english else item["name"]
                status = STATUS_EN.get(item["status"], item["status"]) if is_english else item["status"]
                expl, rec = english_details(item) if is_english else (item["explanation"], item["recommendation"])
                report_lines.extend([label, status, expl, rec, item["reference"], ""])
            if ocr_pages:
                report_lines.extend([tr("تحذير: استخدم OCR؛ النتائج والأرقام غير مؤكدة وتحتاج مقارنة بالصور الأصلية.",
                                        "Warning: OCR was used; findings and numbers are unverified and must be compared with the original images."), ""])
            report_lines.append(tr("راجع المصادر الرسمية وتحقق من سريان النصوص يدويًا.",
                                   "Verify current law against official sources manually."))
            st.download_button(tr("تحميل التقرير النصي", "Download text report"),
                               data="\n".join(report_lines).encode("utf-8-sig"),
                               file_name="daqqiq_report.txt", mime="text/plain")

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
                    if matching is None or matching["status"] == "لم يتم التعرف على البند":
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
                            reference = "Articles 98–100" if matching["name"] == "ساعات العمل" else reference.replace("المواد", "Articles").replace("المادة", "Article").replace(" و", " and ")
                        source = retrieve_reference(topic)
                        if source:
                            st.write("**" + tr("من المكتبة المرجعية المحلية:", "From the local reference index:") + "**")
                            st.write(source["en"] if is_english else source["ar"])
                            st.caption(tr("رقم المادة للمراجعة: ", "Article pointer: ") + source["articles"])
                            st.markdown("[" + tr("القسم النظامي الرسمي", "Official legal section") + "](" + TOPIC_SOURCE_URLS[topic] + ") · [" + tr("نظام العمل", "Labor Law") + "](" + OFFICIAL_LAW_URL + ")")
                        st.caption(tr("مرجع مذكور للمراجعة (لم يتم التحقق من سريانه آليًا): ",
                                      "Reference for manual verification (not automatically checked for currency): ") + reference)
                        st.caption(tr(
                            "الإجابة مبنية على قواعد الفحص وبيانات العقد المستخرجة، وليست محادثة ذكاء اصطناعي أو فتوى قانونية.",
                            "This answer comes from rule-based analysis of extracted contract text, not an AI legal opinion."
                        ))

            st.info(tr("هذا فحص أولي بقواعد محددة. عدم ظهور تنبيه لا يعني سلامة العقد، وقد توجد استثناءات نظامية.",
                       "This is a preliminary rule-based check. No alert does not mean the contract is legally compliant; exceptions may apply."))
    except Exception:
        st.error(tr("حدث خطأ أثناء قراءة العقد أو تحليله. تأكدي من أن الملف PDF صالح وأن OCR متاح على الخادم.",
                    "Could not process the PDF. Check that the PDF is valid and OCR is available on the server."))
