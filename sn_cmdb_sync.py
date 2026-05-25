import requests
from requests.auth import HTTPBasicAuth

INSTANCE = "https://dev274568.service-now.com"
USERNAME = "admin"
PASSWORD = "q4k8xwRTN=@Z"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

servers = [
    {
        "name": "peka-dev-ai-001",
        "ip_address": "10.50.1.4",
        "os": "Ubuntu 22.04",
        "location": "centralindia",
        "short_description": "PEKA Core AI Server"
    },
    {
        "name": "peka-dev-linux-sea-001",
        "ip_address": "10.70.1.5",
        "os": "Ubuntu 22.04",
        "location": "southeastasia",
        "short_description": "PEKA Linux Application Server"
    },
    {
        "name": "peka-dev-win-sea-001",
        "ip_address": "10.70.1.6",
        "os": "Windows Server 2022",
        "location": "southeastasia",
        "short_description": "PEKA Windows Application Server"
    }
]

url = f"{INSTANCE}/api/now/table/cmdb_ci_server"

for server in servers:

    payload = {
        "name": server["name"],
        "ip_address": server["ip_address"],
        "os": server["os"],
        "location": server["location"],
        "short_description": server["short_description"]
    }

    response = requests.post(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers=headers,
        json=payload
    )

    print(f"{server['name']} -> {response.status_code}")

    if response.status_code not in [200, 201]:
        print(response.text)
