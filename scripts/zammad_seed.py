#!/usr/bin/env python3

import os
import sys
import time
import requests

ZAMMAD_URL = os.getenv(
    "ZAMMAD_URL",
    "http://localhost:8080"
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
        print("\nAPI ERROR")
        print("METHOD:", method)
        print("URL:", url)
        print("STATUS:", response.status_code)
        print(response.text)
        response.raise_for_status()

    if not response.text:
        return None

    return response.json()


def find_user_by_email(email):
    try:
        results = api(
            "GET",
            f"/api/v1/users/search?query={email}"
        )

        if isinstance(results, list):
            for user in results:
                if user.get("email") == email:
                    return user

    except Exception:
        pass

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
    try:
        results = api(
            "GET",
            f"/api/v1/organizations/search?query={name}"
        )

        if isinstance(results, list):
            for org in results:
                if org.get("name") == name:
                    return org

    except Exception:
        pass

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
            "name": name
        }
    )

    print(f"Created organization: {name}")

    return org


def create_ticket(
    title,
    customer_id,
    body
):
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
        payload
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
            "kenady"
        ),
        (
            "Ravi",
            "Reddy",
            "ravi@example.com",
            "ravi"
        ),
        (
            "Naveej",
            "KA",
            "naveej@example.com",
            "naveej"
        ),
        (
            "Anirudh",
            "Kumar",
            "anirudh@example.com",
            "anirudh"
        ),
    ]

    created_users = {}

    for user in users:
        created = ensure_user(*user)
        created_users[user[2]] = created

    customer_id = created_users[
        "kenady@example.com"
    ]["id"]

    tickets = [
        {
            "title":
                "High CPU observed on peka-dev-ai-001",
            "body":
                "Monitoring reported high CPU on "
                "peka-dev-ai-001. "
                "Validate top CPU processes."
        },
        {
            "title":
                "PEKA portal response time is slow",
            "body":
                "Users reported slow response "
                "from PEKA portal."
        },
        {
            "title":
                "Loki ingestion delay",
            "body":
                "Promtail and Loki require "
                "validation."
        },
        {
            "title":
                "Node exporter unreachable",
            "body":
                "Prometheus target down on "
                "peka-dev-linux-sea-001."
        },
        {
            "title":
                "Filesystem usage warning",
            "body":
                "Disk usage threshold exceeded."
        },
    ]

    for ticket in tickets:
        create_ticket(
            title=ticket["title"],
            customer_id=customer_id,
            body=ticket["body"],
        )

        time.sleep(1)

    print()
    print("Seed complete.")
    print()


if __name__ == "__main__":
    main()
