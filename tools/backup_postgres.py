from __future__ import annotations

import argparse
import pathlib
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/backups/servicedesk.sql")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"',
    ]
    with output.open("w", encoding="utf-8") as handle:
        subprocess.run(command, cwd=root, check=True, stdout=handle)
    print(output)


if __name__ == "__main__":
    main()
