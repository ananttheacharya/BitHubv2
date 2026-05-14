"""
BitHub V2 — answer_generator.py
Universal AI solution generator.
  - Reads normalized JSONs from normalized_questions/
  - Auto-detects subject from the data's 'subject' field
  - Builds a subject-aware and question-type-aware prompt
  - Writes solutions to answers/<stem>_answers.json
  - Supports incremental saving + retry on failure
"""

import os
import json
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import google.generativeai as genai
from google.generativeai.types import generation_types

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
BASE_DIR          = Path(__file__).parent
NORMALIZED_DIR    = BASE_DIR / "normalized_questions"
ANSWERS_DIR       = BASE_DIR / "answers"
ANSWERS_DIR.mkdir(exist_ok=True)

MODEL_NAME  = "gemini-3.1-flash-lite"
MAX_RETRIES = 3

load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found in environment variables. "
        "Please check your .env file."
    )

genai.configure(api_key=API_KEY)

# ------------------------------------------------------------------
# PROMPT TEMPLATES  (subject-aware + question-type-aware)
# ------------------------------------------------------------------

BASE_SCHEMA = """{
  "solution_text": "",
  "solution_latex": "",
  "final_answer": "",
  "confidence_score": 0.0
}"""

BASE_RULES = """Rules:
- Return ONLY valid JSON — no markdown, no code blocks, no commentary outside JSON.
- Use precise mathematical reasoning.
- solution_text: plain-English step-by-step explanation.
- solution_latex: full LaTeX-formatted derivation/solution (no $$ delimiters).
- final_answer: the concise boxed result (plain text or inline LaTeX).
- confidence_score: float 0.0–1.0 reflecting your certainty."""

TYPE_ADDENDUM = {
    "derivation": (
        "This is a DERIVATION question. Your solution must:\n"
        "  1. State all assumptions and starting equations clearly.\n"
        "  2. Show every algebraic / calculus step — do not skip steps.\n"
        "  3. End with the final derived expression clearly stated.\n"
        "  4. Reference any standard theorems or laws used (e.g. Snell's Law, Gauss's Theorem).\n"
    ),
    "proof": (
        "This is a PROOF question. Your solution must:\n"
        "  1. State what is to be proved.\n"
        "  2. Use a rigorous logical argument (direct proof or by contradiction as appropriate).\n"
        "  3. Show all intermediate steps.\n"
        "  4. Conclude with Q.E.D. or equivalent.\n"
    ),
    "numerical": (
        "This is a NUMERICAL question. Your solution must:\n"
        "  1. Identify the given quantities and what is to be found.\n"
        "  2. Write down the relevant formula(s).\n"
        "  3. Substitute values and calculate step by step.\n"
        "  4. State the final numerical answer with units.\n"
    ),
    "analytical": (
        "This is an ANALYTICAL question. Your solution must:\n"
        "  1. Analyse the problem conceptually before computing.\n"
        "  2. Show all working clearly.\n"
        "  3. Interpret the result.\n"
    ),
    "default": (
        "Provide a complete, rigorous, step-by-step solution.\n"
    ),
}


def build_system_prompt(subject: str, question_type: str) -> str:
    type_hint = TYPE_ADDENDUM.get(
        (question_type or "").lower().strip(),
        TYPE_ADDENDUM["default"]
    )
    return (
        f"You are an expert university {subject} solution engine.\n\n"
        f"Generate a rigorous, concise, step-by-step solution.\n\n"
        f"{type_hint}\n"
        f"Return ONLY valid JSON matching this schema:\n{BASE_SCHEMA}\n\n"
        f"{BASE_RULES}"
    )

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def load_json(filepath: Path) -> list:
    if not filepath.exists():
        return []
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_json(data: list, filepath: Path) -> None:
    filepath.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


def log_failure(log_path: Path, uid: str, error: str) -> None:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"--- FAILED: {uid} ---\n{error}\n" + "-" * 50 + "\n")


