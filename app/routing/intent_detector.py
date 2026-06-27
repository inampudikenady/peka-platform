"""
intent_detector.py

Purpose:
    Analyze a user question and determine:
    - Operational intent: cmdb, health, logs, history, docs
    - CI hostname, IP address references

Used by:
    context_builder.py
"""

import re


def extract_identifier(question: str):
    q = question.lower()

    ip_match = re.search(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        q,
    )

    if ip_match:
        return ip_match.group(0)

    hostname_patterns = [
        # hostnames ending with -001, -002, etc.
        r"\b[a-z0-9]+(?:-[a-z0-9]+)+-\d{3}\b",

        # hostnames with multiple dash sections
        r"\b[a-z][a-z0-9-]{2,}\b",
    ]

    ignore_words = {
        "show",
        "error",
        "errors",
        "logs",
        "log",
        "why",
        "slow",
        "health",
        "status",
        "ticket",
        "tickets",
        "incident",
        "incidents",
        "history",
        "for",
        "from",
        "last",
        "days",
        "hours",
        "what",
        "is",
        "the",
        "server",
        "host",
        "node",
        
        "performance",
    }

    for pattern in hostname_patterns:
        matches = re.findall(pattern, q)

        for match in matches:
            if match not in ignore_words:
                return match

    return None


def detect_intent(question: str):
    q = question.lower()

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
        "last 24",
        "last 2",
    ]

    history_words = [
        "incident",
        "incidents",
        "ticket",
        "tickets",
        "history",
        "past",
        "last 30",
        "recent issue",
    ]

    health_words = [
        "health",
        "status",
        "slow",
        "slowness",
        "cpu",
        "memory",
        "mem",
        "disk",
        "filesystem",
        "process",
        "utilization",
        "usage",
        "load",
        "performance",
        "operational issue",
        "issue",
        "problem",
        "down",
        "unresponsive",
    ]

    doc_words = [
        "patch",
        "upgrade",
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
        "rhel",
        "ubuntu",
        "windows patch",
        "change plan",
    ]

    # Logs first because "error logs" also contains "error",
    # and should be routed to logs, not health.
    if any(word in q for word in log_words):
        return "logs"

    if any(word in q for word in history_words):
        return "history"

    if any(word in q for word in health_words):
        return "health"

    if any(word in q for word in doc_words):
        return "docs"

    return "cmdb"