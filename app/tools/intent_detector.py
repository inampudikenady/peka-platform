"""
intent_detector.py

Purpose:
    Analyze a user question and determine:
    - Operational intent (cmdb, health, logs, history, docs)
    - CI hostname or IP address references

Used by:
    context_builder.py

Examples:
    "Show CI overview for peka-dev-ai-001"
        -> intent=cmdb

    "Why is peka-dev-ai-001 slow?"
        -> intent=health

    "Show logs for peka-dev-ai-001"
        -> intent=logs
"""

import re


def extract_identifier(question: str):
    ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", question)

    if ip_match:
        return ip_match.group(0)

    ci_match = re.search(
        r"\bpeka-dev-[a-z0-9-]+-\d{3}\b",
        question.lower()
    )

    if ci_match:
        return ci_match.group(0)

    return None


def detect_intent(question: str):
    q = question.lower()

    doc_words = [
        "patch", "upgrade", "install", "installation",
        "configure", "configuration", "procedure", "steps",
        "document", "documentation", "how do i", "how to",
        "runbook", "guide", "rhel", "ubuntu",
        "windows patch", "change plan",
    ]

    health_words = [
        "health", "status", "slow", "cpu", "memory", "mem",
        "disk", "filesystem", "process", "utilization",
        "usage", "load", "performance", "operational issue",
        "issue", "problem",
    ]

    history_words = [
        "incident", "ticket", "history", "past",
        "last 30", "recent issue",
    ]

    log_words = [
        "log", "logs", "error", "errors", "failed",
        "failure", "event", "events", "auth",
        "authentication", "sudo", "security", "last 24",
    ]

    if any(x in q for x in doc_words):
        return "docs"

    if any(x in q for x in health_words):
        return "health"

    if any(x in q for x in history_words):
        return "history"

    if any(x in q for x in log_words):
        return "logs"

    return "cmdb"
