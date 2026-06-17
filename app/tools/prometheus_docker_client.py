"""
prometheus_docker_client.py

Purpose:
    Read local Docker container metrics from Prometheus/cAdvisor.

Used for Tuple/local demos where workloads are Docker containers
instead of real VMs with node_exporter.
"""

import os
import subprocess
import requests


PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://localhost:9090",
).rstrip("/")


def promql(query: str):
    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _first_value(result):
    try:
        return float(result["data"]["result"][0]["value"][1])
    except Exception:
        return None


def _run_docker_command(args):
    result = subprocess.run(
        ["docker"] + args,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def get_container_id(container_name: str):
    output = _run_docker_command(
        [
            "ps",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.ID}}",
        ]
    )

    lines = output.splitlines()

    if not lines:
        return None

    return lines[0]


def get_container_status_text(container_name: str):
    output = _run_docker_command(
        [
            "ps",
            "-a",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Status}}",
        ]
    )

    lines = output.splitlines()

    if not lines:
        return "not_found"

    return lines[0]


def get_container_state(container_name: str):
    output = _run_docker_command(
        [
            "inspect",
            "-f",
            "{{.State.Status}}",
            container_name,
        ]
    )

    if not output:
        return "unknown"

    return output.splitlines()[0]


def get_container_running(container_name: str):
    output = _run_docker_command(
        [
            "inspect",
            "-f",
            "{{.State.Running}}",
            container_name,
        ]
    )

    return output.lower().strip() == "true"


def get_normalized_status(container_name: str):
    state = get_container_state(container_name)
    running = get_container_running(container_name)

    if running and state == "running":
        return "up"

    if state in ["exited", "dead"]:
        return "down"

    if state in ["paused", "restarting"]:
        return state

    return state or "unknown"


def bytes_to_mb(value):
    if value is None:
        return None

    return round(value / 1024 / 1024, 2)


def get_container_summary(container_name: str):
    container_id = get_container_id(container_name)

    if not container_id:
        return {
            "found": False,
            "name": container_name,
            "status": "not_found",
            "state": "not_found",
            "running": False,
            "status_text": "not_found",
            "summary": "Container not found",
        }

    id_regex = f"/docker/{container_id}.*"

    cpu_query = (
        'rate(container_cpu_usage_seconds_total'
        f'{{id=~"{id_regex}",cpu="total"}}[1m]) * 100'
    )

    memory_query = (
        "container_memory_usage_bytes"
        f'{{id=~"{id_regex}"}}'
    )

    memory_working_set_query = (
        "container_memory_working_set_bytes"
        f'{{id=~"{id_regex}"}}'
    )

    last_seen_query = (
        "container_last_seen"
        f'{{id=~"{id_regex}"}}'
    )

    cpu_percent = _first_value(promql(cpu_query))
    memory_bytes = _first_value(promql(memory_query))
    memory_working_set_bytes = _first_value(
        promql(memory_working_set_query)
    )
    last_seen = _first_value(promql(last_seen_query))

    return {
        "found": True,
        "name": container_name,
        "container_id": container_id,
        "status": get_normalized_status(container_name),
        "state": get_container_state(container_name),
        "running": get_container_running(container_name),
        "status_text": get_container_status_text(container_name),
        "cpu_percent": round(cpu_percent or 0, 4),
        "memory_mb": bytes_to_mb(memory_bytes),
        "memory_working_set_mb": bytes_to_mb(
            memory_working_set_bytes
        ),
        "last_seen": last_seen,
    }