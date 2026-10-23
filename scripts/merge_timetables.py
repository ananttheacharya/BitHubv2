# pyrefly: ignore[missing-import]
"""Classroom Finder — Timetable Data Merging Pipeline.

This script processes raw college timetable CSV files from data/raw/,
dynamically detects their headers, normalises column names, extracts course
metadata from filenames, validates all records, and outputs a merged master
timetable along with detailed diagnostic reports.

Execution:
    python3 scripts/merge_timetables.py
"""

import csv
import hashlib
from pathlib import Path
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

# Base project paths (using pathlib for cross-platform portability)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

# Output artifact paths
MASTER_CSV_PATH = PROCESSED_DATA_DIR / "master_timetable.csv"
MERGE_REPORT_PATH = PROCESSED_DATA_DIR / "merge_report.txt"
WARNINGS_CSV_PATH = PROCESSED_DATA_DIR / "validation_warnings.csv"

# Exact canonical column order required for master_timetable.csv
CANONICAL_SCHEMA = [
    "course",
    "semester",
    "section",
    "day",
    "time",
    "subject",
    "faculty_code",
    "venue",
    "source_file",
    "source_row",
]

# Essential timetable fields that must be present and non-empty
REQUIRED_TIMETABLE_FIELDS = ["day", "time", "subject", "venue"]

# Header aliases mapping raw header names (lowercased & stripped) to canonical keys
HEADER_ALIASES = {
    "day": "day",
    "time": "time",
    "subject": "subject",
    "subject / activity": "subject",
    "subject/activity": "subject",
    "activity": "subject",
    "faculty": "faculty_code",
    "faculty code": "faculty_code",
    "faculty_code": "faculty_code",
    "venue": "venue",
    "room": "venue",
}

# The identity tuple used to detect true duplicates (excludes source_file and source_row)
DUPLICATE_KEY_FIELDS = (
    "course",
    "semester",
    "section",
    "day",
    "time",
    "subject",
    "faculty_code",
    "venue",
)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def normalise_header_cell(cell: str) -> str:
    """Normalises a header cell string by stripping whitespace and converting to lowercase."""
    return cell.strip().lower()


def parse_filename(filepath: Path) -> Tuple[str, str, str, List[Tuple[str, str]]]:
    """Extracts course, semester, and section metadata from a timetable CSV filename.

    Rules established in Phase 1 and approved by user:
      1. Course: Preserve degree and specialisation (e.g. 'B.Tech CSE', 'B.Tech ECE',
         'MSc (AI & DS)', 'Master of Animation Design'). For the 1st year common cohort,
         use 'B.Tech 1st Year'.
      2. Semester: Preserves integer semester number (e.g. '1', '3', '5', '7').
      3. Section: Explicit letter if present (e.g. 'A', 'B', 'C', 'D'); otherwise empty string ''.
         No sections are inferred.

    Returns:
        (course, semester, section, warnings_list)
    """
    stem = filepath.stem.strip()
    warnings: List[Tuple[str, str]] = []

    # 1. Section extraction (look for "- Section X" or "— Section X")
    sec_match = re.search(r"[-—]\s*Section\s+([A-Za-z0-9]+)\b", stem, re.IGNORECASE)
    section = sec_match.group(1).upper() if sec_match else ""

    # Remove section part to avoid interference with semester/course parsing
    stem_clean = re.sub(r"[-—]\s*Section\s+[A-Za-z0-9]+\b", "", stem, flags=re.IGNORECASE).strip()

    # 2. Semester extraction (look for "Sem X", "Semester X", or "MCA1" / "MCA3")
    sem_match = re.search(r"\bSem(?:ester)?\.?\s*(\d+)\b", stem_clean, re.IGNORECASE)
    if sem_match:
        semester = sem_match.group(1)
    else:
        mca_match = re.search(r"\bMCA(\d+)\b", stem_clean)
        if mca_match:
            semester = mca_match.group(1)
        else:
            semester = ""
            warnings.append(
                ("UNCERTAIN_METADATA", f"Could not extract semester from filename: {filepath.name}")
            )

    # 3. Course extraction (rule-based matching preserving degrees and specialisations)
    if "B.Tech. 1st Year" in stem or "B.Tech 1st Year" in stem:
        course = "B.Tech 1st Year"
    elif stem.startswith("MCA1") or stem.startswith("MCA3"):
        course = "MCA"
    elif "Master of Animation Design" in stem:
        course = "Master of Animation Design"
    elif "MSc (AI & DS)" in stem:
        course = "MSc (AI & DS)"
    elif "B.Sc. Animation and Multimedia" in stem:
        course = "B.Sc. Animation and Multimedia"
    elif "BSc. Visual Communications" in stem:
        course = "BSc. Visual Communications"
    elif "BSc AI&DS" in stem:
        course = "BSc AI&DS"
    elif "B.Tech AI" in stem:
        course = "B.Tech AI"
    elif "B.Tech CSE" in stem:
        course = "B.Tech CSE"
    elif "B.Tech ECE" in stem:
        course = "B.Tech ECE"
    elif "B.Tech EEE" in stem:
        course = "B.Tech EEE"
    elif stem.upper().startswith("BBA"):
        course = "BBA"
    elif stem.upper().startswith("BCA"):
        course = "BCA"
    else:
        # General fallback: extract prefix before comma or "Sem"
        fallback = re.split(r",|\bSem\b|\bSemester\b", stem_clean, flags=re.IGNORECASE)[0].strip()
        course = fallback
        if not course:
            warnings.append(
                ("UNCERTAIN_METADATA", f"Could not extract course from filename: {filepath.name}")
            )

    return course, semester, section, warnings


