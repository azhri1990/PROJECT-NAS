# Omni Device AI Bridges v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, provider-agnostic AI/device bridge layer to PROJECT-NAS that can discover and route to compatible local/mobile AI endpoints while preserving the existing Omni Core security and verification model.

**Architecture:** Keep PROJECT-NAS as the orchestrator, policy owner, memory owner, and audit boundary. Add a typed adapter contract and an HTTP OpenAI-compatible adapter for endpoints such as Ollama Local AI and Hermes Agent; treat PocketPal, OfflineGPT, and Codex Mobile as optional adapters that are disabled unless a verified compatible endpoint is configured. Hermes-Relay remains a remote Android client/relay surface rather than a trusted execution authority.

**Tech Stack:** Python 3.x, FastAPI, Pydantic-compatible typed models, `requests`, SQLite-compatible existing runtime, pytest-compatible tests where available.

## Global Constraints

- Preserve the existing Omni Core design: policy/capability primitives precede autonomous execution.
- Local-first; no mandatory paid AI/API subscription.
- No unrestricted shell, filesystem, network, GitHub, or credential access for model output.
- Credentials are configuration secrets, never committed to the repository or sent to model context.
- External/mobile agents are untrusted execution peers; PROJECT-NAS remains the policy boundary.
- Provider selection must be deterministic and must never silently switch to a paid provider.
- Every adapter call has timeout, bounded payloads, health checks, and auditable provider metadata.
- Unknown or unsupported app APIs remain disabled rather than guessed.

---

### Task 1: Define provider and capability contracts

**Files:**
- Create: `runtime/omni/__init__.py`
- Create: `runtime/omni/models.py`
- Create: `runtime/omni/providers.py`
- Test: `runtime/tests/test_omni_models.py`

**Interfaces:**
- `ProviderKind` identifies `openai_compatible`, `local_only`, and `device_agent` roles.
- `ProviderConfig` contains `name`, `kind`, `base_url`, `api_key_env`, `model`, `enabled`, `timeout_seconds`, and `max_input_chars`.
- `ProviderHealth` contains `name`, `reachable`, `authenticated`, `latency_ms`, and `detail`.
- `AIProvider` exposes `health()` and `chat(messages)`.
- `ProviderRegistry` exposes `register(config, provider)`, `enabled()`, and `health_all()`.

- [ ] **Step 1: Write failing model tests**

```python
from runtime.omni.models import ProviderConfig, ProviderKind


def test_provider_config_defaults_are_local_first():
    config = ProviderConfig(name="ollama", kind=ProviderKind.OPENAI_COMPATIBLE, base_url="http://127.0.0.1:11434/v1")
    assert config.enabled is True
    assert config.timeout_seconds == 15
    assert config.max_input_chars == 12000
```

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest runtime/tests/test_omni_models.py -q`
Expected: FAIL because the models do not exist yet.

- [ ] **Step 3: Implement the minimal typed contracts**

Use dataclasses/enums from the standard library where possible. Validate URLs as HTTP(S), reject blank names, require positive timeout and input limits, and never store raw API key values in `ProviderConfig`.

- [ ] **Step 4: Re-run the focused test**

Run: `python -m pytest runtime/tests/test_omni_models.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/omni runtime/tests/test_omni_models.py
git commit -m "feat: add omni provider contracts"
```

---

### Task 2: Implement the OpenAI-compatible adapter

**Files:**
- Create: `runtime/omni/openai_compatible.py`
- Test: `runtime/tests/test_openai_compatible.py`

**Interfaces:**
- `OpenAICompatibleProvider(config, session=None)` implements `AIProvider`.
- `health()` calls `/health` when available, otherwise `/v1/models`.
- `chat(messages)` calls `/v1/chat/completions` and returns normalized assistant text plus provider/model metadata.

- [ ] **Step 1: Write failing adapter tests with a fake session**

```python
def test_chat_normalizes_openai_response():
    provider = OpenAICompatibleProvider(config, session=FakeSession({"choices": [{"message": {"content": "ok"}}]}))
    result = provider.chat([{"role": "user", "content": "hello"}])
    assert result.text == "ok"
    assert result.provider == "ollama"
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m pytest runtime/tests/test_openai_compatible.py -q`
Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Implement bounded HTTP behavior**

Use `requests.Session`, explicit timeout, `Authorization: Bearer` only when the configured environment variable exists, bounded message content, and strict response parsing. Never log the authorization header or response payload. Return structured failures rather than raw exceptions.

- [ ] **Step 4: Add health and error tests**

Cover timeout, HTTP 401, malformed JSON, missing choices, and oversized input. Each failure must return a safe diagnostic without secret material.

- [ ] **Step 5: Run the focused tests**

Run: `python -m pytest runtime/tests/test_openai_compatible.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/omni/openai_compatible.py runtime/tests/test_openai_compatible.py
git commit -m "feat: add openai compatible provider adapter"
```

---

### Task 3: Add deterministic app/provider profiles

**Files:**
- Create: `runtime/omni/catalog.py`
- Modify: `runtime/omni/models.py`
- Test: `runtime/tests/test_provider_catalog.py`

**Interfaces:**
- `default_catalog()` returns disabled-by-default profiles for `ollama-local-ai`, `hermes-agent`, `codex-mobile`, `pocketpal`, and `offlinegpt`.
- `ProviderProfile.status` distinguishes `supported`, `optional`, and `unverified`.
- Only `supported` profiles with an explicit URL and enabled flag may instantiate an active adapter.

- [ ] **Step 1: Write catalog tests**

Assert that Ollama Local AI and Hermes Agent use the OpenAI-compatible adapter contract, while PocketPal, OfflineGPT, and Codex Mobile are marked optional/unverified until an endpoint is explicitly configured.

- [ ] **Step 2: Run the tests and verify failure**

Run: `python -m pytest runtime/tests/test_provider_catalog.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement the catalog**

