"""PC worker identity adapter."""
from __future__ import annotations

from ..worker_client import WorkerClient
from ..worker_protocol import WorkerRegistration


def create_worker(worker_id: str, capabilities: frozenset[str], request) -> WorkerClient:
    return WorkerClient(request, WorkerRegistration(worker_id, "pc", capabilities))
