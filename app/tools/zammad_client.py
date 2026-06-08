import os
import requests


ZAMMAD_URL = os.getenv("ZAMMAD_URL", "http://localhost:8080").rstrip("/")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")


def _headers():
    if not ZAMMAD_TOKEN:
        raise RuntimeError("ZAMMAD_TOKEN is not set")

    return {
        "Authorization": f"Token token={ZAMMAD_TOKEN}",
        "Content-Type": "application/json",
    }


def zammad_get(path: str, params: dict | None = None):
    response = requests.get(
        f"{ZAMMAD_URL}{path}",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def search_tickets(query: str):
    return zammad_get(
        "/api/v1/tickets/search",
        params={"query": query},
    )


def get_tickets_for_ci(ci_name: str):
    tickets = search_tickets(ci_name)

    results = []

    for ticket in tickets:
        results.append(
            {
                "id": ticket.get("id"),
                "number": ticket.get("number"),
                "title": ticket.get("title"),
                "state_id": ticket.get("state_id"),
                "priority_id": ticket.get("priority_id"),
                "created_at": ticket.get("created_at"),
                "updated_at": ticket.get("updated_at"),
                "link": f"{ZAMMAD_URL}/#ticket/zoom/{ticket.get('id')}",
            }
        )

    return results
import os
import requests


ZAMMAD_URL = os.getenv("ZAMMAD_URL", "http://localhost:8080").rstrip("/")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")


def _headers():
    if not ZAMMAD_TOKEN:
        raise RuntimeError("ZAMMAD_TOKEN is not set")

    return {
        "Authorization": f"Token token={ZAMMAD_TOKEN}",
        "Content-Type": "application/json",
    }


def zammad_get(path: str, params: dict | None = None):
    response = requests.get(
        f"{ZAMMAD_URL}{path}",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def search_tickets(query: str):
    return zammad_get(
        "/api/v1/tickets/search",
        params={"query": query},
    )


def get_tickets_for_ci(ci_name: str):
    tickets = search_tickets(ci_name)

    results = []

    for ticket in tickets:
        results.append(
            {
                "id": ticket.get("id"),
                "number": ticket.get("number"),
                "title": ticket.get("title"),
                "state_id": ticket.get("state_id"),
                "priority_id": ticket.get("priority_id"),
                "created_at": ticket.get("created_at"),
                "updated_at": ticket.get("updated_at"),
                "link": f"{ZAMMAD_URL}/#ticket/zoom/{ticket.get('id')}",
            }
        )

    return results
