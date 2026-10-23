# pyrefly: ignore[missing-import]
"""Classroom Finder — SQLite Database Creation and CSV Ingestion Pipeline.

This script implements the database schema approved in docs/database-schema.md.
It creates the SQLite database, enables foreign-key constraints, sets up tables
and indexes, and safely imports all 711 timetable entries from master_timetable.csv.

Key Design Decisions Implemented:
  1. Time String Preservation & Partial Normalization:
     - All original time strings are preserved in 'time_raw'.
     - Times with explicit AM/PM markers (393 rows) are converted to 24-hour 'HH:MM'
       format and marked as 'CONFIRMED'.
     - Ambiguous times lacking AM/PM markers (318 rows) are kept with NULL start/end
       times and marked as 'UNVALIDATED' pending verified college operating rules.
  2. Uppercase, Hyphenated Canonical Room IDs:
     - Standard classrooms are mapped to verified canonical IDs (e.g. CR-01 .. CR-14).
     - Ambiguous prefixes ('C' vs 'CR') are kept distinct (C-01 .. C-14) to avoid
       automatic merging of unverified rooms.
  3. Non-Classroom Exclusion:
     - Venues like 'Campus', 'Online', composite workshops, and outdoor grounds are
       marked 'is_schedulable_classroom = 0' to exclude them from classroom availability
       searches while fully preserving their timetable records.
  4. Faculty Integrity:
     - Faculty names, emails, and departments are not guessed or invented; they remain
       NULL with is_verified = 0 until official HR records are supplied.
  5. 100% Record Preservation:
     - All 711 timetable records from master_timetable.csv are imported, including the
       record with missing faculty code ('Lock' at 'Campus').

Execution:
    python3 scripts/import_to_sqlite.py
"""

import csv
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ==============================================================================
# CONFIGURATION & FILE PATHS
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "master_timetable.csv"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "classroom_finder.db"


# ==============================================================================
# TIME PARSING & NORMALIZATION
# ==============================================================================

def parse_timetable_time(raw_time: str) -> Tuple[Optional[str], Optional[str], str]:
    """Parses a timetable time string, normalizing only explicit AM/PM formats.

    Returns:
        (start_time_24h, end_time_24h, status)
        where status is 'CONFIRMED' or 'UNVALIDATED'.
    """
    raw_clean = raw_time.strip()

    # Rule 1: If neither AM nor PM is present, keep unvalidated
    if not ("AM" in raw_clean or "PM" in raw_clean):
        return None, None, "UNVALIDATED"

    # Split on en-dash (\u2013), em-dash (\u2014), or hyphen (-)
    parts = re.split(r"[\u2013\u2014\-]", raw_clean)
    if len(parts) != 2:
        return None, None, "UNVALIDATED"

    start_str = parts[0].strip()
    end_str = parts[1].strip()

    # Find explicit markers
    end_match = re.search(r"\b(AM|PM)\b", end_str, re.IGNORECASE)
    end_ampm = end_match.group(1).upper() if end_match else None

    start_match = re.search(r"\b(AM|PM)\b", start_str, re.IGNORECASE)
    start_ampm = start_match.group(1).upper() if start_match else None

    if not end_ampm:
        return None, None, "UNVALIDATED"

    # Infer start AM/PM only when end AM/PM is explicit and deterministic:
    # If end is AM, morning start must be AM.
    # If end is PM:
    #   hours 8, 9, 10, 11 must be AM (e.g. 11:00 AM - 1:50 PM, 11:00 - 12:50 PM)
    #   hours 12, 1, 2, 3, 4, 5 are PM
    if not start_ampm:
        start_digits = re.sub(r"[^\d:]", "", start_str)
        try:
            start_hour = int(start_digits.split(":")[0])
        except (ValueError, IndexError):
            return None, None, "UNVALIDATED"

        if end_ampm == "AM":
            start_ampm = "AM"
        elif end_ampm == "PM":
            if start_hour in (8, 9, 10, 11):
                start_ampm = "AM"
            else:
                start_ampm = "PM"

    def to_hhmm_24(time_text: str, ampm: str) -> Optional[str]:
        digits = re.sub(r"[^\d:]", "", time_text)
        try:
            h_str, m_str = digits.split(":")
            h = int(h_str)
            m = int(m_str)
        except (ValueError, IndexError):
            return None

        if ampm == "PM" and h != 12:
            h += 12
        elif ampm == "AM" and h == 12:
            h = 0

        return f"{h:02d}:{m:02d}"

    start_24 = to_hhmm_24(start_str, start_ampm)
    end_24 = to_hhmm_24(end_str, end_ampm)

    if start_24 and end_24 and start_24 < end_24:
        return start_24, end_24, "CONFIRMED"

    return None, None, "UNVALIDATED"


