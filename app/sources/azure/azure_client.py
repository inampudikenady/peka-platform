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
        "az", "vm", "list", "-d",
        "--query", "[].{name:name,resourceGroup:resourceGroup,location:location,powerState:powerState,privateIps:privateIps,publicIps:publicIps,size:hardwareProfile.vmSize}",
        "-o", "json",
    ])
