"""
source_router.py

Purpose:
    Decide which PEKA sources should be used for a user question.

Flow:
    Question -> intent -> source flags

Sources:
    cmdb        Local CMDB / ServiceNow CI details
    metrics     Prometheus / Docker metrics
    logs        Loki logs
    tickets     Zammad / ServiceNow incidents
    docs        RAG documentation
    azure       Azure cost and inventory APIs
"""

from app.routing.intent_detector import extract_identifier


def route_sources(question: str) -> dict:
    q = question.lower()
    identifier = extract_identifier(question)

    route = {
        "intent": "inventory",
        "identifier": identifier,
        "sources": {
            "cmdb": False,
            "metrics": False,
            "logs": False,
            "tickets": False,
            "docs": False,
            "azure": False,
        },
    }

    azure_words = [
        "azure",
        "bill",
        "billing",
        "cost",
        "spend",
        "subscription",
        "resource group",
        "resources in azure",
        "azure resources",
        "virtual machine",
        "vm",
        "vms",
    ]

    health_words = [
        "slow",
        "slowness",
        "health",
        "status",
        "cpu",
        "memory",
        "mem",
        "disk",
        "filesystem",
        "load",
        "performance",
        "down",
        "unresponsive",
        "issue",
        "problem",
    ]

    log_words = [
        "log",
        "logs",
        "error",
        "errors",
        "failed",
        "failure",
        "event",
        "events",
        "auth",
        "authentication",
        "sudo",
        "security",
    ]

    ticket_words = [
        "incident",
        "incidents",
        "ticket",
        "tickets",
        "history",
        "recent issue",
        "recent issues",
        "past issues",
    ]

    doc_words = [
        "install",
        "installation",
        "configure",
        "configuration",
        "procedure",
        "steps",
        "document",
        "documentation",
        "how do i",
        "how to",
        "runbook",
        "guide",
    ]

    if any(word in q for word in azure_words):
        route["intent"] = "cloud"
        route["identifier"] = None
        route["sources"]["azure"] = True
        return route

    if any(word in q for word in doc_words):
        route["intent"] = "docs"
        route["identifier"] = None
        route["sources"]["docs"] = True
        return route

    if any(word in q for word in health_words):
        route["intent"] = "operational_health"
        route["sources"]["cmdb"] = True
        route["sources"]["metrics"] = True
        route["sources"]["logs"] = True
        route["sources"]["tickets"] = True
        return route

    if any(word in q for word in log_words):
        route["intent"] = "logs"
        route["sources"]["cmdb"] = True
        route["sources"]["logs"] = True
        return route

    if any(word in q for word in ticket_words):
        route["intent"] = "ticket_history"
        route["sources"]["cmdb"] = True
        route["sources"]["tickets"] = True
        return route

    field_intents = {
        "inventory_field_owner": [
            "who owns",
            "owner of",
            "owned by",
            "who is responsible",
        ],
        "inventory_field_ip_address": [
            "ip address",
            "what is the ip",
            "which ip",
        ],
        "inventory_field_application": [
            "what application",
            "which application",
            "application runs",
            "app runs",
        ],
        "inventory_field_criticality": [
            "criticality",
            "how critical",
            "priority",
        ],
        "inventory_field_environment": [
            "environment",
            "which env",
            "what env",
        ],
        "inventory_field_os": [
            "what os",
            "which os",
            "operating system",
        ],
        "inventory_field_patch_group": [
            "patch group",
            "patching group",
        ],
    }

    for field_intent, words in field_intents.items():
        if any(word in q for word in words):
            route["intent"] = field_intent
            route["sources"]["cmdb"] = True
            return route

    route["intent"] = "inventory"
    route["sources"]["cmdb"] = True
    return route
