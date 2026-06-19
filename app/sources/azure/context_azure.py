from collections import defaultdict

from app.sources.azure.azure_client import (
    get_account,
    get_resource_groups,
    get_resources,
    get_vms,
    get_vm_details,
    get_month_to_date_cost,
    get_cost_by_resource_group,
    get_cost_by_service,
)


def _is_error(data) -> bool:
    return isinstance(data, dict) and data.get("error") is True


def _error_context(data) -> str:
    return f"""
===== Azure Context =====

AZURE_ERROR: true
AZURE_ERROR_MESSAGE: {data.get("message", "Unknown Azure CLI error")}

ACTION_REQUIRED:
Run az login and confirm subscription access.
"""


def _extract_cost_total(cost_data: dict) -> tuple[float, str]:
    rows = cost_data.get("properties", {}).get("rows", [])

    if not rows:
        return 0.0, ""

    return float(rows[0][0] or 0), str(rows[0][1] or "")


def _extract_cost_rows(cost_data: dict) -> list[dict]:
    rows = cost_data.get("properties", {}).get("rows", [])
    output = []

    for row in rows:
        cost = float(row[0] or 0)
        group_or_service = str(row[1] or "Unknown")
        currency = str(row[2] or "")

        output.append({
            "name": group_or_service,
            "cost": cost,
            "currency": currency,
        })

    output.sort(key=lambda x: x["cost"], reverse=True)
    return output


def build_azure_context(question: str) -> str:
    q = question.lower()

    account = get_account()

    if _is_error(account):
        return _error_context(account)

    if "cost breakdown" in q or "spend breakdown" in q or "cost by resource group" in q or "spend by resource group" in q:
        return build_azure_cost_breakdown_context(account)

    if "cost by service" in q or "spend by service" in q or "which services are costing" in q:
        return build_azure_cost_by_service_context(account)

    if "cost" in q or "bill" in q or "billing" in q or "spend" in q:
        return build_azure_cost_context(account)

    if "vm" in q or "virtual machine" in q:
        return build_azure_vm_context(account, question)

    if "resource group" in q or "resource groups" in q:
        return build_azure_resource_group_context(account)

    return build_azure_resource_inventory_context(account)


def build_azure_cost_context(account: dict) -> str:
    cost_data = get_month_to_date_cost()

    if _is_error(cost_data):
        return _error_context(cost_data)

    total_cost, currency = _extract_cost_total(cost_data)

    return f"""
===== Azure Context =====

AZURE_QUERY_TYPE: cost_month_to_date
SUBSCRIPTION_NAME: {account.get("name")}
SUBSCRIPTION_ID: {account.get("id")}
TENANT_ID: {account.get("tenantId")}
USER: {account.get("user")}

MONTH_TO_DATE_COST: {total_cost:.2f}
CURRENCY: {currency}
"""


def build_azure_cost_breakdown_context(account: dict) -> str:
    total_data = get_month_to_date_cost()
    breakdown_data = get_cost_by_resource_group()

    if _is_error(total_data):
        return _error_context(total_data)

    if _is_error(breakdown_data):
        return _error_context(breakdown_data)

    total_cost, currency = _extract_cost_total(total_data)
    rows = _extract_cost_rows(breakdown_data)

    lines = [
        "===== Azure Context =====",
        "",
        "AZURE_QUERY_TYPE: cost_breakdown_resource_group",
        f"SUBSCRIPTION_NAME: {account.get('name')}",
        f"SUBSCRIPTION_ID: {account.get('id')}",
        f"TENANT_ID: {account.get('tenantId')}",
        f"USER: {account.get('user')}",
        "",
        f"MONTH_TO_DATE_COST: {total_cost:.2f}",
        f"CURRENCY: {currency}",
        "",
        "COST_BY_RESOURCE_GROUP:",
    ]

    if not rows:
        lines.append("- No cost rows returned.")

    for row in rows:
        lines.append(
            f"- {row['name']} | cost={row['cost']:.2f} | currency={row['currency']}"
        )

    return "\n".join(lines)


