from pathlib import Path
from datetime import date
import re
import pdfplumber
import pandas as pd

# =====================
# Regex
# =====================
DATE_RE = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")
TXN_RE = re.compile(r"^\d{4}$")
ORDER_LONG_RE = re.compile(r"^\d{10,}(?:_\d+)?$")
NUM_RE = re.compile(r"^\d+(?:\.\d{1,2})?$")

TOTAL_USD_RE = re.compile(
    r"Total\s*\(\s*USD\s*\)\s*:\s*([$]?\s*[\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

SINGLE_COUNTRIES = {
    "canada","australia","mexico","china","france","germany",
    "italy","spain","japan","singapore","uae","pakistan","uk"
}

# =====================
# Helpers
# =====================
def clean(t):
    return (t or "").strip("[]{}(),;:")

def parse_ymd_to_date(s):
    y, m, d = s.split("/")
    return date(int(y), int(m), int(d))

def excel_serial_from_date(dt):
    excel_epoch = date(1899, 12, 30)
    return (dt - excel_epoch).days

# =====================
# PDF extraction
# =====================
def extract_tokens_and_text(pdf_path):
    tokens = []
    full_text = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            full_text.append(txt)
            tokens.extend(txt.split())

    return tokens, "\n".join(full_text)

def extract_total_usd(text):
    m = TOTAL_USD_RE.search(text or "")
    if not m:
        return None
    return float(m.group(1).replace("$", "").replace(",", ""))

# =====================
# Core parser
# =====================
def parse_pdf_tokens(tokens, file_name):
    rows = []
    i = 0

    while i < len(tokens) - 2:
        if not (
            ORDER_LONG_RE.match(clean(tokens[i])) and
            TXN_RE.match(clean(tokens[i+1])) and
            DATE_RE.match(clean(tokens[i+2]))
        ):
            i += 1
            continue

        order = int(tokens[i+1])
        dt = parse_ymd_to_date(tokens[i+2])
        date_serial = excel_serial_from_date(dt)

        qty = None
        cost = None

        for j in range(i+3, min(i+150, len(tokens))):
            t = clean(tokens[j]).lower()
            if t.isdigit() and 1 <= int(t) <= 999:
                qty = int(t)
            elif NUM_RE.match(t) and "." in t:
                cost = float(t)

        if cost is not None:
            rows.append({
                "File": file_name,
                "DateSerial": date_serial,
                "Order": order,
                "Qty": qty,
                "Cost": cost
            })

        i += 3

    return rows

# =====================
# PUBLIC API FUNCTION
# =====================
def convert_pdf_to_dataframe(pdf_path: Path):
    tokens, text = extract_tokens_and_text(pdf_path)
    rows = parse_pdf_tokens(tokens, pdf_path.name)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
