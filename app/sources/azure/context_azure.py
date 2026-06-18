from collections import defaultdict

from app.sources.azure.azure_client import (
    get_account,
    get_resource_groups,
    get_resources,
    get_vms,
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


def build_azure_context(question: str) -> str:
    q = question.lower()

    account = get_account()

    if _is_error(account):
        return _error_context(account)

    if "vm" in q or "virtual machine" in q:
        return build_azure_vm_context(account)

    if "resource group" in q or "resource groups" in q:
        return build_azure_resource_group_context(account)

    return build_azure_resource_inventory_context(account)


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


def build_azure_vm_context(account: dict) -> str:
    vms = get_vms()

    if _is_error(vms):
        return _error_context(vms)

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
            f"state={vm.get('powerState')} | "
            f"size={vm.get('size')} | "
            f"private_ip={vm.get('privateIps')} | "
            f"public_ip={vm.get('publicIps')}"
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