def find_header_row(rows: List[List[str]]) -> Tuple[Optional[int], Optional[List[str]]]:
    """Dynamically finds the header row by searching for 'day' and 'time' or 'subject'.

    This skips title rows (like 'Table 1') or separator lines of commas.

    Returns:
        (header_index_0_based, header_cells) or (None, None) if not found.
    """
    for idx, row in enumerate(rows):
        cleaned_cells = [normalise_header_cell(c) for c in row]
        has_day = "day" in cleaned_cells
        has_time = any("time" in c for c in cleaned_cells)
        has_subject = any("subject" in c for c in cleaned_cells)

        if has_day and (has_time or has_subject):
            return idx, row

    return None, None


def prune_blank_header_columns(
    header_cells: List[str],
    data_rows: List[List[str]],
    filename: str,
    header_row_1_based: int,
) -> Tuple[List[str], List[List[str]], List[Tuple[Optional[int], str, str]]]:
    """Prunes blank-header columns only when all data cells in that column are empty.

    If any non-empty value exists in a blank-header column, the column is retained
    and a warning is recorded to avoid silent data loss.

    Returns:
        (pruned_header, pruned_data_rows, warnings)
    """
    warnings: List[Tuple[Optional[int], str, str]] = []
    blank_indices = [i for i, c in enumerate(header_cells) if not c.strip()]

    if not blank_indices:
        return header_cells, data_rows, warnings

    columns_to_drop = []
    for col_idx in blank_indices:
        # Check if any row has non-empty data in this column
        has_data = False
        sample_rows = []
        for r_offset, r in enumerate(data_rows, start=header_row_1_based + 1):
            if col_idx < len(r) and r[col_idx].strip():
                has_data = True
                sample_rows.append((r_offset, r[col_idx].strip()))

        if has_data:
            # DO NOT DROP! Retain and report issue
            samples = ", ".join(f"Row {r}: '{v}'" for r, v in sample_rows[:3])
            warnings.append((
                None,
                "BLANK_HEADER_WITH_DATA",
                f"Column index {col_idx} has a blank header but contains data ({samples}). Column retained.",
            ))
        else:
            columns_to_drop.append(col_idx)

    # Prune dropped columns from header and rows
    columns_to_keep = [i for i in range(len(header_cells)) if i not in columns_to_drop]
    new_header = [header_cells[i] for i in columns_to_keep]
    new_data_rows = [
        [r[i] if i < len(r) else "" for i in columns_to_keep]
        for r in data_rows
    ]

    return new_header, new_data_rows, warnings


