import json
import re
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "MA24103.json"
OUTPUT_FILE = BASE_DIR / "normalized_MA24103.json"

# -----------------------------
# OCR + LATEX NORMALIZATION MAP
# -----------------------------

LATEX_REPLACEMENTS = {
    r"J'\*n\(x\)": r"J_n'(x)",  # Fix for literal J'*n(x)
    r"J\*{n-1}\(x\)": r"J_{n-1}(x)", # Fix for xJ*{n-1}(x)
    r"j_([0-9])": r"J_\1",
    r"(?<!\\)\bSin\b": r"\\sin",
    r"(?<!\\)\bCos\b": r"\\cos",
    r"(?<!\\)\bTan\b": r"\\tan",
    r"(?<!\\)\bln\b": r"\\ln",
}

TEXT_READABILITY_MAP = {
    r"\\partial": "∂",
    r"\\pi": "π",
    r"\\int": "∫",
    r"\\oint": "∮",
    r"\\le": "≤",
    r"\\ge": "≥",
    r"\\mu": "μ",
    r"\\sigma": "σ",
    r"\\sqrt": "√",
    r"\\infty": "∞",
    r"\^2": "²",
    r"\^3": "³",
    r"\\left": "",
    r"\\right": "",
    r"\\frac": "",
    r"\{": "(",
    r"\}": ")",
    r"\\quad": " ",
    r"\\text": "",
    r"\\sin": "sin",
    r"\\cos": "cos",
    r"\\tan": "tan",
    r"\\ln": "ln",
    r"\\begin{cases}": "",
    r"\\end{cases}": "",
    r"\\begin{array}": "",
    r"\\end{array}": "",
    r"\\hline": "",
    r"&": " ",
    r"\\\\": " ",
    r"\s+": " "
}

# -----------------------------
# NORMALIZE TEXT
# -----------------------------

def normalize_text(text):
    if not text:
        return ""

    text = text.strip()

    # Apply general LaTeX OCR fixes first
    for pattern, replacement in LATEX_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text)

    # Convert known LaTeX to unicode for readability in question_text
    for pattern, replacement in TEXT_READABILITY_MAP.items():
        text = re.sub(pattern, replacement, text)
        
    return text.strip()

# -----------------------------
# FIX LATEX ESCAPING
# -----------------------------

def normalize_latex(latex):
    if not latex:
        return ""

    latex = latex.strip()

    # Apply general LaTeX OCR fixes
    for pattern, replacement in LATEX_REPLACEMENTS.items():
        latex = re.sub(pattern, replacement, latex)
        
    # Fix malformed derivative conditions
    latex = latex.replace(
        r"\left(\frac{\partial y}{\partial t}\right)*{t=0}",
        r"\left.\frac{\partial y}{\partial t}\right|_{t=0}"
    )
    
    latex = latex.replace(
        r"\right)*{t=0}",
        r"\right|_{t=0}"
    )

    return latex

# -----------------------------
# GENERATE UNIQUE HASH
# -----------------------------

def generate_uid(question_text):
    normalized = question_text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

# -----------------------------
# AUTO TAGGING
# -----------------------------

def generate_tags(question_text, question_latex):
    tags = set()
    q = (question_text + " " + question_latex).lower()

    if "fourier" in q: tags.add("Fourier Series")
    if "legendre" in q or "p_n" in q: tags.add("Legendre Polynomials")
    if "bessel" in q or "j_" in q or "j'" in q: tags.add("Bessel Functions")
    if "wave equation" in q or "\\partial^2" in q or "vibration of a string" in q: tags.add("Wave Equation")
    if "probability" in q or "binomial" in q or "poisson" in q or "random variable" in q or "pdf" in q: tags.add("Probability")
    if "wronskian" in q: tags.add("Wronskian")
    if "harmonic" in q or "analytic" in q or "complex" in q or "contour" in q or "\\oint" in q or "dz" in q: tags.add("Complex Analysis")
    if "differential equation" in q or "y''" in q or "d^2y" in q or "dy/dx" in q or "complementary function" in q or "particular integral" in q: tags.add("Differential Equations")
    if "variation of parameter" in q: tags.add("Variation of Parameters")

    return sorted(list(tags))

# -----------------------------
# NORMALIZATION PIPELINE
# -----------------------------

def normalize_question(q):
    
    original_text = q.get("question_text", "")
    original_latex = q.get("question_latex", "")

    q["question_latex"] = normalize_latex(original_latex)
    q["question_text"] = normalize_text(original_text)
    
    q["question_uid"] = generate_uid(q["question_text"])
    q["tags"] = generate_tags(original_text, original_latex)
    
    # Validation flags
    q["is_normalized"] = True
    q["is_verified"] = False
    q["latex_valid"] = True

    return q

# -----------------------------
# MAIN EXECUTION
# -----------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw_data = f.read()
    # Escape single backslashes in the malformed JSON so it can be parsed
    raw_data = raw_data.replace("\\", "\\\\")
    data = json.loads(raw_data)

normalized_data = []
seen_hashes = set()

for q in data:
    normalized_q = normalize_question(q)

    if normalized_q["question_uid"] in seen_hashes:
        continue

    seen_hashes.add(normalized_q["question_uid"])
    normalized_data.append(normalized_q)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        normalized_data,
        f,
        indent=4,
        ensure_ascii=False
    )

print(f"Normalized {len(normalized_data)} questions.")
