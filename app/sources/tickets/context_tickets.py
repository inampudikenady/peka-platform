"""
context_tickets.py

Build ticket context from the selected ticket provider.

Supported:
    - servicenow
    - zammad
"""

import os

from app.sources.servicenow.servicenow_client import get_ci_summary
from app.sources.tickets.zammad_client import get_tickets_for_ci
from dotenv import load_dotenv

load_dotenv()

def build_ticket_context(identifier: str):
    provider = os.getenv("TICKET_PROVIDER", "servicenow").lower()

    if provider == "zammad":
        return build_zammad_ticket_context(identifier)

    if provider == "servicenow":
        return build_servicenow_ticket_context(identifier)

    return f"""
===== Ticket Context =====

TICKET_PROVIDER: {provider}
TICKET_COUNT_30D: 0
HAS_TICKETS: false
"""


def build_servicenow_ticket_context(identifier: str):
    data = get_ci_summary(identifier)
    incidents = data.get("incidents_last_30_days", []) or []

    return _build_ticket_context_from_items(
        provider="servicenow",
        items=[
            {
                "number": inc.get("number"),
                "title": inc.get("short_description"),
                "link": inc.get("link"),
                "created_at": inc.get("sys_created_on"),
                "updated_at": inc.get("sys_updated_on"),
                "state": inc.get("state"),
                "priority": inc.get("priority"),
            }
            for inc in incidents
        ],
    )


def build_zammad_ticket_context(identifier: str):
    tickets = get_tickets_for_ci(identifier)

    return _build_ticket_context_from_items(
        provider="zammad",
        items=[
            {
                "number": ticket.get("number"),
                "title": ticket.get("title"),
                "link": ticket.get("link"),
                "created_at": ticket.get("created_at"),
                "updated_at": ticket.get("updated_at"),
                "state": ticket.get("state_id"),
                "priority": ticket.get("priority_id"),
            }
            for ticket in tickets
        ],
    )


def _build_ticket_context_from_items(provider: str, items: list):
    count = len(items)
    has_tickets = count > 0

    context = f"""
===== Ticket Context =====

TICKET_PROVIDER: {provider}
TICKET_COUNT_30D: {count}
HAS_TICKETS: {str(has_tickets).lower()}
"""

    if not has_tickets:
        context += "\nNO_TICKETS_FOUND: true\n"
        return context

    context += "\n===== Related Tickets Last 30 Days =====\n"

    for item in items:
        context += f"""
TICKET_NUMBER: {item.get("number")}
TICKET_TITLE: {item.get("title")}
TICKET_LINK: {item.get("link")}
TICKET_CREATED_AT: {item.get("created_at")}
TICKET_UPDATED_AT: {item.get("updated_at")}
TICKET_STATE: {item.get("state")}
TICKET_PRIORITY: {item.get("priority")}
TICKET_MARKDOWN: - [{item.get("number")}]({item.get("link")}) - {item.get("title")}
"""

    return context