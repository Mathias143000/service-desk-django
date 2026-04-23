from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def require_markers(errors: list[str], path: Path, markers: list[str]) -> None:
    text = read(path)
    for marker in markers:
        if marker not in text:
            fail(errors, f"{path.relative_to(ROOT)} is missing marker: {marker}")


def main() -> int:
    errors: list[str] = []

    require_markers(
        errors,
        ROOT / "Dockerfile",
        [
            "adduser --disabled-password",
            "COPY --chown=appuser:appuser",
            "USER appuser",
        ],
    )

    require_markers(
        errors,
        ROOT / ".github" / "workflows" / "ci.yml",
        [
            "Hardening policy check",
            "tools/hardening_check.py",
            "ruff check src tools",
            "docker compose config",
            "tools/smoke_check.py --seed-demo-data",
        ],
    )

    require_markers(
        errors,
        ROOT / "docker-compose.yml",
        [
            "nginx:1.27-alpine",
            "celery",
            "run_scheduler",
            "prom/prometheus",
            "prom/alertmanager",
            "grafana/grafana-oss",
            "otel/opentelemetry-collector-contrib",
            "grafana/tempo",
            "healthcheck:",
        ],
    )

    for required in [
        ROOT / "nginx" / "default.conf",
        ROOT / "prometheus.yml",
        ROOT / "alerts.yml",
        ROOT / "alertmanager.yml",
        ROOT / "otel-collector" / "config.yml",
        ROOT / "tempo" / "config.yml",
        ROOT / "tools" / "smoke_check.py",
        ROOT / "tools" / "backup_postgres.py",
        ROOT / "tools" / "restore_postgres.py",
        ROOT / "tools" / "collect_logs.py",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "runbook.md",
        ROOT / "docs" / "hardening.md",
    ]:
        if not required.exists():
            fail(errors, f"missing required hardening asset: {required.relative_to(ROOT)}")

    require_markers(
        errors,
        ROOT / "README.md",
        [
            "non-root application container runtime",
            "hardening policy check",
            "docs/hardening.md",
            "compose-smoke",
        ],
    )

    report = {
        "status": "failed" if errors else "passed",
        "checks": [
            "application image runs as non-root",
            "CI includes workload hardening policy and compose smoke",
            "compose stack includes edge, async, observability, and health checks",
            "operator tools and hardening docs are present",
        ],
        "errors": errors,
    }

    output_dir = ROOT / "artifacts" / "hardening"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "hardening-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Service Desk workload hardening checks passed.")
    print(f"Report: {output_dir / 'hardening-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