def call_gemini(
    question_text: str,
    question_latex: str,
    system_prompt: str,
) -> tuple[dict | None, str | None]:
    """Call Gemini with retry + JSON parsing. Returns (parsed_dict, error)."""
    prompt = (
        f"Question (plain text):\n{question_text}\n\n"
        f"Question (LaTeX):\n{question_latex}\n\n"
        f"{system_prompt}"
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception:
        model = genai.GenerativeModel("gemini-1.5-flash")

    gen_config = genai.GenerationConfig(response_mime_type="application/json")

    for attempt in range(MAX_RETRIES):
        try:
            resp     = model.generate_content(prompt, generation_config=gen_config)
            raw_text = resp.text.strip()

            # Strip accidental markdown fences
            for fence in ("```json", "```"):
                if raw_text.startswith(fence):
                    raw_text = raw_text[len(fence):]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)

            # Guarantee all required keys exist
            for key in ("solution_text", "solution_latex", "final_answer"):
                parsed.setdefault(key, "")
            parsed.setdefault("confidence_score", 0.0)

            return parsed, None

        except json.JSONDecodeError as e:
            err = f"JSONDecodeError: {e}"
        except generation_types.StopCandidateException as e:
            err = f"StopCandidateException: {e}"
        except Exception as e:
            err = f"APIError: {e}"

        if attempt == MAX_RETRIES - 1:
            return None, err
        time.sleep(2 ** attempt)  # exponential back-off

    return None, "Exceeded maximum retries."

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
    print("BitHub V2 — Universal Answer Generator")
    print("=" * 55)

    # --- Pick normalized input file ---
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if not input_path.is_absolute():
            input_path = NORMALIZED_DIR / input_path
    else:
        input_path = pick_file(
            NORMALIZED_DIR,
            "Select a normalized question JSON to generate answers for:"
        )

    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    questions = load_json(input_path)
    if not questions:
        print("[ERROR] No questions loaded. Check the file.")
        sys.exit(1)

    # Auto-detect subject from first record
    subject      = questions[0].get("subject",      "University")
    subject_code = questions[0].get("subject_code", "UNKNOWN")

    stem        = input_path.stem                            # e.g. PH24101_Derivation_normalized
    output_stem = stem.replace("_normalized", "")           # PH24101_Derivation
    output_path = ANSWERS_DIR / f"{output_stem}_answers.json"
    failed_path = ANSWERS_DIR / f"{output_stem}_failed.json"
    log_path    = ANSWERS_DIR / f"{output_stem}_malformed.log"

    print(f"\n  Input         : {input_path.name}")
    print(f"  Output        : {output_path.name}")
    print(f"  Subject       : {subject} ({subject_code})")
    print(f"  Model         : {MODEL_NAME}")
    print(f"  Questions     : {len(questions)}\n")

    # --- Load existing progress ---
    answers         = load_json(output_path)
    failed_q        = load_json(failed_path)
    completed_uids  = {a["question_uid"] for a in answers if "question_uid" in a}
    failed_uids     = {f["question_uid"] for f in failed_q if "question_uid" in f}
    pending         = [q for q in questions if q.get("question_uid") not in completed_uids]

    print(f"  Previously completed : {len(completed_uids)}")
    print(f"  Remaining            : {len(pending)}\n")

    if not pending:
        print("  All questions already processed!")
        return

    # --- Process ---
    with tqdm(total=len(questions), initial=len(completed_uids),
              desc="Generating Answers") as pbar:
        for q in pending:
            uid           = q.get("question_uid", "")
            qtype         = q.get("question_type", "default")
            system_prompt = build_system_prompt(subject, qtype)

            result, error = call_gemini(
                q.get("question_text", ""),
                q.get("question_latex", ""),
                system_prompt,
            )

            if result:
                answer_doc = {
                    "question_uid":    uid,
                    "subject_code":    subject_code,
                    "question_type":   qtype,
                    "solution_text":   result.get("solution_text", ""),
                    "solution_latex":  result.get("solution_latex", ""),
                    "final_answer":    result.get("final_answer", ""),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "generated_by":    MODEL_NAME,
                }
                answers.append(answer_doc)
                save_json(answers, output_path)

                # Remove from failed if it was there before
                if uid in failed_uids:
                    failed_q   = [f for f in failed_q if f.get("question_uid") != uid]
                    failed_uids.remove(uid)
                    save_json(failed_q, failed_path)
            else:
                log_failure(log_path, uid, error or "Unknown error")
                if uid not in failed_uids:
                    failed_q.append({
                        "question_uid":    uid,
                        "question_number": q.get("question_number"),
                        "question_type":   qtype,
                        "error_reason":    error,
                    })
                    save_json(failed_q, failed_path)
                    failed_uids.add(uid)

            pbar.update(1)
            time.sleep(0.8)  # gentle rate limiting

    print(f"\n  ✓ Answers saved : {output_path}")
    if failed_q:
        print(f"  ⚠ Failed        : {len(failed_q)} questions → {failed_path.name}")
    print("\n  Done.\n")


if __name__ == "__main__":
    main()
