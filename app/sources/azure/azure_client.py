from __future__ import annotations

import json
import re
import subprocess
from typing import Any


_STATUS_MESSAGES = {
    401: "Not authenticated",
    403: "Permission denied",
    404: "Resource not found",
}

_STATUS_ACTIONS = {
    401: "Run az login and confirm the Azure CLI session is active.",
    403: "Confirm the signed-in account has permission for this subscription or resource.",
    404: "Confirm the subscription, resource group, and resource name exist.",
}

_AZURE_ERROR_CODE_STATUS = {
    "authenticationfailed": 401,
    "expiredauthenticationtoken": 401,
    "invalidauthenticationtoken": 401,
    "authorizationfailed": 403,
    "forbidden": 403,
    "resourcenotfound": 404,
    "notfound": 404,
    "toomanyrequests": 429,
    "ratelimitexceeded": 429,
    "throttled": 429,
    "throttling": 429,
    "badgateway": 502,
    "internalservererror": 500,
    "serviceunavailable": 503,
    "gatewaytimeout": 504,
}


def _extract_retry_after(output: str) -> str:
    patterns = [
        r"\bretry-after\b\D{0,20}(\d+)",
        r"\bretry after\D{0,20}(\d+)\s*(?:seconds?|secs?|s)?\b",
        r"\btry again in\D{0,20}(\d+)\s*(?:seconds?|secs?|s)?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    return ""


def _extract_status_from_error_code(output: str) -> int | None:
    for error_code, status_code in _AZURE_ERROR_CODE_STATUS.items():
        if error_code in output.lower().replace("_", "").replace(" ", ""):
            return status_code

    return None


def _extract_status_code(output: str) -> int | None:
    status_patterns = [
        r"\bstatus\s+code\D{0,20}([1-5]\d\d)\b",
        r"\bhttp\s+status\D{0,20}([1-5]\d\d)\b",
        r"\bresponse\s+status\D{0,20}([1-5]\d\d)\b",
        r"\bstatus\D{0,10}([1-5]\d\d)\b",
    ]

    for pattern in status_patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    return _extract_status_from_error_code(output)


def _azure_error_message(status_code: int | None, retry_after: str) -> str | None:
    if status_code == 429:
        if retry_after:
            return f"Rate limited (retry after {retry_after} seconds)"
        return "Rate limited"

    if status_code is not None and 500 <= status_code <= 599:
        return "Azure service unavailable"

    return _STATUS_MESSAGES.get(status_code)


def _azure_error_action(status_code: int | None) -> str:
    if status_code == 429:
        return "Retry the Azure request after the rate limit window has passed."

    if status_code is not None and 500 <= status_code <= 599:
        return "Retry later. If the issue persists, check Azure service health."

    return _STATUS_ACTIONS.get(
        status_code,
        "Review the Azure CLI error and confirm subscription access.",
    )


def _build_error_result(stdout: str, stderr: str) -> dict:
    raw_message = stderr.strip() or stdout.strip()
    status_code = _extract_status_code(raw_message)
    retry_after = _extract_retry_after(raw_message)
    friendly_message = _azure_error_message(status_code, retry_after)

    if friendly_message:
        message = friendly_message
        if raw_message:
            message = f"{friendly_message}. Details: {raw_message}"
    else:
        message = raw_message

    return {
        "error": True,
        "message": message,
        "status_code": status_code,
        "retry_after_seconds": retry_after,
        "action_required": _azure_error_action(status_code),
    }


def run_az(command: list[str]) -> Any:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return _build_error_result(result.stdout, result.stderr)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "error": True,
            "message": result.stdout.strip(),
        }


def get_account() -> dict:
    return run_az([
        "az", "account", "show",
        "--query", "{name:name,id:id,tenantId:tenantId,user:user.name}",
        "-o", "json",
    ])


def get_resource_groups() -> list[dict] | dict:
    return run_az([
        "az", "group", "list",
        "--query", "[].{name:name,location:location,status:properties.provisioningState}",
        "-o", "json",
    ])


def get_resources() -> list[dict] | dict:
    return run_az([
        "az", "resource", "list",
        "--query", "[].{name:name,type:type,resourceGroup:resourceGroup,location:location}",
        "-o", "json",
    ])


def get_vms() -> list[dict] | dict:
    return run_az([
        "az", "vm", "list",
        "--query", "[].{id:id,name:name,resourceGroup:resourceGroup,location:location,size:hardwareProfile.vmSize,osType:storageProfile.osDisk.osType}",
        "-o", "json",
    ])


def get_vm_details(vm_id: str) -> dict:
    return run_az([
        "az", "vm", "show",
        "--ids", vm_id,
        "--show-details",
        "--query", "{name:name,resourceGroup:resourceGroup,location:location,size:hardwareProfile.vmSize,powerState:powerState,privateIps:privateIps,publicIps:publicIps,osType:storageProfile.osDisk.osType}",
        "-o", "json",
    ])


def get_month_to_date_cost() -> dict:
    account = get_account()

    if isinstance(account, dict) and account.get("error"):
        return account

    subscription_id = account.get("id")

    body = {
        "type": "ActualCost",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum",
                }
            },
        },
    }

    return run_az([
        "az", "rest",
        "--method", "post",
        "--url", f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2024-08-01",
        "--body", json.dumps(body),
    ])


def get_cost_by_resource_group() -> dict:
    account = get_account()

    if isinstance(account, dict) and account.get("error"):
        return account

    subscription_id = account.get("id")

    body = {
        "type": "ActualCost",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum",
                }
            },
            "grouping": [
                {
                    "type": "Dimension",
                    "name": "ResourceGroup",
                }
            ],
        },
    }

    return run_az([
        "az", "rest",
        "--method", "post",
        "--url", f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2024-08-01",
        "--body", json.dumps(body),
    ])


def get_cost_by_service() -> dict:
    account = get_account()

    if isinstance(account, dict) and account.get("error"):
        return account

    subscription_id = account.get("id")

    body = {
        "type": "ActualCost",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum",
                }
            },
            "grouping": [
                {
                    "type": "Dimension",
                    "name": "ServiceName",
                }
            ],
        },
    }

    return run_az([
        "az", "rest",
        "--method", "post",
        "--url", f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2024-08-01",
        "--body", json.dumps(body),
    ])