def validate_record(record: Dict[str, str], source_file: str, source_row: int) -> List[Tuple[str, str]]:
    """Validates a single timetable record and returns any diagnostic warnings.

    Checks:
      - Missing day, time, subject, venue
      - Missing faculty_code
      - Blank or uncertain course or semester metadata
    """
    warnings: List[Tuple[str, str]] = []

    # Essential timetable values
    for field in REQUIRED_TIMETABLE_FIELDS:
        val = record.get(field, "").strip()
        if not val:
            warnings.append(
                (f"MISSING_{field.upper()}", f"Field '{field}' is empty in {source_file} at row {source_row}")
            )

    # Faculty code check (allowed to be empty per user decision 6, but must be flagged)
    if not record.get("faculty_code", "").strip():
        subj = record.get("subject", "")
        ven = record.get("venue", "")
        warnings.append(
            ("MISSING_FACULTY", f"Faculty code is empty for subject '{subj}' at venue '{ven}'")
        )

    # Metadata validation
    if not record.get("course", "").strip():
        warnings.append(("EMPTY_COURSE", f"Course metadata is missing for {source_file}"))
    if not record.get("semester", "").strip():
        warnings.append(("EMPTY_SEMESTER", f"Semester metadata is missing for {source_file}"))

    return warnings


# ==============================================================================
# FILE PROCESSING & AGGREGATION
# ==============================================================================

def process_single_csv(filepath: Path) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Dict[str, int]]:
    """Reads and parses a single timetable CSV file.

    Returns:
        (records_list, warnings_list, file_stats)
    """
    records: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    file_stats = {
        "total_lines": 0,
        "data_rows": 0,
        "header_row": 0,
        "is_parsed": 0,
    }

    # Extract filename metadata
    course, semester, section, fn_warnings = parse_filename(filepath)
    for w_type, w_detail in fn_warnings:
        warnings.append({
            "source_file": filepath.name,
            "source_row": "",
            "warning_type": w_type,
            "detail": w_detail,
        })

    # Read CSV file using utf-8-sig to automatically handle potential BOM
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as fp:
            raw_rows = list(csv.reader(fp))
    except Exception as exc:
        warnings.append({
            "source_file": filepath.name,
            "source_row": "",
            "warning_type": "FILE_DECODE_ERROR",
            "detail": f"Failed to read file as UTF-8: {exc}",
        })
        return records, warnings, file_stats

    file_stats["total_lines"] = len(raw_rows)
    if not raw_rows:
        warnings.append({
            "source_file": filepath.name,
            "source_row": "",
            "warning_type": "EMPTY_FILE",
            "detail": "File contains zero rows.",
        })
        return records, warnings, file_stats

    # Identify header row
    h_idx, header_cells = find_header_row(raw_rows)
    if h_idx is None or header_cells is None:
        warnings.append({
            "source_file": filepath.name,
            "source_row": "",
            "warning_type": "UNRECOGNISED_HEADER",
            "detail": "Could not identify timetable header row (missing 'Day' / 'Time').",
        })
        return records, warnings, file_stats

    file_stats["header_row"] = h_idx + 1
    raw_data_rows = raw_rows[h_idx + 1:]

    # Prune empty blank-header columns if safe
    pruned_header, pruned_data, prune_warnings = prune_blank_header_columns(
        header_cells, raw_data_rows, filepath.name, h_idx + 1
    )
    for r_num, w_type, w_detail in prune_warnings:
        warnings.append({
            "source_file": filepath.name,
            "source_row": str(r_num) if r_num else "",
            "warning_type": w_type,
            "detail": w_detail,
        })

    # Map column positions by matching header names against aliases
    col_mapping: Dict[int, str] = {}
    for col_idx, cell_text in enumerate(pruned_header):
        norm = normalise_header_cell(cell_text)
        if norm in HEADER_ALIASES:
            col_mapping[col_idx] = HEADER_ALIASES[norm]

    # Verify that required columns are mapped
    mapped_fields = set(col_mapping.values())
    missing_required = set(REQUIRED_TIMETABLE_FIELDS) - mapped_fields
    if missing_required:
        warnings.append({
            "source_file": filepath.name,
            "source_row": str(h_idx + 1),
            "warning_type": "MISSING_REQUIRED_COLUMNS",
            "detail": f"Header is missing required fields: {sorted(missing_required)}",
        })
        return records, warnings, file_stats

    # Process data rows
    for offset, row in enumerate(pruned_data):
        original_row_num = h_idx + 2 + offset

        # Skip empty rows if any
        if not any(c.strip() for c in row):
            continue

        # Check field length mismatch
        if len(row) != len(pruned_header):
            warnings.append({
                "source_file": filepath.name,
                "source_row": str(original_row_num),
                "warning_type": "FIELD_COUNT_MISMATCH",
                "detail": f"Row has {len(row)} fields, expected {len(pruned_header)}.",
            })

        # Build canonical record
        record: Dict[str, str] = {
            "course": course.strip(),
            "semester": semester.strip(),
            "section": section.strip(),
            "day": "",
            "time": "",
            "subject": "",
            "faculty_code": "",
            "venue": "",
            "source_file": filepath.name,
            "source_row": str(original_row_num),
        }

        for c_idx, field_name in col_mapping.items():
            if c_idx < len(row):
                record[field_name] = row[c_idx].strip()

        # Validate the record values
        row_warnings = validate_record(record, filepath.name, original_row_num)
        for w_type, w_detail in row_warnings:
            warnings.append({
                "source_file": filepath.name,
                "source_row": str(original_row_num),
                "warning_type": w_type,
                "detail": w_detail,
            })

        records.append(record)

    file_stats["data_rows"] = len(records)
    file_stats["is_parsed"] = 1
    return records, warnings, file_stats


