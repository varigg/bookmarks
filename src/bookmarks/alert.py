"""Alerting edge: the operator's email.

The msmtp adapter relies on the host's mail relay; cron jobs run as the user,
so a readable per-user ~/.msmtprc must exist (2026-10: /etc/msmtprc is root-only).
"""

import subprocess
from typing import Protocol


class AlertError(Exception):
    pass


class Alerter(Protocol):
    def send(self, subject: str, body: str) -> None: ...


class MsmtpAlerter:
    def __init__(self, to: str, executable: str = "msmtp", timeout: float = 30.0):
        self.to = to
        self.executable = executable
        self.timeout = timeout

    def send(self, subject: str, body: str) -> None:
        message = f"To: {self.to}\nSubject: {subject}\n\n{body}\n"
        try:
            done = subprocess.run(
                [self.executable, "-t"],
                input=message,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AlertError(f"msmtp did not run: {error}") from error
        if done.returncode != 0:
            raise AlertError(f"msmtp exited {done.returncode}: {done.stderr.strip()}")
