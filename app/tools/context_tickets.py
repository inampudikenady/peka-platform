"""
context_tickets.py

Build ticket context from Zammad.
"""

from app.tools.zammad_client import get_tickets_for_ci


def build_ticket_context(ci_name: str):

    tickets = get_tickets_for_ci(ci_name)

    if not tickets:
        return f"""
===== Zammad Ticket Context =====

TICKET_COUNT_30D: 0
HAS_TICKETS: false
"""

    context = f"""
===== Zammad Ticket Context =====

TICKET_COUNT_30D: {len(tickets)}
HAS_TICKETS: true
"""

    for ticket in tickets:
        context += f"""

TICKET_NUMBER: {ticket.get("number")}
TICKET_TITLE: {ticket.get("title")}
TICKET_LINK: {ticket.get("link")}
STATE_ID: {ticket.get("state_id")}
PRIORITY_ID: {ticket.get("priority_id")}
CREATED_AT: {ticket.get("created_at")}

TICKET_MARKDOWN: - [{ticket.get("number")}]({ticket.get("link")}) - {ticket.get("title")}
"""

    return context
