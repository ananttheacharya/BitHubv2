"""
BitHub V2 — normalization.py
Universal question normalizer.
  - Reads raw JSONs from raw_questions/
  - Detects subject from filename (e.g. PH24101_Derivation → Physics)
  - Strips any leftover 'answer' field
  - Adds 'subject' and 'subject_code' to every record
  - Generates a globally-unique question_uid (sha256 of subject_code + question_text)
  - Writes normalized output to normalized_questions/<stem>_normalized.json
"""

import json
import re
import sys
import hashlib
from pathlib import Path

BASE_DIR            = Path(__file__).parent
RAW_DIR             = BASE_DIR / "raw_questions"
NORMALIZED_DIR      = BASE_DIR / "normalized_questions"
NORMALIZED_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# SUBJECT REGISTRY  (add new codes here as needed)
# ------------------------------------------------------------------
SUBJECT_REGISTRY = {
    "MA24103": "Mathematics 2",
    "MA24101": "Mathematics 1",
    "PH24101": "Physics",
    "EC24101": "Basics of Electronic Engineering",
    "CH24101": "Chemistry",
    "CS24101": "Programming for Problem Solving",
    "CE24101": "Environmental Sciences",
    "ME24101": "Basics of Mechanical Engineering",
    "EE24101": "Basics of Electrical Engineering",
}

# ------------------------------------------------------------------
# OCR + LATEX NORMALIZATION MAPS
# ------------------------------------------------------------------
LATEX_REPLACEMENTS = {
    r"J'\*n\(x\)":        r"J_n'(x)",
    r"J\*{n-1}\(x\)":    r"J_{n-1}(x)",
    r"j_([0-9])":         r"J_\1",
    r"(?<!\\)\bSin\b":    r"\\sin",
    r"(?<!\\)\bCos\b":    r"\\cos",
    r"(?<!\\)\bTan\b":    r"\\tan",
    r"(?<!\\)\bln\b":     r"\\ln",
}

TEXT_READABILITY_MAP = {
    r"\\partial":           "∂",
    r"\\pi":                "π",
    r"\\int":               "∫",
    r"\\oint":              "∮",
    r"\\le":                "≤",
    r"\\ge":                "≥",
    r"\\mu":                "μ",
    r"\\sigma":             "σ",
    r"\\sqrt":              "√",
    r"\\infty":             "∞",
    r"\^2":                 "²",
    r"\^3":                 "³",
    r"\\left":              "",
    r"\\right":             "",
    r"\\frac":              "",
    r"\{":                  "(",
    r"\}":                  ")",
    r"\\quad":              " ",
    r"\\text":              "",
    r"\\sin":               "sin",
    r"\\cos":               "cos",
    r"\\tan":               "tan",
    r"\\ln":                "ln",
    r"\\begin\{cases\}":    "",
    r"\\end\{cases\}":      "",
    r"\\begin\{array\}":    "",
    r"\\end\{array\}":      "",
    r"\\hline":             "",
    r"&":                   " ",
    r"\\\\":                " ",
    r"\s+":                 " ",
}

