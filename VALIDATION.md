# Validation checklist

All runtime acceptance is pending. Record exact revision, test class, environment, expected/observed result and redacted evidence per future PR. Use pass/fail/blocked/not-run, never infer a pass from static inspection. No machines, sessions, credentials or relay availability are assumed.

## D0 documentation checks

- [ ] Diff contains only README and planned scope documents; no source, license, workflow or settings changes.
- [ ] Local relative links and Markdown anchors resolve; no private paths, operational data, credentials or unnecessary attribution in added text/PR body.
- [ ] Baseline matches fork main; commit author and committer are the requested project identity; independent read-only review covers exact candidate.
- [ ] PR targets this fork's main, not upstream; remote head SHA is verified. No merge/install/config/release/deployment.

These are publication gates, not runtime test results. Inherited documentation and notices are retained, not re-certified.

## Distribution and independence

- [ ] Static inventory: source/defaults, explicit and background updater, both installers, generated commands, UI/help/skills, onboarding URLs, metadata, migrations and release workflow/artifacts.
- [ ] Fixture tests: upstream replacement disabled; missing/invalid fork release/version/checksum/publisher data fails closed; mirror/environment overrides cannot bypass publisher policy; no execution of downloaded scripts in tests.
- [ ] Reason absent/denied: create/join team, discover existing sessions, message, coordinate and recover without Reason account, CLI, hosted page or cloud bridge.
- [ ] Explicit custom relay: block n0 and Reason endpoints; observe DNS and outbound connections (including startup, invite, direct/relay reconnect, restart and relay changes). No hidden lookup/relay fallback. Include indirect defaults and discovery paths, not just configured URL strings.
- [ ] Invalid/unreachable custom relay: visible failure, no hosted fallback. Long-form independently shareable invitations work without hosted rendering or short-code lookup.
- [ ] LAN with internet unavailable: measure discovery/direct messaging where supported; cross-NAT with operator-owned relay: measure delivery separately. Record necessary DNS/TLS/relay infrastructure and outages, including a member offline during relay change.

## Trust and protocol failure matrix

Exercise at unit/state-machine, isolated multi-process and real-session levels where applicable:

- [ ] Wrong key, spoofed coordinator name/role, unauthorized invitation/removal/metadata update, malformed/missing/stale policy, replayed roster, old/unsupported peer downgrade and ordinary-message control-command smuggling are rejected.
- [ ] Worker opt-in off, wrong repository/session, session-name reuse, rotation/revocation and expired/wrong-action approval cannot grant authority. Interactive permission denial survives unattended orchestration.
- [ ] Duplicate/reordered message, caller-ID payload conflict, restart before/after durable admission, disconnect during work and lost terminal notification preserve recoverable state without silent resubmission.
- [ ] Expired lease, stale fenced result and coordinator/worker crash produce explicit uncertainty where warranted. Explicit retry/reassignment warns about duplicate external effects; no exactly-once claim.
- [ ] Cancel-requested differs from confirmed cancelled; running uninterruptible work stays inspectable. Revocation blocks new admissions/results but cannot erase effects or guarantee termination.
- [ ] Results/artifact references are scoped, tied to authenticated task/attempt/session/fence and not mistaken for validated completion. Reconnect/cursor replay does not lose terminal results or duplicate execution.

## Real integration acceptance

| Layer | Required evidence | Current status |
| --- | --- | --- |
| Unit/protocol | Authorization, transitions, leases, fencing, conflicts and approval tests | Not run |
| Isolated processes | Persistence, duplicate/reorder, disconnect/restart, event recovery and updater fixtures | Not run |
| Generic client | Non-Hermes client exercises authenticated MCP/API lifecycle | Not run |
| Hermes + Codex | Existing session only, scoped work, durable unattended result, approval/denial | Not run |
| Hermes + Claude Code | Existing session only, scoped work, durable unattended result, approval/denial | Not run |
| Separate physical machines | Both worker kinds, real transport, restart and uncertain execution recovery | Not run |
| Linux/macOS/Windows native | Repository checks plus supported local IPC/session behavior | Not run |
| Windows/WSL boundary | Explicitly document worker/daemon placement, IPC/path identity, permissions, reconnect and unsupported combinations | Not run |
| Operator-owned relay | No n0/Reason traffic under explicit independent configuration, NAT/outage/invitation evidence | Not run |

Passing CI does not prove real-agent behavior, Windows/WSL interoperability or cloud independence. Missing environments remain explicit acceptance gaps. Real tests must avoid production repositories/actions and require separate permission for installation, agent configuration or infrastructure. Keep raw logs privately; publish only sanitized reproducible evidence.
