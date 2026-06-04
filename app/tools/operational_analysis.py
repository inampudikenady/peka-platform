from app.tools.servicenow_client import resolve_ci, get_ci_summary
from app.tools.prometheus_client import get_linux_host_summary
from app.tools.loki_client import query_logs, query_errors


def _severity(level: str, finding: str, evidence: str, recommendation: str = ""):
    return {
        "severity": level,
        "finding": finding,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def analyze_ci(identifier: str, hours: int = 24) -> dict:
    """
    Build structured operational analysis for a CI.

    Inputs can be:
    - hostname
    - IP address

    Sources:
    - ServiceNow CMDB
    - ServiceNow incidents
    - Prometheus metrics
    - Loki logs
    """

    findings = []

    snow = get_ci_summary(identifier)

    if snow.get("found"):
        ci = snow.get("cmdb_record", {})
    else:
        resolved = resolve_ci(identifier)

        if not resolved.get("found"):
            return {
                "identifier": identifier,
                "found": False,
                "summary": "CI was not found in ServiceNow CMDB.",
                "findings": [
                    _severity(
                        "warning",
                        "CI not found",
                        f"No CMDB record found for {identifier}.",
                        "Validate hostname/IP or populate CMDB.",
                    )
                ],
            }

        ci = resolved["cmdb_record"]

    ci_name = ci.get("name")
    ip_address = ci.get("ip_address")

    incident_candidates = []

    for lookup in [identifier, ci_name, ip_address]:
        if lookup and lookup not in incident_candidates:
            incident_candidates.append(lookup)

    incidents = []

    for lookup in incident_candidates:
        snow_lookup = get_ci_summary(lookup)
        incidents = snow_lookup.get("incidents_last_30_days", []) or []

        if incidents:
            break

    if incidents:
        findings.append(
            _severity(
                "info",
                "Recent incidents found",
                f"{len(incidents)} incident(s) found in ServiceNow in the last 30 days.",
                "Review linked incidents for recent operational history.",
            )
        )

    if not ip_address:
        findings.append(
            _severity(
                "warning",
                "Missing IP address in CMDB",
                f"CI {ci_name} has no IP address in ServiceNow.",
                "Update CMDB IP address so monitoring/log correlation can work.",
            )
        )

        return {
            "identifier": identifier,
            "found": True,
            "ci": ci,
            "incidents_last_30_days": incidents,
            "monitoring": None,
            "logs": None,
            "findings": findings,
            "overall_severity": "warning",
            "summary": "CI found, but monitoring correlation cannot run because IP address is missing.",
        }

    monitoring = get_linux_host_summary(ip_address)

    if monitoring.get("status") != "up":
        findings.append(
            _severity(
                "critical",
                "Node exporter down",
                monitoring.get(
                    "message",
                    "Prometheus reports this node as down.",
                ),
                "Check node_exporter service, host availability, firewall, and Prometheus target status.",
            )
        )

    else:
        cpu = monitoring.get("cpu_percent") or 0
        memory = monitoring.get("memory", {}) or {}
        mem_used = memory.get("used_percent") or 0

        if cpu >= 90:
            findings.append(
                _severity(
                    "critical",
                    "Critical CPU pressure",
                    f"CPU usage is currently {cpu}%.",
                    "Check top CPU processes and recent workload spikes.",
                )
            )
        elif cpu >= 75:
            findings.append(
                _severity(
                    "warning",
                    "Elevated CPU usage",
                    f"CPU usage is currently {cpu}%.",
                    "Review top CPU processes.",
                )
            )
        else:
            findings.append(
                _severity(
                    "info",
                    "CPU usage normal",
                    f"CPU usage is currently {cpu}%.",
                )
            )

        if mem_used >= 90:
            findings.append(
                _severity(
                    "critical",
                    "Critical memory pressure",
                    f"Memory usage is currently {mem_used}%.",
                    "Check top memory processes and possible leaks.",
                )
            )
        elif mem_used >= 75:
            findings.append(
                _severity(
                    "warning",
                    "Elevated memory usage",
                    f"Memory usage is currently {mem_used}%.",
                    "Review top memory processes.",
                )
            )
        else:
            findings.append(
                _severity(
                    "info",
                    "Memory usage normal",
                    f"Memory usage is currently {mem_used}%.",
                )
            )

        for fs in monitoring.get("filesystems", []) or []:
            mount = fs.get("mountpoint")
            used = fs.get("used_percent") or 0

            if used >= 90:
                findings.append(
                    _severity(
                        "critical",
                        "Filesystem critically full",
                        f"{mount} is {round(used, 2)}% used.",
                        "Free space or expand filesystem.",
                    )
                )
            elif used >= 80:
                findings.append(
                    _severity(
                        "warning",
                        "Filesystem usage elevated",
                        f"{mount} is {round(used, 2)}% used.",
                        "Monitor filesystem growth.",
                    )
                )

    # Do not only search for errors. Pull recent logs as well so CPU/memory
    # congestion, cron activity, service restarts, auth, kernel, and app noise
    # are still visible to the LLM/operator.
    recent_logs = query_logs(
        host=ci_name,
        search="",
        hours=hours,
        limit=20,
    )

    errors = query_errors(
        host=ci_name,
        hours=hours,
        limit=20,
    )

    recent_count = recent_logs.get("count", 0)
    error_count = errors.get("count", 0)

    if recent_count > 0:
        findings.append(
            _severity(
                "info",
                "Recent logs available",
                f"{recent_count} recent log entries were found in Loki in the last {hours} hours.",
                "Review recent logs alongside CPU, memory, filesystem, and incident data.",
            )
        )
    else:
        findings.append(
            _severity(
                "info",
                "No recent logs found",
                f"No logs were returned by Loki for {ci_name} in the last {hours} hours.",
                "Validate Promtail service, Loki labels, and host label mapping if logs are expected.",
            )
        )

    if error_count > 0:
        findings.append(
            _severity(
                "warning",
                "Recent error-like log entries found",
                f"{error_count} log entries matched error patterns in the last {hours} hours.",
                "Review error-pattern logs and recent logs together before deciding if actionable.",
            )
        )
    else:
        findings.append(
            _severity(
                "info",
                "No recent error-like logs found",
                f"No log entries matched error patterns in the last {hours} hours.",
            )
        )

    highest = "info"

    if any(f["severity"] == "critical" for f in findings):
        highest = "critical"
    elif any(f["severity"] == "warning" for f in findings):
        highest = "warning"

    if highest == "critical":
        summary = "Operational issues detected that may require action."
    elif highest == "warning":
        summary = "Some warning signals were detected. Review recommended."
    else:
        summary = "No obvious operational issues detected."

    return {
        "identifier": identifier,
        "found": True,
        "ci": ci,
        "incidents_last_30_days": incidents,
        "monitoring": monitoring,
        "logs": {
            "hours": hours,
            "recent_count": recent_count,
            "recent_logs": recent_logs.get("logs", [])[:10],
            "error_count": error_count,
            "sample_errors": errors.get("logs", [])[:10],
        },
        "overall_severity": highest,
        "summary": summary,
        "findings": findings,
    }

