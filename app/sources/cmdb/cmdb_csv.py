import csv
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CMDB_FILE = Path(
    os.getenv(
        "PEKA_CMDB_FILE",
        str(Path.home() / "Documents/Peka/data/cmdb/tuple_cmdb.csv"),
    )
)


def get_ci(ci_name: str):
    if not CMDB_FILE.exists():
        return None

    with open(CMDB_FILE, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["ci_name"].lower() == ci_name.lower():
                return row

            if row.get("ip", "").lower() == ci_name.lower():
                return row

    return None


def find_ci_in_text(question: str):
    if not CMDB_FILE.exists():
        return None

    q = question.lower()

    with open(CMDB_FILE, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["ci_name"].lower() in q:
                return row

            if row.get("ip", "").lower() in q:
                return row

    return None