# ------------------------------------------------------------------
# TAG TAXONOMY  (covers all registered subjects)
# ------------------------------------------------------------------
TAG_RULES = [
    # Mathematics 2
    (["fourier"],                                            "Fourier Series"),
    (["legendre", "p_n"],                                   "Legendre Polynomials"),
    (["bessel", "j_", "j'"],                                "Bessel Functions"),
    (["wave equation", "vibration of a string"],            "Wave Equation"),
    (["probability", "binomial", "poisson",
      "random variable", "pdf"],                            "Probability"),
    (["wronskian"],                                         "Wronskian"),
    (["harmonic", "analytic", "contour", "\\oint", "dz"],   "Complex Analysis"),
    (["differential equation", "y''", "d^2y",
      "dy/dx", "complementary function",
      "particular integral"],                               "Differential Equations"),
    (["variation of parameter"],                            "Variation of Parameters"),
    # Physics
    (["interference", "thin film", "path difference"],      "Interference"),
    (["newton's ring", "newton rings"],                     "Newton's Rings"),
    (["diffraction", "fraunhofer", "fringe"],               "Diffraction"),
    (["wedge", "wedge film"],                               "Wedge Film"),
    (["gauss", "maxwell", "ampere", "faraday"],             "Maxwell's Equations"),
    (["electrostatic", "electric field",
      "potential", "coulomb"],                              "Electrostatics"),
    (["boundary condition", "dielectric"],                  "Boundary Conditions"),
    (["lorentz", "special theory of relativity",
      "postulate", "inertial frame"],                       "Special Theory of Relativity"),
    (["compton", "x-ray scatter"],                          "Compton Effect"),
    (["schrödinger", "schrodinger", "wave function",
      "time independent"],                                  "Schrödinger Equation"),
    (["particle in a box", "infinite potential well",
      "energy level"],                                      "Particle in a Box"),
    (["quantum", "de broglie", "uncertainty"],              "Quantum Mechanics"),
    (["velocity addition", "time dilation", "length contraction",
      "invariant", "invariance"],                           "Relativistic Mechanics"),
    # Chemistry
    (["thermodynamics", "enthalpy", "entropy", "gibbs"],    "Thermodynamics"),
    (["chemical equilibrium", "le chatelier"],              "Chemical Equilibrium"),
    (["electrochemical", "electrode", "nernst"],            "Electrochemistry"),
    # ECE / EEE
    (["transistor", "mosfet", "bjt", "amplifier"],          "Semiconductor Devices"),
    (["circuit", "kirchhoff", "thevenin", "norton"],        "Circuit Analysis"),
    (["diode", "rectifier", "zener"],                       "Diodes"),
    # Environmental Sciences
    (["pollution", "effluent", "wastewater"],               "Pollution Control"),
    (["ecosystem", "biodiversity"],                         "Ecology"),
    # CS / PPS
    (["algorithm", "sorting", "searching", "complexity"],   "Algorithms"),
    (["array", "pointer", "function", "recursion"],         "Programming Concepts"),
    # Mechanical
    (["stress", "strain", "bending", "torsion"],            "Strength of Materials"),
    (["thermodynamic", "carnot", "heat engine"],            "Engineering Thermodynamics"),
]

# ------------------------------------------------------------------
# TEXT / LATEX NORMALIZERS
# ------------------------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    for pattern, replacement in LATEX_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in TEXT_READABILITY_MAP.items():
        text = re.sub(pattern, replacement, text)
    return text.strip()


def normalize_latex(latex: str) -> str:
    if not latex:
        return ""
    latex = latex.strip()
    for pattern, replacement in LATEX_REPLACEMENTS.items():
        latex = re.sub(pattern, replacement, latex)
    latex = latex.replace(
        r"\left(\frac{\partial y}{\partial t}\right)*{t=0}",
        r"\left.\frac{\partial y}{\partial t}\right|_{t=0}"
    )
    latex = latex.replace(r"\right)*{t=0}", r"\right|_{t=0}")
    return latex

# ------------------------------------------------------------------
# UID — globally unique across subjects
# ------------------------------------------------------------------

def generate_uid(subject_code: str, question_text: str) -> str:
    key = f"{subject_code}::{question_text.lower().strip()}"
    key = re.sub(r"\s+", " ", key)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

# ------------------------------------------------------------------
# AUTO-TAGGING
# ------------------------------------------------------------------

def generate_tags(question_text: str, question_latex: str) -> list[str]:
    tags = set()
    combined = (question_text + " " + question_latex).lower()
    for keywords, tag in TAG_RULES:
        if any(kw in combined for kw in keywords):
            tags.add(tag)
    return sorted(tags)

# ------------------------------------------------------------------
# SUBJECT CODE EXTRACTION FROM FILENAME
# ------------------------------------------------------------------

