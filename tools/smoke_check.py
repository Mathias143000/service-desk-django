from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> dict[str, Any]:
    body = None
    request_headers = headers or {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **request_headers}

    request = urllib.request.Request(url, data=body, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.getcode()
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        content = exc.read().decode("utf-8")

    if status != expected_status:
        raise RuntimeError(f"{url} returned {status}, expected {expected_status}: {content}")

    return json.loads(content) if content else {}


def request_ok(url: str) -> None:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.getcode() != 200:
            raise RuntimeError(f"{url} returned {response.getcode()} instead of 200")


def wait_for(predicate, *, timeout: int, step: float, description: str):
    started = time.time()
    while time.time() - started < timeout:
        result = predicate()
        if result:
            return result
        time.sleep(step)
    raise RuntimeError(f"Timed out waiting for {description}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18220")
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:19220")
    parser.add_argument("--alertmanager-url", default="http://127.0.0.1:19223")
    parser.add_argument("--grafana-url", default="http://127.0.0.1:13180")
    parser.add_argument("--tempo-url", default="http://127.0.0.1:13241")
    parser.add_argument("--require-traces", action="store_true")
    parser.add_argument("--support-username", default="support")
    parser.add_argument("--support-password", default="pass12345")
    parser.add_argument("--seed-demo-data", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    root = pathlib.Path(__file__).resolve().parents[1]

    if args.seed_demo_data:
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "api",
                "python",
                "manage.py",
                "seed_demo_data",
            ],
            cwd=root,
            check=True,
        )

    health = request_json(f"{base_url}/api/health/")
    if health["status"] != "ok":
        raise RuntimeError(f"Health failed: {health}")

    request_json(
        f"{base_url}/api/auth/token/",
        method="POST",
        payload={"username": args.support_username, "password": "wrong-password"},
        expected_status=401,
    )

    auth = request_json(
        f"{base_url}/api/auth/token/",
        method="POST",
        payload={"username": args.support_username, "password": args.support_password},
    )
    token = auth["access"]
    headers = {"Authorization": f"Bearer {token}"}

    created = request_json(
        f"{base_url}/api/tickets/",
        method="POST",
        headers=headers,
        payload={
            "title": f"Smoke ticket {int(time.time())}",
            "description": "Background notification smoke test",
            "priority": "high",
        },
        expected_status=201,
    )
    ticket_id = created["id"]

    def notification_sent():
        ticket = request_json(f"{base_url}/api/tickets/{ticket_id}/", headers=headers)
        if ticket.get("notification_stub_sent_at"):
            return ticket
        return None

    wait_for(notification_sent, timeout=60, step=2, description="notification stub task")

    summary = request_json(f"{base_url}/api/tickets/summary/", headers=headers)
    if summary["visible_tickets"] < 1:
        raise RuntimeError(f"Unexpected summary payload: {summary}")

    analytics = request_json(f"{base_url}/api/tickets/analytics/", headers=headers)
    if "active_workload_by_assignee" not in analytics:
        raise RuntimeError(f"Unexpected analytics payload: {analytics}")

    def runtime_snapshot_ready():
        runtime = request_json(f"{base_url}/api/runtime/", headers=headers)
        snapshot = runtime.get("runtime_snapshot")
        if snapshot and snapshot.get("generated_at"):
            return runtime
        return None

    wait_for(runtime_snapshot_ready, timeout=90, step=5, description="beat operational snapshot")

    metrics_text = (
        urllib.request.urlopen(f"{base_url}/api/metrics/", timeout=10)
        .read()
        .decode("utf-8")
    )
    if "service_desk_http_requests_total" not in metrics_text:
        raise RuntimeError("Metrics endpoint is missing service_desk_http_requests_total")

    request_ok(f"{args.prometheus_url.rstrip('/')}/-/ready")
    request_ok(f"{args.alertmanager_url.rstrip('/')}/-/ready")
    request_json(f"{args.grafana_url.rstrip('/')}/api/health")

    try:
        traces = request_json(f"{args.tempo_url.rstrip('/')}/api/search?limit=5")
    except Exception:
        if args.require_traces:
            raise
        traces = {}

    if not traces.get("traces"):
        message = "Tempo search did not return traces yet"
        if args.require_traces:
            raise RuntimeError(message)
        print(f"warning: {message}", flush=True)

    print(json.dumps({"status": "ok", "ticket_id": ticket_id}, ensure_ascii=True))


if __name__ == "__main__":
    main()
