"""
context_tickets.py

Build ticket context from the selected ticket provider.

Supported:
    - servicenow
    - zammad
"""

from app.config import settings

from app.sources.cmdb.inventory import resolve_inventory
from app.sources.tickets.servicenow_ticket_client import get_incidents_for_ci
from app.sources.tickets.zammad_client import get_tickets_for_ci


def build_ticket_context(identifier: str):
    provider = settings["ticket_provider"]

    if provider == "zammad":
        return build_zammad_ticket_context(identifier)

    if provider == "servicenow":
        return build_servicenow_ticket_context(identifier)

    raise RuntimeError(f"Unsupported ticket provider: {provider}")


def build_servicenow_ticket_context(identifier: str):
    incidents = get_incidents_for_ci(identifier)

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
    resolved = resolve_inventory(identifier)
    ci = resolved.get("cmdb_record", {}) or {}

    match_terms = []
    for value in [
        identifier,
        ci.get("name"),
        ci.get("monitoring_host"),
        ci.get("ip_address"),
        ci.get("application"),
    ]:
        if value and value not in match_terms:
            match_terms.append(value)

    seen = set()
    matched = []

    for term in match_terms:
        for ticket in get_tickets_for_ci(term):
            text = " ".join(
                str(x or "")
                for x in [
                    ticket.get("number"),
                    ticket.get("title"),
                    ticket.get("created_at"),
                    ticket.get("updated_at"),
                ]
            ).lower()

            # Keep only tickets that mention an exact CI/host/IP/app term.
            # This prevents broad Zammad search results from attaching unrelated tickets.
            if not any(str(t).lower() in text for t in match_terms):
                continue

            key = ticket.get("id") or ticket.get("number")
            if key in seen:
                continue

            seen.add(key)
            matched.append(ticket)

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
            for ticket in matched
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
