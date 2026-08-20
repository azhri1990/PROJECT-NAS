"""Durable, local-only queue storage for PROJECT-BOB.

This layer stores job state without adding authority. Governance remains in
BobControlLoop; this module only provides persistence and recovery primitives.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable

from 07-AUTOMATION.bob.job_queue import Job, JobState
