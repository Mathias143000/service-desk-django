from __future__ import annotations

import argparse
import pathlib
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--target-db", default="servicedesk_restore_check")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    backup = root / args.input
    if not backup.exists():
        raise FileNotFoundError(backup)

    create_command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        f'psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS {args.target_db};" && '
        f'psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE {args.target_db};"',
    ]
    subprocess.run(create_command, cwd=root, check=True)

    restore_command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "sh",
        "-lc",
        f'psql -U "$POSTGRES_USER" -d {args.target_db}',
    ]
    with backup.open("r", encoding="utf-8") as handle:
        subprocess.run(restore_command, cwd=root, check=True, stdin=handle)
    print(args.target_db)


if __name__ == "__main__":
    main()
