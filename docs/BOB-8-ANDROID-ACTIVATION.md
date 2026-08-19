# BOB-8 Android Activation

BOB-8 provides a mobile-first activation path for the PROJECT-BOB Android/Termux worker.

## Safety model

The worker stores its configuration under `~/.project-nas/bob-worker/` and attempts to restrict the configuration file to owner-only permissions. Tokens are never written into repository files. The worker exposes no arbitrary remote shell endpoint.

BOB remains an orchestrator. PROJECT-NAS policy remains the authorization authority.

## Termux

From a PROJECT-NAS checkout:

```bash
python -m runtime.bob.android_cli init --endpoint http://127.0.0.1:8000
python -m runtime.bob.android_cli doctor
python -m runtime.bob.android_cli register
python -m runtime.bob.android_cli status
python -m runtime.bob.android_cli heartbeat
```

For a remote BOB service, replace the endpoint with the reachable private endpoint. Do not expose the service publicly without an independently reviewed transport/security layer.

## Local versus remote

`127.0.0.1` only works when BOB is running on the same Android device. A PC-hosted BOB service requires an endpoint reachable from the phone.

## Recovery

The activation client is intentionally stateless at the HTTP transport layer. Durable worker/supervisor state remains owned by the existing BOB supervisor. After a process restart, run `doctor`, then `register`; the server-side worker registry and lease recovery logic remain authoritative.

## Android limitations

Android may stop background processes because of OS power management. BOB-8 does not claim uninterrupted execution. Use an OS-compatible startup/restart mechanism appropriate to the device, and treat reconnect/re-registration as normal recovery behavior.
