from runtime.omni_policy import Decision, OmniCapability, OmniPolicy, OmniRequest


def test_read_capabilities_are_allowed():
    policy = OmniPolicy()
    for capability in (
        OmniCapability.READ_MEMORY,
        OmniCapability.READ_STATUS,
        OmniCapability.READ_REPOSITORY,
    ):
        result = policy.evaluate(OmniRequest(capability))
        assert result.decision is Decision.ALLOW


def test_write_and_device_control_require_approval():
    policy = OmniPolicy()
    for capability in (
        OmniCapability.WRITE_REPOSITORY,
        OmniCapability.DEVICE_CONTROL,
    ):
        result = policy.evaluate(OmniRequest(capability))
        assert result.decision is Decision.APPROVAL_REQUIRED


def test_process_and_network_are_denied():
    policy = OmniPolicy()
    for capability in (
        OmniCapability.EXECUTE_PROCESS,
        OmniCapability.NETWORK_ACCESS,
    ):
        result = policy.evaluate(OmniRequest(capability))
        assert result.decision is Decision.DENY
