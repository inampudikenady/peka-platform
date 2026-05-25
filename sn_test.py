import requests
from requests.auth import HTTPBasicAuth

INSTANCE = "https://dev274568.service-now.com"
USERNAME = "admin"
PASSWORD = "q4k8xwRTN=@Z"

url = f"{INSTANCE}/api/now/table/cmdb_ci_server?sysparm_limit=5"

response = requests.get(
    url,
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    headers={"Accept": "application/json"},
)

print("Status:", response.status_code)
print(response.text)
