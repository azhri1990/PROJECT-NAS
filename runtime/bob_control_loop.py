"""Bounded autonomous task/control loop for PROJECT-BOB."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from runtime.autopilot_governance import AutopilotGovernance, DecisionClass
from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest
from 07-AUTOMATION.bob.job_queue import Job, JobQueue, JobState
