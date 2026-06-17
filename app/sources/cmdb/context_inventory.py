"""
context_inventory.py

Build CI/inventory context without ticket data.
"""

import os

from dotenv import load_dotenv

from app.sources.servicenow.servicenow_client import get_ci_summary
from app.sources.cmdb.cmdb_csv import get_ci

load_dotenv()


def build_inventory_context(identifier: str):
    provider = os.getenv("CMDB_PROVIDER", "auto").lower()

    if provider == "csv":
        return build_csv_inventory_context(identifier)

    if provider == "servicenow":
        return build_servicenow_inventory_context(identifier)

    # Auto mode is best for demos:
    # 1. Try local CSV CMDB first.
    # 2. Fall back to ServiceNow if the CI is not in CSV.
    csv_context = build_csv_inventory_context(identifier)

    if "CI not found in local CMDB" not in csv_context:
        return csv_context

    return build_servicenow_inventory_context(identifier)


def build_csv_inventory_context(identifier: str):
    ci = get_ci(identifier)

    if not ci:
        return f"""
===== Inventory Context =====

CI not found in local CMDB for:
{identifier}
"""

    return f"""
===== Inventory Context =====

INVENTORY_PROVIDER: csv
CI_NAME: {ci.get("ci_name")}
CI_LINK:
IP_ADDRESS: {ci.get("ip")}
OS: {ci.get("os_type")}
DESCRIPTION: {ci.get("notes")}
APPLICATION: {ci.get("application")}
OWNER: {ci.get("owner")}
ENVIRONMENT: {ci.get("environment")}
CRITICALITY: {ci.get("criticality")}
PATCH_GROUP: {ci.get("patch_group")}
"""


def build_servicenow_inventory_context(identifier: str):
    data = get_ci_summary(identifier)

    if not data.get("found"):
        return f"""
===== Inventory Context =====

CI not found in ServiceNow for:
{identifier}
"""

    cmdb = data.get("cmdb_record", {})

    return f"""
===== Inventory Context =====

INVENTORY_PROVIDER: servicenow
CI_NAME: {cmdb.get("name")}
CI_LINK: {cmdb.get("link")}
IP_ADDRESS: {cmdb.get("ip_address")}
OS: {cmdb.get("os")}
DESCRIPTION: {cmdb.get("short_description")}
LOCATION: {cmdb.get("location")}
"""