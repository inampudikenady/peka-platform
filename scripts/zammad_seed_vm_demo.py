#!/usr/bin/env python3

import os
import sys
import time
import requests


ZAMMAD_URL = os.getenv("ZAMMAD_URL", "http://localhost:8080").rstrip("/")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")

if not ZAMMAD_TOKEN:
    print("ERROR: ZAMMAD_TOKEN not set")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Token token={ZAMMAD_TOKEN}",
    "Content-Type": "application/json",
}


def api(method, path, payload=None):
    response = requests.request(
        method,
        f"{ZAMMAD_URL}{path}",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        print("API ERROR", method, path, response.status_code)
        print(response.text)
        response.raise_for_status()

    return response.json() if response.text else None


def search(path, query):
    return api("GET", f"{path}?query={query}") or []


def ensure_user(firstname, lastname, email, login):
    for user in search("/api/v1/users/search", email):
        if user.get("email") == email:
            print(f"User exists: {email}")
            return user

    user = api("POST", "/api/v1/users", {
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "login": login,
        "active": True,
    })

    print(f"Created user: {email}")
    return user


def ensure_org(name):
    for org in search("/api/v1/organizations/search", name):
        if org.get("name") == name:
            print(f"Organization exists: {name}")
            return org

    org = api("POST", "/api/v1/organizations", {"name": name})
    print(f"Created organization: {name}")
    return org


def find_ticket_by_title(title):
    for ticket in search("/api/v1/tickets/search", title):
        if ticket.get("title") == title:
            return ticket
    return None


def create_ticket(title, customer_id, body):
    existing = find_ticket_by_title(title)

    if existing:
        print(f"Ticket exists: {existing.get('number')} - {title}")
        return existing

    ticket = api("POST", "/api/v1/tickets", {
        "title": title,
        "group": "Users",
        "customer_id": customer_id,
        "article": {
            "subject": title,
            "body": body,
            "type": "note",
            "internal": False,
        },
    })

    print(f"Created ticket: {ticket.get('number')} - {title}")
    return ticket


def main():
    print("===================================")
    print("PEKA VM Demo Zammad Seed")
    print("===================================")
    print("URL:", ZAMMAD_URL)

    ensure_org("PEKA Lab")

    users = {
        "kenady": ensure_user("Kenady", "Inampudi", "kenady@example.com", "kenady"),
        "ravi": ensure_user("Ravi", "Reddy", "ravi@example.com", "ravi"),
        "naveej": ensure_user("Naveej", "KA", "naveej@example.com", "naveej"),
        "anirudh": ensure_user("Anirudh", "Kumar", "anirudh@example.com", "anirudh"),
    }

    tickets = [
        {
            "title": "High CPU detected on peka-linux-001",
            "customer_id": users["kenady"]["id"],
            "body": (
                "CI: peka-linux-001\n"
                "IP: 172.16.165.11\n"
                "Application: Nitro\n"
                "Monitoring reported elevated CPU on peka-linux-001. "
                "Review top CPU processes from process_exporter and validate Nitro workload."
            ),
        },
        {
            "title": "NTP time jump observed on peka-linux-001",
            "customer_id": users["naveej"]["id"],
            "body": (
                "CI: peka-linux-001\n"
                "IP: 172.16.165.11\n"
                "Application: Nitro\n"
                "Chrony reported a forward time jump on peka-linux-001. "
                "Validate VMware guest time sync and NTP configuration."
            ),
        },
        {
            "title": "Ventana service warning on peka-linux-002",
            "customer_id": users["ravi"]["id"],
            "body": (
                "CI: peka-linux-002\n"
                "IP: 172.16.165.12\n"
                "Application: Ventana\n"
                "Application logs show intermittent warning events on peka-linux-002. "
                "Validate service health and recent syslog entries."
            ),
        },
        {
            "title": "Filesystem usage review for peka-linux-002",
            "customer_id": users["anirudh"]["id"],
            "body": (
                "CI: peka-linux-002\n"
                "IP: 172.16.165.12\n"
                "Application: Ventana\n"
                "Filesystem usage is trending upward on peka-linux-002. "
                "Review root filesystem capacity and cleanup options."
            ),
        },
        {
            "title": "Windows application error on peka-win-001",
            "customer_id": users["kenady"]["id"],
            "body": (
                "CI: peka-win-001\n"
                "IP: 172.16.165.21\n"
                "Application: PEKA-Web\n"
                "Windows Application Event Log reported PEKA-Demo Event ID 5001 "
                "on peka-win-001. Validate service status and recent application events."
            ),
        },
        {
            "title": "Windows exporter validation for peka-win-001",
            "customer_id": users["ravi"]["id"],
            "body": (
                "CI: peka-win-001\n"
                "IP: 172.16.165.21\n"
                "Application: PEKA-Web\n"
                "Validate windows_exporter metrics on peka-win-001 and confirm "
                "Prometheus target health."
            ),
        },
    ]

    for ticket in tickets:
        create_ticket(ticket["title"], ticket["customer_id"], ticket["body"])
        time.sleep(1)

    print("Seed complete.")


if __name__ == "__main__":
    main()
