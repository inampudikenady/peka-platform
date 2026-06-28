"""
context_inventory.py

Build CI/inventory context without ticket data.
"""

from app.sources.cmdb.inventory import get_inventory_summary, resolve_inventory


def build_inventory_context(identifier: str):
    data = resolve_inventory(identifier)
    provider = data.get("provider")

    if not data.get("found"):
        return f"""
===== Inventory Context =====

CI not found in {provider} CMDB for:
{identifier}
"""

    ci = data.get("cmdb_record", {}) or {}

    return f"""
===== Inventory Context =====

INVENTORY_PROVIDER: {provider}
CI_NAME: {ci.get("name")}
CI_LINK: {ci.get("link")}
IP_ADDRESS: {ci.get("ip_address")}
OS: {ci.get("os")}
DESCRIPTION: {ci.get("short_description")}
APPLICATION: {ci.get("application")}
OWNER: {ci.get("owner")}
ENVIRONMENT: {ci.get("environment")}
CRITICALITY: {ci.get("criticality")}
PATCH_GROUP: {ci.get("patch_group")}
LOCATION: {ci.get("location")}
"""


def build_csv_inventory_context(identifier: str):
    return build_inventory_context(identifier)


def build_servicenow_inventory_context(identifier: str):
    data = get_inventory_summary(identifier)

    if data.get("provider") != "servicenow":
        return build_inventory_context(identifier)

    if not data.get("found"):
        return f"""
===== Inventory Context =====

CI not found in ServiceNow for:
{identifier}
"""

    cmdb = data.get("cmdb_record", {}) or {}

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