def parse_subject_code(stem: str) -> str:
    """
    Extract the subject code from a filename stem.
    Examples:
        PH24101_Derivation  → PH24101
        MA24103             → MA24103
        CS24101_MCQ         → CS24101
    """
    match = re.match(r"([A-Z]{2,3}\d{5})", stem, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return stem.upper()

# ------------------------------------------------------------------
# NORMALIZE A SINGLE QUESTION RECORD
# ------------------------------------------------------------------

def normalize_question(q: dict, subject_code: str, subject_name: str) -> dict:
    original_text  = q.get("question_text", "")
    original_latex = q.get("question_latex", "")

    # Normalize fields
    q["question_text"]  = normalize_text(original_text)
    q["question_latex"] = normalize_latex(original_latex)

    # Subject metadata
    q["subject"]      = subject_name
    q["subject_code"] = subject_code

    # Globally unique UID
    q["question_uid"] = generate_uid(subject_code, q["question_text"])

    # Tags (merge existing tags with auto-generated ones)
    existing_tags = q.get("tags") or []
    auto_tags     = generate_tags(original_text, original_latex)
    merged_tags   = sorted(set(existing_tags) | set(auto_tags))
    q["tags"]     = merged_tags

    # Validation flags
    q["is_normalized"] = True
    q["is_verified"]   = False
    q["latex_valid"]   = True

    # Strip the answer field — we do NOT store answers in question records
    q.pop("answer", None)

    return q

# ------------------------------------------------------------------
# FILE PICKER
# ------------------------------------------------------------------

def pick_file(directory: Path, prompt: str) -> Path:
    files = sorted(directory.glob("*.json"))
    if not files:
        print(f"[ERROR] No JSON files found in {directory}")
        sys.exit(1)

    print(f"\n{prompt}")
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f.name}")

    while True:
        try:
            choice = int(input("\nEnter number: ").strip())
            if 1 <= choice <= len(files):
                return files[choice - 1]
        except (ValueError, KeyboardInterrupt):
            pass
        print(f"  Please enter a number between 1 and {len(files)}.")

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    print("=" * 55)
    print("BitHub V2 — Universal Normalizer")
    print("=" * 55)

    # --- Pick input file ---
    if len(sys.argv) > 1:
        arg = Path(sys.argv[1])
        if arg.is_absolute():
            input_path = arg
        elif (BASE_DIR / arg).exists():
            input_path = BASE_DIR / arg
        elif (RAW_DIR / arg.name).exists():
            input_path = RAW_DIR / arg.name
        else:
            input_path = RAW_DIR / arg
    else:
        input_path = pick_file(RAW_DIR, "Select a raw question JSON to normalize:")

    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    stem         = input_path.stem                        # e.g. "PH24101_Derivation"
    subject_code = parse_subject_code(stem)               # e.g. "PH24101"
    subject_name = SUBJECT_REGISTRY.get(
        subject_code,
        f"Unknown Subject ({subject_code})"
    )

    output_path = NORMALIZED_DIR / f"{stem}_normalized.json"

    print(f"\n  Input : {input_path.name}")
    print(f"  Output: {output_path.name}")
    print(f"  Subject Code : {subject_code}")
    print(f"  Subject Name : {subject_name}\n")

    # --- Load raw JSON (handle malformed single-backslash escape) ---
    raw_data = input_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        # Attempt to fix unescaped single backslashes (common OCR artefact)
        raw_data = raw_data.replace("\\", "\\\\")
        data = json.loads(raw_data)

    if not isinstance(data, list):
        print("[ERROR] JSON root must be an array of question objects.")
        sys.exit(1)

    # --- Normalize ---
    normalized_data = []
    seen_uids       = set()
    duplicates      = 0

    for q in data:
        nq = normalize_question(dict(q), subject_code, subject_name)
        uid = nq["question_uid"]

        if uid in seen_uids:
            duplicates += 1
            continue

        seen_uids.add(uid)
        normalized_data.append(nq)

    # --- Write output ---
    output_path.write_text(
        json.dumps(normalized_data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"  [OK] Normalized : {len(normalized_data)} questions")
    if duplicates:
        print(f"  [WARN] Duplicates skipped: {duplicates}")
    print(f"  [OK] Saved to   : {output_path}\n")


if __name__ == "__main__":
    main()