# ==============================================================================
# VENUE CANONICAL MAPPING & CATEGORIZATION
# ==============================================================================

def build_venue_mapping(raw_venue: str) -> Tuple[str, str, str, int]:
    """Maps a raw venue string to its canonical room ID, display name, type, and schedulability.

    Rules:
      - Standard CR classrooms: CR-01 .. CR-14 (schedulable = 1)
      - Ambiguous C rooms: C-01 .. C-14 kept distinct without merging (schedulable = 1)
      - Labs & Drawing Halls: LAB-01, CL-02, AM-2D-LAB, ED-HALL, etc. (schedulable = 1)
      - Non-classroom / non-physical: Campus, Online (schedulable = 0)
      - Outdoor / composite workshops: schedulable = 0

    Returns:
        (canonical_classroom_id, display_name, venue_type, is_schedulable_classroom)
    """
    v = raw_venue.strip()

    # 1. Standard CR Classroom pattern (e.g. 'CR-01', 'CR 01', 'CR1', 'CR-1')
    m_cr = re.match(r"^CR[\s\-]?0?(\d+)$", v, re.IGNORECASE)
    if m_cr:
        num = int(m_cr.group(1))
        return f"CR-{num:02d}", f"Classroom {num:02d}", "CLASSROOM", 1

    # 2. Distinct C room pattern (e.g. 'C-1', 'C1', 'C 2', 'C10') - kept distinct
    m_c = re.match(r"^C[\s\-]?0?(\d+)$", v, re.IGNORECASE)
    if m_c:
        num = int(m_c.group(1))
        return f"C-{num:02d}", f"Room C-{num:02d}", "CLASSROOM", 1

    # 3. Computer Laboratories & Standard Labs
    if v in ("LAB 1", "LAB1"):
        return "LAB-01", "Computer Laboratory 01", "COMPUTER_LAB", 1
    if v in ("LAB 2", "LAB 02"):
        return "LAB-02", "Computer Laboratory 02", "COMPUTER_LAB", 1
    if v in ("LAB 3", "LAB3"):
        return "LAB-03", "Computer Laboratory 03", "COMPUTER_LAB", 1
    if v == "CL-2":
        return "CL-02", "Computer Laboratory 02 (CL)", "COMPUTER_LAB", 1
    if v == "CL-3":
        return "CL-03", "Computer Laboratory 03 (CL)", "COMPUTER_LAB", 1
    if v == "CL13":
        return "CL-13", "Computer Laboratory 13", "COMPUTER_LAB", 1
    if v == "CLab1":
        return "CL-01", "Computer Laboratory 01 (CLab)", "COMPUTER_LAB", 1
    if v in ("MAD CL", "MADCL"):
        return "MAD-CL", "Master of Animation Design Computer Lab", "COMPUTER_LAB", 1
    if v == "BAM CL":
        return "BAM-CL", "BAM Computer Lab", "COMPUTER_LAB", 1
    if v == "A&M BCL":
        return "AM-BCL", "Animation & Multimedia Basic Computer Lab", "COMPUTER_LAB", 1

    # 4. Specialized Laboratories & Studios
    if v in ("LL", "LL Lab", "Language Lab"):
        return "LANGUAGE-LAB", "Language Laboratory", "SPECIALIZED_LAB", 1
    if v == "VFX Lab":
        return "VFX-LAB", "Visual Effects Studio / Laboratory", "SPECIALIZED_LAB", 1
    if v == "A&M 2D Lab":
        return "AM-2D-LAB", "Animation & Multimedia 2D Lab", "SPECIALIZED_LAB", 1
    if v == "M/C Lab":
        return "MC-LAB", "Machine Laboratory", "SPECIALIZED_LAB", 1

    # 5. Halls & Lecture Studios
    if v in ("ED HALL", "ED Hall"):
        return "ED-HALL", "Engineering Drawing Hall", "DRAWING_HALL", 1
    if v == "TPX":
        return "TPX", "TPX Hall", "SEMINAR_HALL", 1
    if v == "A&M CR":
        return "AM-CR", "Animation & Multimedia Studio Classroom", "CLASSROOM", 1

    # 6. Electronics / Electrical Departmental Rooms
    m_el = re.match(r"^EL[\s\-]?(\d+)$", v, re.IGNORECASE)
    if m_el:
        num = int(m_el.group(1))
        return f"EL-{num:02d}", f"Electronics Room/Lab {num:02d}", "SPECIALIZED_LAB", 1

    # 7. Non-Physical Entities (Preserved in timetable, excluded from classroom search)
    if v == "Campus":
        return "CAMPUS", "Main Campus Grounds / Non-Classroom", "NON_PHYSICAL", 0
    if v == "Online":
        return "ONLINE", "Online / Remote Virtual Session", "NON_PHYSICAL", 0

    # 8. Composite Split Workshops & Outdoor Sports (Preserved, excluded from classroom search)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", v).strip("_")[:24].upper()
    if any(kw in v for kw in ("GYM", "Outdoor", "OD/", "NSS")):
        return f"OUTDOOR-{tag}", f"Outdoor Activity Venue ({v})", "SPORTS_OUTDOOR", 0
    if any(kw in v for kw in ("Lab", "LAB", "Ws", "MWS", "Chem")):
        return f"WORKSHOP-{tag}", f"Composite Workshop Facility ({v})", "WORKSHOP", 0

    return f"COMPOSITE-{tag}", f"Composite / Shared Venue ({v})", "COMPOSITE_OTHER", 0