def build_azure_cost_by_service_context(account: dict) -> str:
    total_data = get_month_to_date_cost()
    service_data = get_cost_by_service()

    if _is_error(total_data):
        return _error_context(total_data)

    if _is_error(service_data):
        return _error_context(service_data)

    total_cost, currency = _extract_cost_total(total_data)
    rows = _extract_cost_rows(service_data)

    lines = [
        "===== Azure Context =====",
        "",
        "AZURE_QUERY_TYPE: cost_breakdown_service",
        f"SUBSCRIPTION_NAME: {account.get('name')}",
        f"SUBSCRIPTION_ID: {account.get('id')}",
        f"TENANT_ID: {account.get('tenantId')}",
        f"USER: {account.get('user')}",
        "",
        f"MONTH_TO_DATE_COST: {total_cost:.2f}",
        f"CURRENCY: {currency}",
        "",
        "COST_BY_SERVICE:",
    ]

    if not rows:
        lines.append("- No cost rows returned.")

    for row in rows:
        lines.append(
            f"- {row['name']} | cost={row['cost']:.2f} | currency={row['currency']}"
        )

    return "\n".join(lines)


def build_azure_resource_group_context(account: dict) -> str:
    groups = get_resource_groups()

    if _is_error(groups):
        return _error_context(groups)

    lines = [
        "===== Azure Context =====",
        "",
        "AZURE_QUERY_TYPE: resource_groups",
        f"SUBSCRIPTION_NAME: {account.get('name')}",
        f"SUBSCRIPTION_ID: {account.get('id')}",
        f"TENANT_ID: {account.get('tenantId')}",
        f"USER: {account.get('user')}",
        f"RESOURCE_GROUP_COUNT: {len(groups)}",
        "",
        "RESOURCE_GROUPS:",
    ]

    for group in groups:
        lines.append(
            f"- {group.get('name')} | location={group.get('location')} | status={group.get('status')}"
        )

    return "\n".join(lines)


def build_azure_vm_context(account: dict, question: str) -> str:
    q = question.lower()
    vms = get_vms()

    if _is_error(vms):
        return _error_context(vms)

    selected_vm = None

    for vm in vms:
        vm_name = vm.get("name", "")
        if vm_name and vm_name.lower() in q:
            selected_vm = get_vm_details(vm_id=vm.get("id"))
            break

    if selected_vm:
        if _is_error(selected_vm):
            return _error_context(selected_vm)

        return f"""
===== Azure Context =====

AZURE_QUERY_TYPE: virtual_machine_detail
SUBSCRIPTION_NAME: {account.get("name")}
SUBSCRIPTION_ID: {account.get("id")}
TENANT_ID: {account.get("tenantId")}
USER: {account.get("user")}

VM_NAME: {selected_vm.get("name")}
RESOURCE_GROUP: {selected_vm.get("resourceGroup")}
LOCATION: {selected_vm.get("location")}
SIZE: {selected_vm.get("size")}
POWER_STATE: {selected_vm.get("powerState")}
PRIVATE_IPS: {selected_vm.get("privateIps")}
PUBLIC_IPS: {selected_vm.get("publicIps")}
OS_TYPE: {selected_vm.get("osType")}
"""

    lines = [
        "===== Azure Context =====",
        "",
        "AZURE_QUERY_TYPE: virtual_machines",
        f"SUBSCRIPTION_NAME: {account.get('name')}",
        f"SUBSCRIPTION_ID: {account.get('id')}",
        f"VM_COUNT: {len(vms)}",
        "",
        "VIRTUAL_MACHINES:",
    ]

    if not vms:
        lines.append("- No virtual machines found.")

    for vm in vms:
        lines.append(
            "- "
            f"{vm.get('name')} | "
            f"resource_group={vm.get('resourceGroup')} | "
            f"location={vm.get('location')} | "
            f"size={vm.get('size')} | "
            f"os_type={vm.get('osType')}"
        )

    return "\n".join(lines)


def build_azure_resource_inventory_context(account: dict) -> str:
    resources = get_resources()

    if _is_error(resources):
        return _error_context(resources)

    by_type = defaultdict(list)

    for resource in resources:
        by_type[resource.get("type", "unknown")].append(resource)

    lines = [
        "===== Azure Context =====",
        "",
        "AZURE_QUERY_TYPE: resource_inventory",
        f"SUBSCRIPTION_NAME: {account.get('name')}",
        f"SUBSCRIPTION_ID: {account.get('id')}",
        f"TENANT_ID: {account.get('tenantId')}",
        f"USER: {account.get('user')}",
        f"RESOURCE_COUNT: {len(resources)}",
        "",
        "RESOURCES_BY_TYPE:",
    ]

    for resource_type in sorted(by_type):
        lines.append("")
        lines.append(f"{resource_type}: {len(by_type[resource_type])}")

        for resource in by_type[resource_type][:10]:
            lines.append(
                "- "
                f"{resource.get('name')} | "
                f"resource_group={resource.get('resourceGroup')} | "
                f"location={resource.get('location')}"
            )

    return "\n".join(lines)
