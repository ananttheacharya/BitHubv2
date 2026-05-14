# MA24103 — Mathematics 2 Data Pipeline

This directory contains the full data pipeline for the **MA24103 (Mathematics 2)** course in BitHub V2.

## What's in here

| File | Purpose |
|---|---|
| `normalization.py` | Cleans raw OCR-scanned JSON, enforces LaTeX formatting, generates semantic tags |
| `solution_generator.py` | Calls the Gemini API to generate step-by-step solutions for each question |
| `db_ingest.py` | Ingests normalized questions + solutions into the MySQL database via SSH |
| `normalized_MA24103.json` | Cleaned dataset — 45 questions (End Sem 2022/23/24, Mid Sem 2023/24) |
| `generated_solutions.json` | AI-generated solutions for all 45 questions |
| `.env.example` | Template for required environment variables |

## Setup

```bash
pip install google-generativeai python-dotenv tqdm paramiko
cp .env.example .env
# Fill in your values in .env
```

## Running the pipeline

```bash
# Step 1: Normalize the raw JSON
python normalization.py

# Step 2: Generate solutions via Gemini API
python solution_generator.py

# Step 3: Ingest into the database
python db_ingest.py
```

## Database Method

MySQL on the server uses `auth_socket` (no TCP password). The ingestion script works by:
1. Building a complete SQL file locally
2. Uploading it via SFTP to `/tmp/` on the server
3. Opening an interactive PTY shell via `paramiko.invoke_shell()`
4. Running `sudo mysql <dbname>` and sending the password to the PTY stdin
5. Using MySQL's `source /tmp/file.sql` command to execute all statements

See the walkthrough documentation for full details on what was tried and why this method works.

## Environment Variables

All credentials must be set in a `.env` file (see `.env.example`). **Never commit `.env` to git.**

```
GEMINI_API_KEY=...
DB_SSH_HOST=...
DB_SSH_USER=...
DB_SSH_PASS=...
DB_NAME=questions
```