Use the exact app identities from the integration research. Do not claim an API for an app unless its configured endpoint passes a health check.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest runtime/tests/test_provider_catalog.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/omni/catalog.py runtime/omni/models.py runtime/tests/test_provider_catalog.py
git commit -m "feat: add mobile ai provider catalog"
```

---

### Task 4: Add backend provider discovery and health endpoint

**Files:**
- Modify: `runtime/backend.py`
- Create: `runtime/omni/service.py`
- Test: `runtime/tests/test_backend_omni.py`

**Interfaces:**
- `OmniService.providers()` returns provider metadata without secrets.
- `OmniService.health()` returns normalized health for enabled providers.
- `GET /omni/providers` exposes provider metadata and health only.
- `GET /omni/health` exposes aggregate health without credentials or prompts.

- [ ] **Step 1: Write API tests**

Cover empty configuration, one healthy provider, one unreachable provider, and secret-redaction assertions.

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest runtime/tests/test_backend_omni.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement the service and routes**

Load provider configuration only from environment variables or a local non-secret config file. Never accept an arbitrary URL directly from an HTTP request. Validate configured hosts against an explicit allowlist policy before network access.

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest runtime/tests/test_backend_omni.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/backend.py runtime/omni/service.py runtime/tests/test_backend_omni.py
git commit -m "feat: expose omni provider health"
```

---

### Task 5: Add security controls and documentation for device bridges

**Files:**
- Create: `runtime/omni/security.py`
- Create: `docs/OMNI-DEVICE-BRIDGES.md`
- Test: `runtime/tests/test_omni_security.py`

**Interfaces:**
- `is_allowed_provider_url(url, allowlist)` rejects localhost/network targets unless explicitly configured and rejects unsupported schemes.
- `redact_provider_metadata()` removes key names, token-like values, and authorization headers.
- `classify_provider_action()` labels chat, health, and device-control actions separately.

- [ ] **Step 1: Write adversarial tests**

Cover `file://`, `javascript:`, credential-in-URL, link-local, private-network, and unapproved public hosts. Also cover accidental API-key leakage in diagnostics.

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest runtime/tests/test_omni_security.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement the security boundary**

Default to deny for arbitrary network destinations. Device-control and terminal capabilities remain outside this milestone; this bridge only performs model chat and health discovery.

- [ ] **Step 4: Re-run the adversarial suite**

Run: `python -m pytest runtime/tests/test_omni_security.py -q`
Expected: PASS.

- [ ] **Step 5: Document the six-app integration matrix**

Document verified interfaces: Ollama Local AI exposes an OpenAI-compatible API; Hermes Agent exposes an OpenAI-compatible API when its API server is enabled; Hermes-Relay is a client/relay surface; Codex Mobile is a browser/app-server bridge; PocketPal and OfflineGPT are optional local inference surfaces with no assumed PROJECT-NAS API contract. Clearly label unverified/optional integrations.

- [ ] **Step 6: Commit**

```bash
git add runtime/omni/security.py runtime/tests/test_omni_security.py docs/OMNI-DEVICE-BRIDGES.md
git commit -m "feat: secure omni device bridge boundary"
```

---

### Task 6: Full verification and integration handoff

**Files:**
- Modify: `README-PC-START-HERE.md`
- Modify: `ACTION-PLAN.md`
- Test: existing runtime test suite plus new Omni tests

- [ ] **Step 1: Run focused Omni tests**

Run: `python -m pytest runtime/tests/test_omni_models.py runtime/tests/test_openai_compatible.py runtime/tests/test_provider_catalog.py runtime/tests/test_backend_omni.py runtime/tests/test_omni_security.py -q`
Expected: PASS.

- [ ] **Step 2: Run the existing runtime suite**

Run: `python -m pytest -q`
Expected: PASS or identify pre-existing failures separately.

- [ ] **Step 3: Run static checks available in the repository**

Use the repository's existing doctor/progress checks and any configured Python lint/type checks. Do not add a new tool solely for this milestone.

- [ ] **Step 4: Verify documentation accuracy**

Ensure docs distinguish implemented interfaces from future adapters and preserve the original Omni Core roadmap.

- [ ] **Step 5: Commit**

```bash
git add README-PC-START-HERE.md ACTION-PLAN.md
git commit -m "docs: record omni bridge milestone"
```

- [ ] **Step 6: Open a pull request to `main`**

The PR must summarize security boundaries, verified adapters, tests, and remaining optional integrations. Do not merge automatically.
