# Freedom Network scope

Status: proposal and phased backlog only. No fork runtime acceptance has been established.
This document governs the fork's planned changes; [DESIGN.md](DESIGN.md) describes inherited behavior, not proof of these goals.

## Evidence and purpose

Baseline: fork `bradvin/freedom-network` main at `19b1fbf72430fd9d554f3db70da55f5659d5c402` (package 0.10.7).
Static inspection, not a running prototype, establishes:

- [src/net.rs](src/net.rs) has iroh peer transport, default n0 services and a custom-relay path using the minimal preset.
- [src/daemon/reason.rs](src/daemon/reason.rs) bridges Reason cloud sessions; [install.sh](install.sh) offers hosted onboarding.
- [src/main.rs](src/main.rs), [src/daemon/update.rs](src/daemon/update.rs), both installers and the README point installation/update traffic at upstream releases.
- [DESIGN.md](DESIGN.md) describes any-member invitation/removal and inherited session names/mail. Neither is sufficient authorization for privileged orchestration or task recovery.
- [Cargo.toml](Cargo.toml) and [CI](.github/workflows/ci.yml) define a Rust binary and Linux/macOS/Windows checks. [Release configuration](.github/workflows/release.yml) publishes on version tags or manual dispatch.

Goal: an independently operable agent-team network, usable by a generic trusted third-party orchestrator, with Hermes as the first supported adapter. Initial workers are already-running Codex and Claude Code sessions on separate machines. Retain useful independent transport and existing local agent integration; do not blindly rename wire identifiers, state paths or compatibility interfaces. Preserve both licenses and NOTICE.

## Critical first gate: distribution safety

Do not run the inherited installation commands or treat this fork as a safe distribution yet. The daemon can replace a standalone binary using upstream installation scripts; changing only a download environment variable or README would not fix the compiled update source. Checksums fetched beside an archive establish consistency, not independent publisher authenticity.

The first implementation PR must neutralize upstream binary replacement and hosted installer handoffs before other implementation or installation trials. Audit explicit and automatic updates, generated join/install commands, shell and PowerShell installers, migration paths, UI/help/skill links, package metadata, defaults and release artifact/script provenance. Disable unattended replacement by default; unsupported or absent fork releases must fail closed without upstream fallback. Document a deliberate, reviewed fork update policy and version/publisher verification. Review the tag/manual release workflow as an artifact-distribution hazard, without triggering or changing Actions, repository settings or publishing a release in this scope.

This documentation does not remove the hazard; inherited README instructions remain historical context below its fork warning.

## Independence means three different things

1. No Reason service: no account, Reason CLI, workspace sync, hosted join page, cloud bridge or Reason-hosted onboarding needed for team creation, admission, messaging and orchestration.
2. No n0 service: an explicit self-hosted relay/discovery mode must avoid n0 relays, DNS/pkarr lookup and accidental fallback, including invitations and reconnects. Existing source suggests support; fresh runtime evidence is required. Invalid relay configuration must fail closed.
3. No infrastructure: not promised for arbitrary internet/NAT traversal. LAN direct discovery can work without a hosted service; cross-network peers may need operator-owned relay, DNS/TLS and reachability. Cloud independence is not universal offline connectivity. Dependency downloads/build distribution are separate from runtime network independence.

Relay provisioning, hosting spend and live installations require separate authorization. Defaults and remaining external dependencies must be explicit, not hidden behind a claim of “no server.”

## Boundaries and exclusions

No arbitrary remote shell, remote agent launching, new worker sessions, OS sandbox claims, Hermes core monkeypatches, production deployment or automatic approval. No installed agent/profile configuration changes in this scope PR. Local humans retain permissions; production actions always require the owner's explicit approval. Existing hook mechanisms that wake/resume sessions must not create replacement sessions under the initial worker contract.

No global rebrand, broad transport rewrite, exactly-once execution guarantee, automatic uncertain-task replay, new hosted control plane, general support for every inherited agent, or claim that receipt means execution/completion. Issues need not be enabled: [IMPLEMENTATION.md](IMPLEMENTATION.md) is the checked-in backlog. No merging, Actions/settings changes, install, configuration, deployment or release is authorized by this documentation slice. Later workflow or release changes need a separately authorized slice.

## Completion evidence

The architecture contract is in [TRUST.md](TRUST.md), ordered acceptance/exclusions in [IMPLEMENTATION.md](IMPLEMENTATION.md), and the evidence matrix in [VALIDATION.md](VALIDATION.md). Every future PR must distinguish static evidence, simulated/process checks and real-session validation; unchecked acceptance remains a gap, not an implied pass.
