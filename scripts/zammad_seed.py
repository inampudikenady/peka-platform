#!/usr/bin/env python3

import os
import sys
import time
import requests


ZAMMAD_URL = os.getenv(
    "ZAMMAD_URL",
    "http://localhost:8080",
).rstrip("/")

ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")


if not ZAMMAD_TOKEN:
    print("ERROR: ZAMMAD_TOKEN not set")
    print('export ZAMMAD_TOKEN="your_token_here"')
    sys.exit(1)


HEADERS = {
    "Authorization": f"Token token={ZAMMAD_TOKEN}",
    "Content-Type": "application/json",
}


def api(method, path, payload=None):
    url = f"{ZAMMAD_URL}{path}"

    response = requests.request(
        method,
        url,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        print()
        print("API ERROR")
        print("METHOD:", method)
        print("URL:", url)
        print("STATUS:", response.status_code)
        print(response.text)
        response.raise_for_status()

    if not response.text:
        return None

    return response.json()


def find_user_by_email(email):
    results = api(
        "GET",
        f"/api/v1/users/search?query={email}",
    )

    if isinstance(results, list):
        for user in results:
            if user.get("email") == email:
                return user

    return None


def ensure_user(firstname, lastname, email, login):
    existing = find_user_by_email(email)

    if existing:
        print(f"User exists: {email}")
        return existing

    payload = {
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "login": login,
        "active": True,
    }

    user = api(
        "POST",
        "/api/v1/users",
        payload,
    )

    print(f"Created user: {email}")

    return user


def find_org(name):
    results = api(
        "GET",
        f"/api/v1/organizations/search?query={name}",
    )

    if isinstance(results, list):
        for org in results:
            if org.get("name") == name:
                return org

    return None


def ensure_org(name):
    existing = find_org(name)

    if existing:
        print(f"Organization exists: {name}")
        return existing

    org = api(
        "POST",
        "/api/v1/organizations",
        {
            "name": name,
        },
    )

    print(f"Created organization: {name}")

    return org


def find_ticket_by_title(title):
    results = api(
        "GET",
        f"/api/v1/tickets/search?query={title}",
    )

    if isinstance(results, list):
        for ticket in results:
            if ticket.get("title") == title:
                return ticket

    return None


def create_ticket(title, customer_id, body):
    existing = find_ticket_by_title(title)

    if existing:
        print(
            f"Ticket exists: "
            f"{existing.get('number')} - {title}"
        )
        return existing

    payload = {
        "title": title,
        "group": "Users",
        "customer_id": customer_id,
        "article": {
            "subject": title,
            "body": body,
            "type": "note",
            "internal": False,
        },
    }

    ticket = api(
        "POST",
        "/api/v1/tickets",
        payload,
    )

    print(
        f"Created ticket: "
        f"{ticket.get('number')} - {title}"
    )

    return ticket


def main():
    print()
    print("===================================")
    print("Zammad Seed Utility")
    print("===================================")
    print("URL:", ZAMMAD_URL)
    print()

    ensure_org("Tuple Labs")

    users = [
        (
            "Kenady",
            "Inampudi",
            "kenady@example.com",
            "kenady",
        ),
        (
            "Ravi",
            "Reddy",
            "ravi@example.com",
            "ravi",
        ),
        (
            "Naveej",
            "KA",
            "naveej@example.com",
            "naveej",
        ),
        (
            "Anirudh",
            "Kumar",
            "anirudh@example.com",
            "anirudh",
        ),
    ]

    created_users = {}

    for user in users:
        created = ensure_user(*user)
        created_users[user[2]] = created

    kenady_id = created_users["kenady@example.com"]["id"]
    ravi_id = created_users["ravi@example.com"]["id"]
    naveej_id = created_users["naveej@example.com"]["id"]
    anirudh_id = created_users["anirudh@example.com"]["id"]

    tickets = [
        {
            "title": "High CPU observed on peka-dev-ai-001",
            "customer_id": kenady_id,
            "body": (
                "Monitoring reported high CPU on peka-dev-ai-001. "
                "Validate top CPU processes."
            ),
        },
        {
            "title": "PEKA portal response time is slow",
            "customer_id": ravi_id,
            "body": (
                "Users reported slow response from PEKA portal. "
                "Validate web/API response time."
            ),
        },
        {
            "title": "Loki ingestion delay on peka-dev-ai-001",
            "customer_id": naveej_id,
            "body": (
                "Promtail and Loki require validation for "
                "peka-dev-ai-001."
            ),
        },
        {
            "title": "Node exporter unreachable on peka-dev-ai-001",
            "customer_id": kenady_id,
            "body": (
                "Prometheus target down for peka-dev-ai-001. "
                "Validate node exporter and network reachability."
            ),
        },
        {
            "title": "Filesystem usage warning on peka-dev-ai-001",
            "customer_id": ravi_id,
            "body": (
                "Disk usage threshold exceeded on peka-dev-ai-001. "
                "Validate filesystem usage."
            ),
        },
        {
            "title": "Repeated login failures on linux-demo-002",
            "customer_id": anirudh_id,
            "body": (
                "Multiple failed login attempts detected from "
                "linux-demo-002 test workload. Investigation required."
            ),
        },
        {
            "title": "Container restart observed on linux-demo-002",
            "customer_id": ravi_id,
            "body": (
                "Container linux-demo-002 restarted unexpectedly "
                "during testing. Validate application health."
            ),
        },
        {
            "title": "Memory growth investigation on linux-demo-002",
            "customer_id": kenady_id,
            "body": (
                "Memory usage trend observed for linux-demo-002 "
                "over several hours. Investigate possible leak."
            ),
        },
        {
            "title": "Loki ingestion delay for linux-demo-002",
            "customer_id": naveej_id,
            "body": (
                "Promtail reports delayed log delivery for "
                "linux-demo-002. Validate Loki pipeline health."
            ),
        },
        {
            "title": "High CPU detected on linux-demo-002",
            "customer_id": anirudh_id,
            "body": (
                "CPU utilization exceeded expected baseline for "
                "linux-demo-002. Review workload activity."
            ),
        },
    ]

    for ticket in tickets:
        create_ticket(
            title=ticket["title"],
            customer_id=ticket["customer_id"],
            body=ticket["body"],
        )

        time.sleep(1)

    print()
    print("Seed complete.")
    print()


if __name__ == "__main__":
    main()