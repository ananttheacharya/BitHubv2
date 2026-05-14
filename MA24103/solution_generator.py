import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm
from google.generativeai.types import generation_types

# ==========================================
# CONFIGURATION & FILE PATHS
# ==========================================
BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "normalized_MA24103.json"
OUTPUT_FILE = BASE_DIR / "generated_solutions.json"
FAILED_FILE = BASE_DIR / "failed_questions.json"
MALFORMED_LOG = BASE_DIR / "malformed_output_log.txt"

MODEL_NAME = "gemini-3.1-flash-lite" # If this model doesn't exist yet in the API, change to "gemini-1.5-flash"
MAX_RETRIES = 3

# Load environment variables
load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")

genai.configure(api_key=API_KEY)

# ==========================================
# SYSTEM PROMPT
# ==========================================
SYSTEM_PROMPT = """You are a university mathematics solution engine.

Generate a mathematically rigorous, concise, step-by-step solution.

Return ONLY valid JSON.

Schema:
{
  "solution_text": "",
  "solution_latex": "",
  "final_answer": "",
  "confidence_score": 0.0
}

Rules:
- Use proper mathematical reasoning
- Use concise but complete derivation
- Use proper LaTeX formatting
- No markdown
- No code blocks
- No explanations outside JSON
"""

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_json(filepath):
    """Safely load JSON data from a file."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_json(data, filepath):
    """Save data as JSON iteratively."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def log_malformed_output(question_uid, raw_response, error_msg):
    """Log malformed responses that fail JSON validation."""
    with open(MALFORMED_LOG, "a", encoding="utf-8") as f:
        f.write(f"--- FAILED FOR UID: {question_uid} ---\n")
        f.write(f"Error: {error_msg}\n")
        f.write(f"Raw Response:\n{raw_response}\n")
        f.write("-" * 50 + "\n")

def call_gemini(question_text, question_latex):
    """Generate solution via Gemini API with retry logic and JSON parsing."""
    prompt = f"Question Text: {question_text}\n\nQuestion LaTeX: {question_latex}\n\n{SYSTEM_PROMPT}"
    
    # Assuming gemini-1.5-flash as fallback if 3.1 is not available in the library yet
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception:
        model = genai.GenerativeModel("gemini-1.5-flash")

    # Define generation config to strictly enforce JSON output if supported by model
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json"
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            raw_text = response.text.strip()
            
            # Clean up markdown code blocks if the model ignored instructions
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            
            raw_text = raw_text.strip()
            
            # Validate JSON
            parsed_json = json.loads(raw_text)
            
            # Ensure schema keys exist
            required_keys = ["solution_text", "solution_latex", "final_answer", "confidence_score"]
            for key in required_keys:
                if key not in parsed_json:
                    parsed_json[key] = "" if key != "confidence_score" else 0.0

            return parsed_json, None

        except json.JSONDecodeError as e:
            error_msg = f"JSONDecodeError: {str(e)}"
            if attempt == MAX_RETRIES - 1:
                return None, f"{error_msg}\nRaw: {raw_text}"
            time.sleep(2 ** attempt) # Exponential backoff
            
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            if attempt == MAX_RETRIES - 1:
                return None, error_msg
            time.sleep(2 ** attempt) # Exponential backoff
            
    return None, "Exceeded maximum retries."

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    print("Initializing BitHub V2 Solution Generator...")
    
    # Load inputs
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Load existing state
    solutions = load_json(OUTPUT_FILE)
    failed_questions = load_json(FAILED_FILE)
    
    # Setup tracking sets
    completed_uids = {sol.get("question_uid") for sol in solutions if "question_uid" in sol}
    failed_uids = {fq.get("question_uid") for fq in failed_questions if "question_uid" in fq}
    
    # Determine remaining workload
    pending_questions = [q for q in questions if q.get("question_uid") not in completed_uids]
    total_questions = len(questions)
    
    print(f"Total questions found: {total_questions}")
    print(f"Previously completed: {len(completed_uids)}")
    print(f"Remaining to process: {len(pending_questions)}")
    
    if not pending_questions:
        print("All questions have been processed!")
        return

    # Process with progress bar
    with tqdm(total=total_questions, initial=len(completed_uids), desc="Generating Solutions") as pbar:
        for i, q in enumerate(pending_questions):
            uid = q.get("question_uid")
            
            # Attempt to generate answer
            result, error = call_gemini(q.get("question_text", ""), q.get("question_latex", ""))
            
            if result:
                # Build final output object
                answer_doc = {
                    "question_uid": uid,
                    "solution_text": result.get("solution_text", ""),
                    "solution_latex": result.get("solution_latex", ""),
                    "final_answer": result.get("final_answer", ""),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "generated_by": MODEL_NAME
                }
                
                # Incrementally save success
                solutions.append(answer_doc)
                save_json(solutions, OUTPUT_FILE)
                
                # If it previously failed, remove it from failed_questions
                if uid in failed_uids:
                    failed_questions = [fq for fq in failed_questions if fq.get("question_uid") != uid]
                    save_json(failed_questions, FAILED_FILE)
                    failed_uids.remove(uid)

            else:
                # Handle failure
                log_malformed_output(uid, "N/A", error)
                if uid not in failed_uids:
                    failed_questions.append({
                        "question_uid": uid,
                        "question_number": q.get("question_number"),
                        "error_reason": error
                    })
                    save_json(failed_questions, FAILED_FILE)
                    failed_uids.add(uid)
            
            pbar.update(1)
            # Slight delay to avoid aggressive rate limiting
            time.sleep(1.0)
            
    print("\nGeneration process completed!")

if __name__ == "__main__":
    # Testcase logic: We process a single question if running a test to validate the script
    main()
