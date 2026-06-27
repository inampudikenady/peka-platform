from app.sources.azure.context_azure import build_azure_context


def _get_value(context: str, key: str) -> str:
    prefix = f"{key}:"

    for line in context.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    return ""


def _section_rows(context: str, section_name: str) -> list[str]:
    rows = []
    capture = False

    for line in context.splitlines():
        stripped = line.strip()

        if stripped == f"{section_name}:":
            capture = True
            continue

        if capture:
            if not stripped:
                continue

            if stripped.endswith(":") and not stripped.startswith("-"):
                break

            if stripped.startswith("-"):
                rows.append(stripped)

    return rows


def build_azure_response(question: str) -> str:
    context = build_azure_context(question)

    if "AZURE_ERROR: true" in context:
        message = _get_value(context, "AZURE_ERROR_MESSAGE")
        action_required = _get_multiline_value(context, "ACTION_REQUIRED")
        return f"""# Azure Error

{message}

## Action Required

{action_required}
"""

    query_type = _get_value(context, "AZURE_QUERY_TYPE")

    if query_type == "cost_month_to_date":
        return _cost_summary(context)

    if query_type == "cost_breakdown_resource_group":
        return _cost_breakdown_resource_group(context)

    if query_type == "cost_breakdown_service":
        return _cost_breakdown_service(context)

    if query_type == "resource_groups":
        return _resource_groups(context)

    if query_type == "virtual_machines":
        return _virtual_machines(context)

    if query_type == "virtual_machine_detail":
        return _virtual_machine_detail(context)

    if query_type == "resource_inventory":
        return _resource_inventory(context)

    return context


def _get_multiline_value(context: str, key: str) -> str:
    prefix = f"{key}:"
    lines = context.splitlines()

    for index, line in enumerate(lines):
        if line.startswith(prefix):
            values = []

            remainder = line.split(":", 1)[1].strip()
            if remainder:
                values.append(remainder)

            for next_line in lines[index + 1:]:
                stripped = next_line.strip()

                if not stripped:
                    if values:
                        break
                    continue

                if stripped.endswith(":") and not stripped.startswith("-"):
                    break

                values.append(stripped)

            return "\n".join(values).strip()

    return ""


def _subscription_header(context: str) -> str:
    return f"""## Subscription

- Name: {_get_value(context, "SUBSCRIPTION_NAME")}
- Subscription ID: {_get_value(context, "SUBSCRIPTION_ID")}
"""


def _cost_summary(context: str) -> str:
    return f"""# Azure Cost Summary

{_subscription_header(context)}

## Month-to-Date Cost

- Actual cost: {_get_value(context, "CURRENCY")} {_get_value(context, "MONTH_TO_DATE_COST")}
"""


def _cost_breakdown_resource_group(context: str) -> str:
    rows = _section_rows(context, "COST_BY_RESOURCE_GROUP")

    lines = [
        "# Azure Cost Breakdown",
        "",
        _subscription_header(context).rstrip(),
        "",
        "## Month-to-Date Cost",
        "",
        f"- Total actual cost: {_get_value(context, 'CURRENCY')} {_get_value(context, 'MONTH_TO_DATE_COST')}",
        "",
        "## Cost by Resource Group",
        "",
    ]

    lines.extend(rows or ["- No cost rows returned."])

    return "\n".join(lines)


def _cost_breakdown_service(context: str) -> str:
    rows = _section_rows(context, "COST_BY_SERVICE")

    lines = [
        "# Azure Cost by Service",
        "",
        _subscription_header(context).rstrip(),
        "",
        "## Month-to-Date Cost",
        "",
        f"- Total actual cost: {_get_value(context, 'CURRENCY')} {_get_value(context, 'MONTH_TO_DATE_COST')}",
        "",
        "## Cost by Service",
        "",
    ]

    lines.extend(rows or ["- No cost rows returned."])

    return "\n".join(lines)


def _resource_groups(context: str) -> str:
    rows = _section_rows(context, "RESOURCE_GROUPS")

    lines = [
        "# Azure Resource Groups",
        "",
        _subscription_header(context).rstrip(),
        "",
        "## Resource Groups",
        "",
    ]

    lines.extend(rows or ["- No resource groups found."])

    return "\n".join(lines)


def _virtual_machines(context: str) -> str:
    rows = _section_rows(context, "VIRTUAL_MACHINES")

    lines = [
        "# Azure Virtual Machines",
        "",
        _subscription_header(context).rstrip(),
        "",
        "## Virtual Machines",
        "",
    ]

    lines.extend(rows or ["- No virtual machines found."])

    return "\n".join(lines)


def _virtual_machine_detail(context: str) -> str:
    return f"""# Azure VM Detail - {_get_value(context, "VM_NAME")}

{_subscription_header(context)}

## VM Details

- Name: {_get_value(context, "VM_NAME")}
- Resource Group: {_get_value(context, "RESOURCE_GROUP")}
- Location: {_get_value(context, "LOCATION")}
- Size: {_get_value(context, "SIZE")}
- Power State: {_get_value(context, "POWER_STATE")}
- Private IPs: {_get_value(context, "PRIVATE_IPS")}
- Public IPs: {_get_value(context, "PUBLIC_IPS")}
- OS Type: {_get_value(context, "OS_TYPE")}
"""


def _resource_inventory(context: str) -> str:
    lines = [
        "# Azure Resource Inventory",
        "",
        _subscription_header(context).rstrip(),
        "",
        "## Summary",
        "",
        f"- Total resources: {_get_value(context, 'RESOURCE_COUNT')}",
        "",
        "## Resources",
        "",
    ]

    capture = False

    for line in context.splitlines():
        stripped = line.strip()

        if stripped == "RESOURCES_BY_TYPE:":
            capture = True
            continue

        if capture:
            lines.append(stripped)

    return "\n".join(lines).strip()
