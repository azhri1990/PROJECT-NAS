# BOB-5 Android / Termux Worker

## Purpose

This package turns an Android device running Termux into a PROJECT-BOB worker. It is a worker client, not a remote shell and not an administrator of PROJECT-NAS.

## Prerequisites

- Android with Termux
- Python 3
- A PROJECT-NAS checkout
- Network access to the private BOB worker service
- A worker-scoped BOB authentication token supplied outside Git

## Bootstrap

From the PROJECT-NAS checkout in Termux:

```bash
bash runtime/bootstrap_bob_android.sh
```

Optionally set `PROJECT_NAS_ROOT` when the checkout is elsewhere.

## Configuration

Do not put tokens in repository files. Supply the worker token through the Termux environment or another local secret store:

```bash
export PROJECT_BOB_AUTH_TOKEN='REPLACE_WITH_WORKER_SCOPED_TOKEN'
```

The Android worker uses the BOB-4 HTTP endpoints for registration, heartbeat, claims, and result reporting.

## Safety

- The worker has no arbitrary shell endpoint.
- A capability declaration is not authorization.
- BOB leases jobs; expired leases are not treated as valid execution authority.
- NAS PolicyEngine/ToolGateway remains authoritative.
- Pending results are stored locally without bearer-token material.
- Network loss causes safe retry/reconciliation rather than permission escalation.

## Current limitation

The bootstrap validates the Android runtime and repository prerequisites. It does not silently start a persistent daemon or invent a public tunnel. Persistent background execution and private-network transport must be configured explicitly for the deployment environment.
