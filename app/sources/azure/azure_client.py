import json
import subprocess
from typing import Any


def run_az(command: list[str]) -> Any:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return {
            "error": True,
            "message": result.stderr.strip() or result.stdout.strip(),
        }

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
