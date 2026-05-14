"""
BitHub V2 — db_ingest.py
Ingests normalized questions + AI solutions into MySQL via SSH sudo mysql.
All credentials are loaded from .env — never hardcode secrets.
"""

import json
import time
import os
import paramiko
from pathlib import Path
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv(Path(__file__).parent / ".env")

BASE_DIR        = Path(__file__).parent
NORMALIZED_FILE = BASE_DIR / "normalized_MA24103.json"
SOLUTIONS_FILE  = BASE_DIR / "generated_solutions.json"
SQL_FILE        = BASE_DIR / "bithub_ingest.sql"

SUBJECT         = "Mathematics 2"
SUBJECT_CODE    = "MA24103"

# Credentials from .env — see .env.example for required keys
SSH_HOST        = os.getenv("DB_SSH_HOST")       # e.g. 192.168.1.34
SSH_USER        = os.getenv("DB_SSH_USER")       # e.g. megahacker
SSH_PASS        = os.getenv("DB_SSH_PASS")       # sudo password
DB_NAME         = os.getenv("DB_NAME", "questions")
REMOTE_SQL_PATH = "/tmp/bithub_ingest.sql"

if not all([SSH_HOST, SSH_USER, SSH_PASS]):
    raise ValueError("Missing required environment variables. Check your .env file (see .env.example).")


def esc(val):
    if val is None:
        return "NULL"
    s = str(val)
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace("\0", "\\0")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return f"'{s}'"


def derive_difficulty(marks):
    if marks is None:
        return "NULL"
    if int(marks) <= 2:
        return "'easy'"
    elif int(marks) == 3:
        return "'medium'"
    else:
        return "'hard'"


def build_sql_file(questions, solutions_map):
    print("Building INSERT SQL file...")
    lines = ["-- BitHub V2 INSERT statements", ""]

    for q in questions:
        uid  = q.get("question_uid", "")
        sol  = solutions_map.get(uid, {})
        tags = json.dumps(q.get("tags", []), ensure_ascii=False) if q.get("tags") is not None else None

        lines.append(
            f"INSERT INTO questions (question_uid,exam,subject,subject_code,module,year,question_number,question_text,question_latex,solution_text,solution_latex,final_answer,tags,question_type,confidence_score,is_verified,latex_valid,generated_by,marks,difficulty) VALUES ("
            f"{esc(uid)},{esc(q.get('source_exam'))},{esc(SUBJECT)},{esc(SUBJECT_CODE)},{esc(str(q.get('module_number','')))},{esc(q.get('source_year'))},{esc(q.get('question_number'))},{esc(q.get('question_text'))},{esc(q.get('question_latex'))},{esc(sol.get('solution_text'))},{esc(sol.get('solution_latex'))},{esc(sol.get('final_answer'))},{esc(tags)},{esc(q.get('question_type'))},{esc(sol.get('confidence_score'))},{int(q.get('is_verified',False))},{int(q.get('latex_valid',True))},{esc(sol.get('generated_by'))},{esc(q.get('marks'))},{derive_difficulty(q.get('marks'))}"
            f") ON DUPLICATE KEY UPDATE solution_text=VALUES(solution_text),solution_latex=VALUES(solution_latex),final_answer=VALUES(final_answer),confidence_score=VALUES(confidence_score),generated_by=VALUES(generated_by);"
        )

    SQL_FILE.write_text("\n".join(lines), encoding="utf-8")
    size_kb = SQL_FILE.stat().st_size / 1024
    print(f"  {SQL_FILE.name} ({size_kb:.1f} KB, {len(questions)} inserts)\n")


def shell_send(shell, cmd, wait=1.5):
    """Send a command to an interactive shell and collect output."""
    shell.send(cmd + "\n")
    time.sleep(wait)
    out = ""
    while shell.recv_ready():
        out += shell.recv(65536).decode("utf-8", errors="replace")
    return out