# ==============================================================================
# DATABASE INITIALIZATION (DDL)
# ==============================================================================

SCHEMA_SQL = """
-- Enable Foreign Key enforcement in SQLite
PRAGMA foreign_keys = ON;

-- 1. Physical Classroom & Venue Inventory
CREATE TABLE IF NOT EXISTS classrooms (
    classroom_id             TEXT PRIMARY KEY,
    display_name             TEXT NOT NULL,
    building                 TEXT,
    floor                    TEXT,
    venue_type               TEXT NOT NULL CHECK (
                                 venue_type IN (
                                     'CLASSROOM',
                                     'COMPUTER_LAB',
                                     'SPECIALIZED_LAB',
                                     'WORKSHOP',
                                     'DRAWING_HALL',
                                     'SEMINAR_HALL',
                                     'SPORTS_OUTDOOR',
                                     'NON_PHYSICAL',
                                     'COMPOSITE_OTHER'
                                 )
                             ),
    is_schedulable_classroom INTEGER NOT NULL DEFAULT 1 CHECK (is_schedulable_classroom IN (0, 1)),
    capacity                 INTEGER CHECK (capacity IS NULL OR capacity > 0),
    is_verified_inventory    INTEGER NOT NULL DEFAULT 0 CHECK (is_verified_inventory IN (0, 1)),
    notes                    TEXT
);

-- 2. Venue Aliases Mapping Table
CREATE TABLE IF NOT EXISTS venue_aliases (
    alias_name             TEXT PRIMARY KEY,
    canonical_classroom_id TEXT NOT NULL REFERENCES classrooms(classroom_id)
                           ON UPDATE CASCADE
                           ON DELETE RESTRICT
);

-- 3. Faculty Staff Directory
CREATE TABLE IF NOT EXISTS faculty (
    faculty_code  TEXT PRIMARY KEY,
    full_name     TEXT,
    email         TEXT,
    department    TEXT,
    is_verified   INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),
    notes         TEXT
);

-- 4. Master Timetable Schedule Entries
CREATE TABLE IF NOT EXISTS timetable_entries (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    course                  TEXT NOT NULL,
    semester                INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 12),
    section                 TEXT NOT NULL DEFAULT '',
    day                     TEXT NOT NULL CHECK (
                                day IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
                            ),
    time_raw                TEXT NOT NULL,
    start_time              TEXT CHECK (start_time IS NULL OR start_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    end_time                TEXT CHECK (end_time IS NULL OR end_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    time_validation_status  TEXT NOT NULL DEFAULT 'UNVALIDATED' CHECK (
                                time_validation_status IN ('CONFIRMED', 'INFERRED', 'UNVALIDATED')
                            ),
    subject                 TEXT NOT NULL,
    faculty_code_raw        TEXT NOT NULL DEFAULT '',
    venue_raw               TEXT NOT NULL,
    classroom_id            TEXT REFERENCES classrooms(classroom_id)
                            ON UPDATE CASCADE
                            ON DELETE SET NULL,
    source_file             TEXT NOT NULL,
    source_row              INTEGER NOT NULL,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),

    CONSTRAINT chk_time_order CHECK (
        (start_time IS NULL AND end_time IS NULL) OR
        (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)
    )
);

-- 5. Timetable-Faculty Junction Table for Co-Teaching
CREATE TABLE IF NOT EXISTS timetable_entry_faculty (
    entry_id     INTEGER NOT NULL REFERENCES timetable_entries(id) ON DELETE CASCADE,
    faculty_code TEXT NOT NULL REFERENCES faculty(faculty_code) ON DELETE RESTRICT,
    role         TEXT NOT NULL DEFAULT 'PRIMARY' CHECK (role IN ('PRIMARY', 'CO_TEACHER', 'LAB_ASSISTANT')),
    PRIMARY KEY (entry_id, faculty_code)
);

-- Indexes for Fast Query Performance
CREATE INDEX IF NOT EXISTS idx_timetable_availability
ON timetable_entries (day, start_time, end_time, classroom_id)
WHERE start_time IS NOT NULL AND end_time IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_timetable_room_day
ON timetable_entries (classroom_id, day, start_time);

CREATE INDEX IF NOT EXISTS idx_timetable_cohort
ON timetable_entries (course, semester, section, day);

CREATE INDEX IF NOT EXISTS idx_timetable_faculty_raw
ON timetable_entries (faculty_code_raw);

CREATE INDEX IF NOT EXISTS idx_timetable_source
ON timetable_entries (source_file, source_row);

CREATE INDEX IF NOT EXISTS idx_entry_faculty_code
ON timetable_entry_faculty (faculty_code);
"""


