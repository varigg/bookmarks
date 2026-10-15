"""Alerting: how the operator is told something broke."""

from typing import Protocol


class AlertError(Exception):
    pass


class Alerter(Protocol):
    def send(self, subject: str, body: str) -> None: ...
