"""
BitHub V2 — cs_answer_generator.py
Parses C Lab Assignment.md and uses Gemini to generate OJ metadata.
"""

import os
import re
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
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MATERIAL_DIR = ROOT_DIR / "Study Material" / "CS24102"
ANSWERS_DIR = BASE_DIR / "answers"
ANSWERS_DIR.mkdir(exist_ok=True)

MODEL_NAME = "gemini-3.1-flash-lite"
MAX_RETRIES = 3

load_dotenv(BASE_DIR / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found in test_environment_pipeline/.env"
    )

genai.configure(api_key=API_KEY)

# ------------------------------------------------------------------
# PARSER
# ------------------------------------------------------------------

def parse_markdown(filepath: Path) -> list:
    content = filepath.read_text(encoding="utf-8")
    
    # Split by **number.**
    pattern = re.compile(r'\*\*(\d+)\.\*\*\s+(.*?)(?=\*\*\d+\.\*\*|\Z)', re.DOTALL)
    matches = pattern.findall(content)
    
    questions = []
    for num, text in matches:
        questions.append({
            "problem_id": f"CS24102_Q{num}",
            "question_number": int(num),
            "question_text": text.strip()
        })
    return questions

# ------------------------------------------------------------------
# PROMPT
# ------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert Online Judge (OJ) problem designer.
Given a programming problem description, generate robust JSON metadata for an automated judging system.
The programming language is C.

The output MUST exactly match this JSON schema:
{
  "title": "Short title (2-4 words)",
  "evaluationType": "return_value" or "stdout",
  "functionName": "Name of the C function to implement",
  "returnType": "C return type (e.g. 'int', 'void', 'int*')",
  "parameters": [
    {"type": "int", "name": "a"},
    {"type": "int[]", "name": "arr"},
    {"type": "int", "name": "n"}
  ],
  "testCases": [
    {
      "input": [1, [1, 2, 3], 3],
      "expected_return": 3,
      "expected_stdout": ""
    }
  ],
  "solutionCode": "A complete, working C function that solves the problem. Do NOT include #include <stdio.h> or int main(), ONLY the function definition."
}

Rules for parameters and testCases:
1. ALWAYS use C primitive types (int, float, double, char, etc.) or 1D/2D arrays of primitives.
2. For arrays, the type MUST clearly be an array (e.g., 'int[]' or 'int[10]' or 'int[3][3]' or 'int*').
3. For array inputs, the testCase input must be a JSON array: [1, 2, 3]. For 2D arrays, a nested JSON array: [[1, 2], [3, 4]].
4. NEVER pass custom structs as arguments. If a question asks for a struct, break the struct down into its primitive fields and pass them as separate arguments to the function, or write the testcase such that the function can take primitives.
5. If the function expects a pointer to modify a value (e.g., swapping two integers `void swap(int* a, int* b)`), the parameter type MUST be `int*`. But if possible, avoid passing by pointer if returning the value makes more sense, unless it's strictly required by the question.
6. The testCase "input" array must exactly match the length and order of the "parameters" array.

Rules for evaluationType:
- Use "stdout" if the problem asks to print a pattern, print Hello World, or display specific formatted output. 
- Use "return_value" if the problem asks to calculate, compute, or return a specific logical/mathematical value.
- If evaluationType is "stdout", the test case MUST have "expected_stdout" matching the exact output, and "expected_return" can be null.
- If evaluationType is "return_value", "expected_return" must contain the expected result, and "expected_stdout" can be "".

Generate 2 diverse test cases per problem.
The solutionCode MUST be valid C code implementing the functionName and EXACTLY matching the parameters specified.
Return ONLY valid JSON.
"""

def call_gemini(question_text: str) -> tuple[dict | None, str | None]:
    prompt = f"Problem Description:\n{question_text}\n\n{SYSTEM_PROMPT}"
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception:
        model = genai.GenerativeModel("gemini-1.5-flash")

    gen_config = genai.GenerationConfig(response_mime_type="application/json")

    for attempt in range(MAX_RETRIES):
        try:
            resp = model.generate_content(prompt, generation_config=gen_config)
            raw_text = resp.text.strip()
            
            for fence in ("```json", "```"):
                if raw_text.startswith(fence):
                    raw_text = raw_text[len(fence):]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                if len(parsed) > 0:
                    parsed = parsed[0]
                else:
                    raise ValueError("Empty list returned")
            
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected dict, got {type(parsed)}")
                
            return parsed, None
            
        except Exception as e:
            err = f"Error: {e}"
            
        if attempt == MAX_RETRIES - 1:
            return None, err
        time.sleep(2 ** attempt)

    return None, "Exceeded retries"

def save_json(data: list, filepath: Path) -> None:
    filepath.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

def main():
    md_path = MATERIAL_DIR / "C Lab Assignment.md"
    if not md_path.exists():
        print(f"Error: {md_path} not found.")
        sys.exit(1)
        
    questions = parse_markdown(md_path)
    print(f"Parsed {len(questions)} questions from markdown.")
    
    output_path = ANSWERS_DIR / "CS24102_metadata.json"
    
    existing = []
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
        except:
            pass
            
    completed_ids = {q["problem_id"] for q in existing}
    pending = [q for q in questions if q["problem_id"] not in completed_ids]
    
    print(f"Already processed: {len(completed_ids)}")
    print(f"Pending: {len(pending)}")
    
    if not pending:
        return
        
    with tqdm(total=len(questions), initial=len(completed_ids)) as pbar:
        for q in pending:
            result, err = call_gemini(q["question_text"])
            if result:
                q.update(result)
                existing.append(q)
                save_json(existing, output_path)
            else:
                print(f"Failed Q{q['question_number']}: {err}")
            
            pbar.update(1)
            time.sleep(1) # Rate limit

if __name__ == "__main__":
    main()