def main():
    print("=" * 55)
    print("BitHub V2 -- DB Ingestion")
    print("=" * 55 + "\n")

    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    with open(SOLUTIONS_FILE, "r", encoding="utf-8") as f:
        solutions_map = {s["question_uid"]: s for s in json.load(f)}

    print(f"Loaded: {len(questions)} questions | {len(solutions_map)} solutions\n")
    build_sql_file(questions, solutions_map)

    print(f"SSH -> {SSH_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15)
    print("Connected.\n")

    # Upload SQL file
    print(f"Uploading to {REMOTE_SQL_PATH}...")
    sftp = ssh.open_sftp()
    sftp.put(str(SQL_FILE), REMOTE_SQL_PATH)
    sftp.close()
    print("Uploaded.\n")

    # Open an INTERACTIVE shell — mimics exactly what the user would do in terminal
    shell = ssh.invoke_shell()
    time.sleep(1)
    shell.recv(65536)  # consume login banner/prompt

    print("Entering sudo mysql session...")

    # Open sudo mysql interactively
    out = shell_send(shell, f"sudo mysql {DB_NAME}", wait=1.5)

    # Send sudo password
    out = shell_send(shell, SSH_PASS, wait=3)
    # Check if we're at mysql>
    if "mysql>" not in out and "mysql>" not in shell_send(shell, "", wait=1):
        print(f"  [ERROR] Could not enter mysql: {out}")
        ssh.close()
        return

    print("  mysql shell active.")

    # Step 1: Get existing columns first, then conditionally ADD only missing ones
    print("  Checking existing schema...")
    cols_raw = shell_send(shell, "SHOW COLUMNS FROM questions;", wait=2)
    existing_cols = set()
    for line in cols_raw.splitlines():
        # mysql --table output has | col | type | ... format
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) > 1 and parts[1] and parts[1] != "Field" and not parts[1].startswith("-"):
                existing_cols.add(parts[1])
    print(f"  Existing columns: {sorted(existing_cols)}")

    new_columns = [
        ("question_uid",     "VARCHAR(64) AFTER id"),
        ("subject_code",     "VARCHAR(50) AFTER subject"),
        ("question_latex",   "LONGTEXT AFTER question_text"),
        ("solution_latex",   "LONGTEXT AFTER solution_text"),
        ("final_answer",     "TEXT AFTER solution_latex"),
        ("tags",             "JSON AFTER final_answer"),
        ("question_type",    "VARCHAR(50) AFTER tags"),
        ("confidence_score", "FLOAT AFTER question_type"),
        ("is_verified",      "TINYINT(1) DEFAULT 0 AFTER confidence_score"),
        ("latex_valid",      "TINYINT(1) DEFAULT 1 AFTER is_verified"),
        ("generated_by",     "VARCHAR(100) AFTER latex_valid"),
    ]

    print("  Running ALTER TABLE (skipping existing columns)...")
    for col, defn in new_columns:
        if col in existing_cols:
            print(f"    SKIP (exists): {col}")
            continue
        stmt = f"ALTER TABLE questions ADD COLUMN {col} {defn};"
        out_a = shell_send(shell, stmt, wait=3)
        err_lines = [l for l in out_a.splitlines() if "error" in l.lower()]
        if err_lines:
            print(f"    FAIL {col}: {err_lines[0][:100]}")
        else:
            print(f"    OK: + {col}")

    # Add unique index on question_uid if it wasn't there before
    if "question_uid" not in existing_cols:
        idx_out = shell_send(shell, "CREATE UNIQUE INDEX uniq_uid ON questions (question_uid);", wait=2)
        print("    OK: UNIQUE INDEX" if "error" not in idx_out.lower() else f"    WARN index: {idx_out[:80]}")

    # Verify
    chk = shell_send(shell, "SHOW COLUMNS FROM questions LIKE 'question_uid';", wait=2)
    if "question_uid" not in chk:
        print("\n[FATAL] question_uid still missing. Aborting.")
        shell_send(shell, "exit;", wait=1)
        ssh.close()
        return
    print("  Schema OK.\n")

    # Step 2: Source the INSERT-only SQL file
    print("  Sourcing INSERT statements...")
    out = shell_send(shell, f"source {REMOTE_SQL_PATH};", wait=25)
    lines = [l for l in out.splitlines() if l.strip() and "password" not in l.lower()]
    print("\n".join(lines[-20:]) if lines else "  (silent)")

    # Step 4: validate
    print("\nValidating...")
    out_v = shell_send(shell, f"SELECT COUNT(*) AS total FROM questions WHERE subject_code='MA24103';", wait=3)
    out_v2 = shell_send(shell, f"SELECT exam, year, COUNT(*) n FROM questions WHERE subject_code='MA24103' GROUP BY exam, year ORDER BY year, exam;", wait=3)
    out_v3 = shell_send(shell, f"SELECT difficulty, COUNT(*) n FROM questions WHERE subject_code='MA24103' GROUP BY difficulty;", wait=3)

    for block in [out_v, out_v2, out_v3]:
        clean = "\n".join(l for l in block.splitlines() if l.strip() and "password" not in l.lower())
        if clean.strip():
            print(clean)

    # Step 5: exit mysql
    shell_send(shell, "exit;", wait=1)

    # Cleanup remote file
    shell_send(shell, f"rm -f {REMOTE_SQL_PATH}", wait=1)
    shell.close()
    ssh.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
