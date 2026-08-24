# PROJECT-NAS Data Index

This index defines the classes of project data that must be preserved in GitHub.

## Source data
- source code
- tests
- scripts
- runtime modules
- worker implementations
- API contracts

## Configuration data
- environment templates
- model/provider configuration
- runtime configuration
- platform-specific requirements
- policy configuration

**Never commit secrets.**

## AI data
- system prompts
- master prompts
- capability definitions
- tool definitions
- memory schemas
- learning schemas
- recommendation metadata
- approval receipts/schemas where safe to retain

## Operational data
- state schemas
- job/lease models
- worker registry structures
- audit event schemas
- diagnostic output intended for retention
- certification evidence

## Knowledge data
- architecture documents
- decisions
- rules
- known issues
- failure analysis
- recovery procedures
- roadmaps
- transfer/handover documents

## Historical data
- branch history
- commit history
- PRs
- superseded designs
- migration notes

## Excluded data
- passwords
- private keys
- API tokens
- credentials
- personal secrets
- raw sensitive production data

These exclusions are deliberate security controls, not missing project data.
