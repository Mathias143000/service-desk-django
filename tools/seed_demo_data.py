from __future__ import annotations

import pathlib
import subprocess


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "manage.py", "seed_demo_data"],
        cwd=root,
        check=True,
    )


if __name__ == "__main__":
    main()