# ==============================================================================
# INGESTION PIPELINE
# ==============================================================================

def create_database(db_path: Path) -> sqlite3.Connection:
    """Creates a new SQLite database with schema and indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()  # Clean re-creation for idempotency

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def populate_venues(conn: sqlite3.Connection, raw_venues: Set[str]) -> Dict[str, str]:
    """Populates classrooms and venue_aliases tables for all distinct venues.

    Returns:
        alias_to_id mapping dictionary
    """
    alias_to_id: Dict[str, str] = {}
    classrooms_to_insert: Dict[str, Tuple[str, str, int]] = {}

    for raw_v in raw_venues:
        cid, dname, vtype, sched = build_venue_mapping(raw_v)
        alias_to_id[raw_v] = cid
        if cid not in classrooms_to_insert:
            classrooms_to_insert[cid] = (dname, vtype, sched)

    # Insert unique classrooms
    for cid, (dname, vtype, sched) in sorted(classrooms_to_insert.items()):
        conn.execute(
            """
            INSERT INTO classrooms (classroom_id, display_name, venue_type, is_schedulable_classroom, is_verified_inventory)
            VALUES (?, ?, ?, ?, 1)
            """,
            (cid, dname, vtype, sched),
        )

    # Insert venue aliases
    for raw_v, cid in sorted(alias_to_id.items()):
        conn.execute(
            """
            INSERT INTO venue_aliases (alias_name, canonical_classroom_id)
            VALUES (?, ?)
            """,
            (raw_v, cid),
        )

    conn.commit()
    return alias_to_id


def ingest_master_csv(conn: sqlite3.Connection, csv_path: Path) -> Dict[str, int]:
    """Reads master_timetable.csv and ingests all records into SQLite."""
    with open(csv_path, "r", encoding="utf-8", newline="") as fp:
        reader = list(csv.DictReader(fp))

    raw_venues = set(r["venue"] for r in reader)
    alias_to_id = populate_venues(conn, raw_venues)

    # Collect distinct faculty codes
    all_individual_faculty: Set[str] = set()
    for r in reader:
        fac_raw = r["faculty_code"].strip()
        if fac_raw:
            parts = [p.strip() for p in fac_raw.split("/")]
            for p in parts:
                if p and p not in ("LL", "LL Lab"):  # Exclude lab room references
                    all_individual_faculty.add(p)

    # Insert unverified faculty stubs (names remain NULL until official HR data is provided)
    for fcode in sorted(all_individual_faculty):
        conn.execute(
            """
            INSERT INTO faculty (faculty_code, full_name, is_verified)
            VALUES (?, NULL, 0)
            """,
            (fcode,),
        )

    # Insert timetable entries
    confirmed_times = 0
    unvalidated_times = 0
    junction_links = 0

    for r in reader:
        s_time, e_time, status = parse_timetable_time(r["time"])
        if status == "CONFIRMED":
            confirmed_times += 1
        else:
            unvalidated_times += 1

        cid = alias_to_id.get(r["venue"])
        cursor = conn.execute(
            """
            INSERT INTO timetable_entries (
                course, semester, section, day, time_raw,
                start_time, end_time, time_validation_status,
                subject, faculty_code_raw, venue_raw,
                classroom_id, source_file, source_row
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["course"].strip(),
                int(r["semester"]),
                r["section"].strip(),
                r["day"].strip(),
                r["time"].strip(),
                s_time,
                e_time,
                status,
                r["subject"].strip(),
                r["faculty_code"].strip(),
                r["venue"].strip(),
                cid,
                r["source_file"].strip(),
                int(r["source_row"]),
            ),
        )
        entry_id = cursor.lastrowid

        # Insert faculty co-teaching junction rows
        fac_raw = r["faculty_code"].strip()
        if fac_raw:
            parts = [p.strip() for p in fac_raw.split("/")]
            individual_parts = [p for p in parts if p and p not in ("LL", "LL Lab")]
            role = "PRIMARY" if len(individual_parts) == 1 else "CO_TEACHER"
            for p in individual_parts:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO timetable_entry_faculty (entry_id, faculty_code, role)
                    VALUES (?, ?, ?)
                    """,
                    (entry_id, p, role),
                )
                junction_links += 1

    conn.commit()

    return {
        "total_imported": len(reader),
        "distinct_venues": len(raw_venues),
        "distinct_classrooms": len(set(alias_to_id.values())),
        "distinct_faculty": len(all_individual_faculty),
        "confirmed_times": confirmed_times,
        "unvalidated_times": unvalidated_times,
        "junction_links": junction_links,
    }


# ==============================================================================
# INTEGRITY CHECKS & VERIFICATION QUERIES
# ==============================================================================

def run_integrity_checks(conn: sqlite3.Connection) -> Dict[str, any]:
    """Runs database integrity checks and returns metrics."""
    # 1. Foreign Key Verification
    fk_violations = list(conn.execute("PRAGMA foreign_key_check;"))

    # 2. Record counts
    total_entries = conn.execute("SELECT COUNT(*) FROM timetable_entries;").fetchone()[0]
    total_classrooms = conn.execute("SELECT COUNT(*) FROM classrooms;").fetchone()[0]
    schedulable_classrooms = conn.execute(
        "SELECT COUNT(*) FROM classrooms WHERE is_schedulable_classroom = 1;"
    ).fetchone()[0]
    total_faculty = conn.execute("SELECT COUNT(*) FROM faculty;").fetchone()[0]
    total_aliases = conn.execute("SELECT COUNT(*) FROM venue_aliases;").fetchone()[0]
    missing_faculty_entries = conn.execute(
        "SELECT COUNT(*) FROM timetable_entries WHERE faculty_code_raw = '';"
    ).fetchone()[0]

    return {
        "fk_violations_count": len(fk_violations),
        "fk_violations": fk_violations,
        "total_entries": total_entries,
        "total_classrooms": total_classrooms,
        "schedulable_classrooms": schedulable_classrooms,
        "total_faculty": total_faculty,
        "total_aliases": total_aliases,
        "missing_faculty_entries": missing_faculty_entries,
    }


def test_classroom_availability_query(conn: sqlite3.Connection) -> List[Tuple]:
    """Tests the conservative classroom availability query for Monday 10:00 to 11:00.

    Categorizes schedulable classrooms into three distinct, transparent states:
      1. 'CONFIRMED_OCCUPIED': Has confirmed scheduled class overlapping 10:00-11:00.
      2. 'UNRESOLVED_POSSIBLE_OCCUPANCY': Has an unvalidated timetable entry whose raw
         time could conflict with 10:00-11:00 (e.g. '10:00-10:50', '9:00-10:50').
         These rooms are NEVER marked as available or clear.
      3. 'CONFIRMED_AVAILABLE': Schedulable classroom with NO confirmed overlapping
         classes AND NO potential unvalidated conflicts during the requested window.
    """
    query = """
    SELECT 
        c.classroom_id,
        c.display_name,
        c.venue_type,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM timetable_entries t 
                WHERE t.classroom_id = c.classroom_id 
                  AND t.day = 'Monday' 
                  AND t.time_validation_status = 'CONFIRMED' 
                  AND t.start_time < '11:00' 
                  AND t.end_time > '10:00'
            ) THEN 'CONFIRMED_OCCUPIED'
            WHEN EXISTS (
                SELECT 1 FROM timetable_entries t_unval 
                WHERE t_unval.classroom_id = c.classroom_id 
                  AND t_unval.day = 'Monday' 
                  AND t_unval.time_validation_status = 'UNVALIDATED'
                  AND (
                      t_unval.time_raw LIKE '%10:%' 
                      OR (t_unval.time_raw LIKE '9:%' AND t_unval.time_raw NOT LIKE '%9:50%')
                  )
            ) THEN 'UNRESOLVED_POSSIBLE_OCCUPANCY'
            ELSE 'CONFIRMED_AVAILABLE'
        END AS availability_status,
        (
            SELECT COUNT(*) 
            FROM timetable_entries t2 
            WHERE t2.classroom_id = c.classroom_id 
              AND t2.day = 'Monday' 
              AND t2.time_validation_status = 'UNVALIDATED'
        ) AS unvalidated_monday_slots
    FROM classrooms c
    WHERE c.is_schedulable_classroom = 1
    ORDER BY 
        CASE availability_status 
            WHEN 'CONFIRMED_AVAILABLE' THEN 1 
            WHEN 'UNRESOLVED_POSSIBLE_OCCUPANCY' THEN 2 
            ELSE 3 
        END,
        c.classroom_id;
    """
    return list(conn.execute(query))


# ==============================================================================
# MAIN SCRIPT EXECUTION
# ==============================================================================

def main() -> int:
    """Executes the SQLite creation, ingestion, and verification workflow."""
    print("=" * 74)
    print("Classroom Finder — SQLite Database Ingestion Pipeline")
    print("=" * 74)

    if not DEFAULT_CSV_PATH.exists():
        print(f"ERROR: Processed master timetable CSV not found: {DEFAULT_CSV_PATH}", file=sys.stderr)
        return 1

    print(f"[*] Reading master CSV: {DEFAULT_CSV_PATH}")
    print(f"[*] Creating SQLite DB: {DEFAULT_DB_PATH}")

    # 1. Initialize DB and schema
    conn = create_database(DEFAULT_DB_PATH)

    # 2. Ingest CSV data
    stats = ingest_master_csv(conn, DEFAULT_CSV_PATH)
    print(f"[+] Successfully ingested {stats['total_imported']} timetable entries")
    print(f"    - Confirmed normalized time slots: {stats['confirmed_times']}")
    print(f"    - Unvalidated ambiguous slots:     {stats['unvalidated_times']}")
    print(f"    - Unique physical venues/rooms:    {stats['distinct_classrooms']}")
    print(f"    - Distinct raw venue spellings:    {stats['distinct_venues']}")
    print(f"    - Distinct faculty codes:          {stats['distinct_faculty']}")
    print(f"    - Co-teaching junction rows:       {stats['junction_links']}")

    # 3. Run Integrity Checks
    checks = run_integrity_checks(conn)
    print("\n--- Database Integrity Verification ---")
    print(f"Foreign-key violations:             {checks['fk_violations_count']}")
    print(f"Total timetable entries in DB:      {checks['total_entries']} (expected: 711)")
    print(f"Total classrooms/venues:            {checks['total_classrooms']}")
    print(f"Schedulable classrooms:             {checks['schedulable_classrooms']}")
    print(f"Total faculty code directory rows:  {checks['total_faculty']}")
    print(f"Total venue alias mappings:         {checks['total_aliases']}")
    print(f"Entries with missing faculty code:  {checks['missing_faculty_entries']} (expected: 1)")

    if checks["fk_violations_count"] > 0:
        print(f"CRITICAL ERROR: Foreign key violations detected: {checks['fk_violations']}", file=sys.stderr)
        conn.close()
        return 2

    if checks["total_entries"] != 711:
        print(f"CRITICAL ERROR: Entry count mismatch: {checks['total_entries']} != 711", file=sys.stderr)
        conn.close()
        return 3

    # 4. Test Sample Queries
    print("\n--- Testing Classroom Availability Query ---")
    print("Search: Available classrooms on Monday between 10:00 and 11:00")
    print(f"{'Room ID':<12} {'Display Name':<30} {'Type':<16} {'Availability Status':<28} {'Unval Slots'}")
    print("-" * 96)

    sample_results = test_classroom_availability_query(conn)
    # Display sample of rooms across all three states
    for row in sample_results[:12]:
        cid, dname, vtype, status, unval = row
        unval_notice = f"{unval} slot(s)" if unval > 0 else "0 (None)"
        print(f"{cid:<12} {dname:<30} {vtype:<16} {status:<28} {unval_notice}")

    # 5. Test Missing Faculty Record Retrieval
    print("\n--- Traceability Verification: Missing Faculty Record ---")
    missing_row = conn.execute(
        """
        SELECT course, semester, section, day, time_raw, subject, venue_raw, source_file, source_row
        FROM timetable_entries
        WHERE faculty_code_raw = '';
        """
    ).fetchone()
    print(f"Course:      {missing_row[0]} Sem {missing_row[1]} Sec {missing_row[2]}")
    print(f"Subject:     {missing_row[5]}")
    print(f"Venue:       {missing_row[6]}")
    print(f"Day & Time:  {missing_row[3]} at {missing_row[4]}")
    print(f"Source:      {missing_row[7]} (Line {missing_row[8]})")

    conn.close()
    print("\n[SUCCESS] SQLite database successfully built and verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
