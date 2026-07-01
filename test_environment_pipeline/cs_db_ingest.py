"""
BitHub V2 — cs_db_ingest.py
Ingests CS24102 metadata into the MySQL database.
"""

import json
import time
import os
import sys
from pathlib import Path
import paramiko
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ANSWERS_DIR = BASE_DIR / "answers"
SQL_PATH = BASE_DIR / "CS24102_ingest.sql"

load_dotenv(BASE_DIR / ".env")
SSH_HOST = os.getenv("DB_SSH_HOST")
SSH_USER = os.getenv("DB_SSH_USER")
SSH_PASS = os.getenv("DB_SSH_PASS")
DB_NAME = os.getenv("DB_NAME", "questions")
REMOTE_SQL_PATH = "/tmp/cs24102_ingest.sql"

def esc(val) -> str:
    if val is None: return "NULL"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"'{s}'"

def main():
    metadata_path = ANSWERS_DIR / "CS24102_metadata.json"
    if not metadata_path.exists():
        print(f"Error: {metadata_path} not found.")
        sys.exit(1)
        
    with open(metadata_path, encoding="utf-8") as f:
        problems = json.load(f)
        
    lines = [
        "CREATE TABLE IF NOT EXISTS cs_problems (",
        "  problem_id VARCHAR(50) PRIMARY KEY,",
        "  question_number INT,",
        "  title VARCHAR(255),",
        "  question_text TEXT,",
        "  evaluationType VARCHAR(50),",
        "  functionName VARCHAR(100),",
        "  returnType VARCHAR(50),",
        "  parameters JSON,",
        "  testCases JSON",
        ");",
        ""
    ]
    
    for p in problems:
        lines.append(
            "INSERT INTO cs_problems (problem_id, question_number, title, question_text, evaluationType, functionName, returnType, parameters, testCases) VALUES ("
            f"{esc(p['problem_id'])}, "
            f"{p['question_number']}, "
            f"{esc(p.get('title', ''))}, "
            f"{esc(p.get('question_text', ''))}, "
            f"{esc(p.get('evaluationType', 'return_value'))}, "
            f"{esc(p.get('functionName', ''))}, "
            f"{esc(p.get('returnType', 'void'))}, "
            f"{esc(json.dumps(p.get('parameters', [])))}, "
            f"{esc(json.dumps(p.get('testCases', [])))}"
            ") ON DUPLICATE KEY UPDATE "
            "title=VALUES(title), question_text=VALUES(question_text), "
            "evaluationType=VALUES(evaluationType), functionName=VALUES(functionName), "
            "returnType=VALUES(returnType), parameters=VALUES(parameters), testCases=VALUES(testCases);"
        )
        
    SQL_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Built SQL with {len(problems)} problems.")
    print("Done. (Run manually or use paramiko to upload and source, as done in db_ingest.py)")

if __name__ == "__main__":
    main()