def detect_exact_duplicates(records: List[Dict[str, str]]) -> Tuple[int, List[Dict[str, str]]]:
    """Finds exact duplicate records based on full timetable identity.

    Excludes source_file and source_row from comparison.
    Per Decision 7: compares course, semester, section, day, time, subject,
    faculty_code, and venue.

    Returns:
        (total_duplicate_occurrences, duplicate_details)
    """
    seen: Dict[Tuple[str, ...], List[Dict[str, str]]] = defaultdict(list)
    for rec in records:
        key = tuple(rec[f] for f in DUPLICATE_KEY_FIELDS)
        seen[key].append(rec)

    duplicate_occurrences = 0
    duplicate_details: List[Dict[str, str]] = []

    for key, occurrences in seen.items():
        if len(occurrences) > 1:
            # Each occurrence after the first is counted as a duplicate
            duplicate_occurrences += len(occurrences) - 1
            for dup in occurrences[1:]:
                duplicate_details.append({
                    "source_file": dup["source_file"],
                    "source_row": dup["source_row"],
                    "warning_type": "DUPLICATE_RECORD",
                    "detail": (
                        f"Exact duplicate of record from {occurrences[0]['source_file']} "
                        f"(Row {occurrences[0]['source_row']}): {dict(zip(DUPLICATE_KEY_FIELDS, key))}"
                    ),
                })

    return duplicate_occurrences, duplicate_details


# ==============================================================================
# REPORTING & ARTIFACT WRITERS
# ==============================================================================

def write_master_csv(records: List[Dict[str, str]], output_path: Path) -> None:
    """Writes all processed records to master_timetable.csv."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=CANONICAL_SCHEMA)
        writer.writeheader()
        writer.writerows(records)


def write_validation_warnings_csv(warnings: List[Dict[str, str]], output_path: Path) -> None:
    """Writes all validation warnings to validation_warnings.csv."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = ["source_file", "source_row", "warning_type", "detail"]
    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=schema)
        writer.writeheader()
        writer.writerows(warnings)


