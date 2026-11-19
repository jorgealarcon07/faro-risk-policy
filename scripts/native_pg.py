"""Run a Python command with its own disposable, loopback-only PostgreSQL cluster."""

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psycopg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55434)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Pass a Python command after --")
    runtime = Path(".runtime").resolve()
    runtime.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(dir=runtime))
    data = run / "pg"
    password = secrets.token_urlsafe(32)
    pw = run / "init.password"
    pw.write_text(password, encoding="utf8")

    def pg(name):
        return str(args.bin.resolve() / (name + (".exe" if os.name == "nt" else "")))

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        subprocess.run(
            [
                pg("initdb"),
                "-D",
                str(data),
                "-U",
                "faro_risk",
                "--encoding=UTF8",
                "--locale=C",
                "--auth=scram-sha-256",
                f"--pwfile={pw}",
            ],
            check=True,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
        )
    finally:
        pw.unlink(missing_ok=True)
    environment = dict(
        os.environ,
        PGHOST="127.0.0.1",
        PGPORT=str(args.port),
        PGUSER="faro_risk",
        PGPASSWORD=password,
        PGDATABASE="postgres",
    )
    with (run / "server.log").open("w") as log:
        server = subprocess.Popen(
            [pg("postgres"), "-D", str(data), "-h", "127.0.0.1", "-p", str(args.port)],
            creationflags=flags,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError(f"PostgreSQL stopped. Inspect {log.name}")
                try:
                    with psycopg.connect(
                        host="127.0.0.1",
                        port=args.port,
                        user="faro_risk",
                        dbname="postgres",
                        password=password,
                        connect_timeout=2,
                    ):
                        break
                except psycopg.OperationalError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Timed out connecting to the new cluster")
            return subprocess.run(
                [sys.executable, *command], env=environment, check=False
            ).returncode
        finally:
            if server.poll() is None:
                subprocess.run(
                    [pg("pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"],
                    timeout=40,
                    stdout=subprocess.DEVNULL,
                    check=True,
                    creationflags=flags,
                )
                server.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
