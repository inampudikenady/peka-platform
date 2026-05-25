import requests
from requests.auth import HTTPBasicAuth

INSTANCE = "https://dev274568.service-now.com"
USERNAME = "admin"
PASSWORD = "q4k8xwRTN=@Z"

auth = HTTPBasicAuth(USERNAME, PASSWORD)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def find_ci_sys_id(ci_name):
    url = f"{INSTANCE}/api/now/table/cmdb_ci_server"
    params = {
        "sysparm_query": f"name={ci_name}",
        "sysparm_fields": "sys_id,name",
        "sysparm_limit": "1"
    }
    r = requests.get(url, auth=auth, headers=headers, params=params)
    r.raise_for_status()
    result = r.json().get("result", [])
    if not result:
        raise Exception(f"CI not found: {ci_name}")
    return result[0]["sys_id"]

incidents = [
    {
        "ci": "peka-dev-ai-001",
        "short_description": "PEKA portal response time is slow",
        "description": "Users reported slow response from PEKA OpenWebUI. Initial check required on AI host CPU, memory, and container health.",
        "urgency": "2",
        "impact": "2"
    },
    {
        "ci": "peka-dev-linux-sea-001",
        "short_description": "High CPU observed on Linux application server",
        "description": "Prometheus alert indicates sustained CPU utilization above threshold on Linux workload server.",
        "urgency": "2",
        "impact": "3"
    },
    {
        "ci": "peka-dev-win-sea-001",
        "short_description": "Windows server unreachable from monitoring",
        "description": "Monitoring system cannot reach Windows server over expected management/agent path. Validate network and Windows service status.",
        "urgency": "3",
        "impact": "3"
    }
]

for inc in incidents:
    ci_sys_id = find_ci_sys_id(inc["ci"])

    payload = {
        "short_description": inc["short_description"],
        "description": inc["description"],
        "cmdb_ci": ci_sys_id,
        "caller_id": "admin",
        "category": "inquiry",
        "subcategory": "internal application",
        "urgency": inc["urgency"],
        "impact": inc["impact"],
        "contact_type": "self-service"
    }

    r = requests.post(
        f"{INSTANCE}/api/now/table/incident",
        auth=auth,
        headers=headers,
        json=payload
    )

    print(f"{inc['ci']} -> {r.status_code}")
    print(r.text)
