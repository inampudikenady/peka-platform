import os
import requests


PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")


def promql(query: str) -> dict:
    url = f"{PROMETHEUS_URL}/api/v1/query"
    response = requests.get(url, params={"query": query}, timeout=15)
    response.raise_for_status()
    return response.json()


def _first_value(result: dict):
    data = result.get("data", {}).get("result", [])
    if not data:
        return None

    try:
        return float(data[0]["value"][1])
    except Exception:
        return None


def _first_metric(result: dict):
    data = result.get("data", {}).get("result", [])
    if not data:
        return None

    return data[0].get("metric", {})


def _vector_values(result: dict):
    values = []

    for item in result.get("data", {}).get("result", []):
        metric = item.get("metric", {})
        value = item.get("value", [None, None])[1]

        try:
            value = float(value)
        except Exception:
            continue

        values.append(
            {
                "metric": metric,
                "value": value,
            }
        )

    return values


def bytes_to_gb(value):
    if value is None:
        return None

    return round(value / 1024 / 1024 / 1024, 2)


def get_target_status(instance: str) -> dict:
    result = promql(f'up{{instance="{instance}"}}')
    value = _first_value(result)

    if value is None:
        return {
            "instance": instance,
            "status": "unknown",
            "up": False,
            "message": "Target not found in Prometheus",
        }

    return {
        "instance": instance,
        "status": "up" if value == 1 else "down",
        "up": value == 1,
        "value": value,
    }


def get_linux_os_info(instance: str):
    result = promql(f'node_os_info{{instance="{instance}"}}')
    metric = _first_metric(result)

    if not metric:
        return None

    pretty_name = metric.get("pretty_name")
    name = metric.get("name")
    version = metric.get("version")
    version_id = metric.get("version_id")

    return {
        "source": "prometheus_node_exporter",
        "pretty_name": pretty_name,
        "name": name,
        "version": version,
        "version_id": version_id,
    }


def get_windows_os_info(instance: str):
    result = promql(f'windows_os_info{{instance="{instance}"}}')
    metric = _first_metric(result)

    if not metric:
        return None

    return {
        "source": "prometheus_windows_exporter",
        "product": metric.get("product"),
        "version": metric.get("version"),
        "revision": metric.get("revision"),
        "build_number": metric.get("build_number"),
    }


def get_linux_cpu_percent(instance: str):
    query = (
        f'100 - (avg(rate(node_cpu_seconds_total{{instance="{instance}",mode="idle"}}[5m])) * 100)'
    )
    return _first_value(promql(query))


def get_linux_memory_bytes(instance: str):
    total = _first_value(
        promql(f'node_memory_MemTotal_bytes{{instance="{instance}"}}')
    )
    available = _first_value(
        promql(f'node_memory_MemAvailable_bytes{{instance="{instance}"}}')
    )

    if total is None or available is None:
        return None

    used = total - available

    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "used_percent": (used / total) * 100 if total else None,
    }

def get_linux_uptime_seconds(instance: str):
    query = (
        f'node_time_seconds{{instance="{instance}"}} '
        f'- node_boot_time_seconds{{instance="{instance}"}}'
    )

    return _first_value(promql(query))


def get_linux_load_average(instance: str):
    return {
        "load1": _first_value(
            promql(f'node_load1{{instance="{instance}"}}')
        ),
        "load5": _first_value(
            promql(f'node_load5{{instance="{instance}"}}')
        ),
        "load15": _first_value(
            promql(f'node_load15{{instance="{instance}"}}')
        ),
    }

def get_linux_filesystems(instance: str):
    query = (
        f'100 - ((node_filesystem_avail_bytes{{instance="{instance}",fstype!="tmpfs",fstype!="overlay",mountpoint!~"/run.*|/snap.*"}} '
        f'/ node_filesystem_size_bytes{{instance="{instance}",fstype!="tmpfs",fstype!="overlay",mountpoint!~"/run.*|/snap.*"}}) * 100)'
    )

    result = _vector_values(promql(query))
    filesystems = []

    for item in result:
        metric = item["metric"]
        filesystems.append(
            {
                "mountpoint": metric.get("mountpoint"),
                "device": metric.get("device"),
                "used_percent": item["value"],
            }
        )

    return filesystems


def get_linux_top_cpu_processes(instance: str, limit: int = 5):
    query = (
        f'topk({limit}, rate(namedprocess_namegroup_cpu_seconds_total{{instance="{instance}"}}[5m]) * 100)'
    )

    results = _vector_values(promql(query))
    processes = []

    for item in results:
        metric = item["metric"]
        processes.append(
            {
                "process": metric.get("groupname") or metric.get("name"),
                "cpu_percent_estimate": item["value"],
            }
        )

    return processes


def get_linux_top_memory_processes(instance: str, limit: int = 5):
    query = (
        f'topk({limit}, '
        f'namedprocess_namegroup_memory_bytes{{instance="{instance}",memtype="resident"}})'
    )

    results = _vector_values(promql(query))
    processes = []

    for item in results:
        metric = item["metric"]
        processes.append(
            {
                "process": metric.get("groupname") or metric.get("name"),
                "memory_bytes": item["value"],
            }
        )

    return processes


def get_linux_host_summary(host_ip: str) -> dict:
    node_instance = f"{host_ip}:9100"
    process_instance = f"{host_ip}:9256"

    node_status = get_target_status(node_instance)

    if not node_status["up"]:
        return {
            "host_ip": host_ip,
            "node_exporter": node_status,
            "status": "down",
            "message": "Prometheus reports this node as DOWN. No live node metrics are currently available.",
        }

    process_status = get_target_status(process_instance)
    memory = get_linux_memory_bytes(node_instance)
    uptime_seconds = get_linux_uptime_seconds(node_instance)
    load_average = get_linux_load_average(node_instance)

    return {
        "host_ip": host_ip,
        "status": "up",
        "observed_os": get_linux_os_info(node_instance),
        "node_exporter": node_status,
        "process_exporter": process_status,
        "cpu_percent": round(get_linux_cpu_percent(node_instance) or 0, 2),
        "uptime": {
            "seconds": round(uptime_seconds or 0),
            "hours": round((uptime_seconds or 0) / 3600, 2),
            "days": round((uptime_seconds or 0) / 86400, 2),
        },
        "load_average": load_average,
        "memory": {
            "total_gb": bytes_to_gb(memory["total_bytes"]) if memory else None,
            "used_gb": bytes_to_gb(memory["used_bytes"]) if memory else None,
            "available_gb": bytes_to_gb(memory["available_bytes"]) if memory else None,
            "used_percent": round(memory["used_percent"], 2) if memory else None,
        },
        "filesystems": get_linux_filesystems(node_instance),
        "top_cpu_processes": (
            get_linux_top_cpu_processes(process_instance)
            if process_status["up"]
            else []
        ),
        "top_memory_processes": (
            get_linux_top_memory_processes(process_instance)
            if process_status["up"]
            else []
        ),
    }