def write_merge_report(report_data: dict, output_path: Path) -> None:
    """Writes the comprehensive merge report text file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "=" * 78,
        "CLASSROOM FINDER — MASTER TIMETABLE MERGE REPORT",
        "=" * 78,
        "",
        "1. EXECUTION SUMMARY",
        f"  - Total Input CSV Files Discovered:  {report_data['total_files']}",
        f"  - Successfully Parsed Files:         {report_data['parsed_files']}",
        f"  - Failed Files:                      {report_data['failed_files_count']}",
        f"  - Total Timetable Records Processed: {report_data['total_records']}",
        f"  - Rows With Validation Warnings:     {report_data['rows_with_warnings_count']}",
        f"  - Exact Duplicate Records Detected:  {report_data['duplicate_count']}",
        "",
        "2. WARNING COUNTS BY CATEGORY",
    ]

    warning_counts = report_data["warning_counts_by_type"]
    if warning_counts:
        for cat, cnt in sorted(warning_counts.items()):
            lines.append(f"  - {cat:<28}: {cnt}")
    else:
        lines.append("  (No validation warnings detected)")

    lines.extend([
        "",
        "3. PER-FILE PROCESSING DETAILS",
        f"  {'#':<3} {'Filename':<50} {'Rows':<6} {'Header':<8} {'Status'}",
        "  " + "-" * 74,
    ])

    for item in report_data["per_file_details"]:
        lines.append(
            f"  {item['index']:<3} {item['filename']:<50} {item['data_rows']:<6} "
            f"Row {item['header_row']:<4} {item['status']}"
        )

    lines.extend([
        "",
        "4. DETAILED VALIDATION WARNINGS & DIAGNOSTICS",
    ])

    all_warnings = report_data["all_warnings"]
    if all_warnings:
        for idx, w in enumerate(all_warnings, 1):
            row_str = f"Row {w['source_row']}" if w['source_row'] else "File-level"
            lines.append(f"  [{idx:02d}] {w['source_file']} ({row_str})")
            lines.append(f"       Type:   {w['warning_type']}")
            lines.append(f"       Detail: {w['detail']}")
    else:
        lines.append("  (Zero diagnostic warnings recorded)")

    lines.extend([
        "",
        "5. RECORDS REQUIRING MANUAL REVIEW",
    ])
    review_records = report_data["manual_review_records"]
    if review_records:
        for rev in review_records:
            lines.append(f"  - File: {rev['source_file']}, Row: {rev['source_row']}")
            lines.append(f"    Issue: {rev['detail']}")
    else:
        lines.append("  (No records requiring manual review)")

    lines.extend([
        "",
        "6. GENERATED OUTPUT ARTIFACTS",
        f"  - Master Timetable CSV:   {MASTER_CSV_PATH}",
        f"  - Validation Warnings CSV:{WARNINGS_CSV_PATH}",
        f"  - Merge Report Text:      {MERGE_REPORT_PATH}",
        "",
        "=" * 78,
        "END OF REPORT",
        "=" * 78,
    ])

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")


def compute_directory_checksums(directory: Path) -> Dict[str, str]:
    """Computes SHA-256 hashes of all files in a directory to verify data integrity."""
    checksums = {}
    for filepath in sorted(directory.glob("*.csv")):
        h = hashlib.sha256()
        with open(filepath, "rb") as fp:
            while chunk := fp.read(65536):
                h.update(chunk)
        checksums[filepath.name] = h.hexdigest()
    return checksums


# ==============================================================================
# MAIN EXECUTION PIPELINE
# ==============================================================================

def main() -> int:
    """Runs the complete timetable merge pipeline."""
    print("=" * 70)
    print("Classroom Finder — Timetable Data Merging Pipeline")
    print("=" * 70)

    # 1. Capture baseline checksums of data/raw/ before processing
    if not RAW_DATA_DIR.exists():
        print(f"ERROR: Raw data directory not found: {RAW_DATA_DIR}", file=sys.stderr)
        return 1

    pre_checksums = compute_directory_checksums(RAW_DATA_DIR)
    raw_files = sorted(list(RAW_DATA_DIR.glob("*.csv")))
    print(f"[*] Discovered {len(raw_files)} CSV files in {RAW_DATA_DIR}")

    # 2. Process all files
    all_records: List[Dict[str, str]] = []
    all_warnings: List[Dict[str, str]] = []
    per_file_details = []
    failed_files: List[str] = []

    for idx, fpath in enumerate(raw_files, 1):
        records, warnings, stats = process_single_csv(fpath)
        all_records.extend(records)
        all_warnings.extend(warnings)

        status_str = "SUCCESS" if stats["is_parsed"] else "FAILED"
        if not stats["is_parsed"]:
            failed_files.append(fpath.name)

        per_file_details.append({
            "index": idx,
            "filename": fpath.name,
            "data_rows": stats["data_rows"],
            "header_row": stats["header_row"],
            "status": status_str,
        })

    # 3. Detect exact duplicates across the dataset
    dup_count, dup_warnings = detect_exact_duplicates(all_records)
    all_warnings.extend(dup_warnings)

    # 4. Group warning counts
    warning_counts = Counter(w["warning_type"] for w in all_warnings)
    rows_with_warnings = set(
        (w["source_file"], w["source_row"]) for w in all_warnings if w["source_row"]
    )

    # 5. Write generated outputs
    write_master_csv(all_records, MASTER_CSV_PATH)
    write_validation_warnings_csv(all_warnings, WARNINGS_CSV_PATH)

    manual_review = [
        w for w in all_warnings if w["warning_type"] in ("MISSING_FACULTY", "BLANK_HEADER_WITH_DATA")
    ]

    report_data = {
        "total_files": len(raw_files),
        "parsed_files": len(raw_files) - len(failed_files),
        "failed_files_count": len(failed_files),
        "total_records": len(all_records),
        "rows_with_warnings_count": len(rows_with_warnings),
        "duplicate_count": dup_count,
        "warning_counts_by_type": dict(warning_counts),
        "per_file_details": per_file_details,
        "all_warnings": all_warnings,
        "manual_review_records": manual_review,
    }
    write_merge_report(report_data, MERGE_REPORT_PATH)

    # 6. Verify that raw data was NOT modified
    post_checksums = compute_directory_checksums(RAW_DATA_DIR)
    is_raw_unchanged = (pre_checksums == post_checksums)

    # 7. Print Terminal Summary
    print("\n--- Pipeline Execution Summary ---")
    print(f"Total input files discovered:       {len(raw_files)}")
    print(f"Successfully parsed files:          {len(raw_files) - len(failed_files)}")
    print(f"Failed files count:                 {len(failed_files)}")
    print(f"Total timetable records processed:  {len(all_records)}")
    print(f"Rows with validation warnings:      {len(rows_with_warnings)}")
    print(f"Total validation warning entries:   {len(all_warnings)}")
    print(f"Exact duplicate records count:      {dup_count}")
    print(f"Raw data directory unchanged:       {is_raw_unchanged}")

    if warning_counts:
        print("\nWarning counts by category:")
        for cat, cnt in sorted(warning_counts.items()):
            print(f"  - {cat}: {cnt}")
    else:
        print("\nWarning counts by category: None")

    if failed_files:
        print("\nFailed files:", file=sys.stderr)
        for ff in failed_files:
            print(f"  - {ff}", file=sys.stderr)
    else:
        print("Failed files: None (all 36 files parsed successfully)")

    print(f"\nOutputs generated:")
    print(f"  1. Master timetable:    {MASTER_CSV_PATH}")
    print(f"  2. Validation warnings: {WARNINGS_CSV_PATH}")
    print(f"  3. Merge report:        {MERGE_REPORT_PATH}")

    if not is_raw_unchanged:
        print("\nCRITICAL ALERT: Raw data was modified during execution!", file=sys.stderr)
        return 2

    if failed_files:
        return 1

    print("\nPipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
