# P2 Reason-independent foundation

## Supported boundary

The standalone fork does not execute the upstream Reason CLI or bridge Reason cloud sessions/workspaces.
`reason = true` remains parseable for old configurations, but emits a disabled diagnostic and cannot enable
cloud discovery, session delivery or a workspace relay. Setup no longer offers the Reason cloud agent.
Installing or copying this binary under `.reason/bin` has no special meaning. External install managers
are outside this fork's control and can still replace their own files.

P1's source-only policy remains: no installer/self-upgrade execution or approved binary release channel.
Use an already available reviewed build. Independently share `reason-network join '<ticket>' --as <name>`;
long tickets do not require a hosted page. Legacy hosted URL parsing extracts ticket data locally, not by
fetching the page, and is not approval to follow that page's install instructions.

This is not authorization/task orchestration, a real-worker acceptance claim or a no-n0 connectivity mode.
Ordinary messages remain untrusted peer input; local permissions remain authoritative.

## Active-path inventory

| Surface | P2 disposition |
| --- | --- |
| `src/daemon/reason.rs` | Removed: `reason session list`, cloud synchronization, `reason network __relay`, Reason executable selection, workspace IO and cloud-session retry/backoff |
| `src/daemon/mod.rs`, `src/config.rs` | No cloud/managed relay tasks; default `reason = false`; explicit legacy true logs disabled and does not block ordinary operation |
| `src/daemon/mail.rs`, `src/daemon/sessions.rs` | No `reason session send` path or Reason push-tier special case; old/explicit `agent = "reason"` session data cannot execute the CLI |
| `src/main.rs`, `src/wizard.rs` | No managed-directory mode; standalone command rendering and local raw-ticket onboarding; no cloud-agent invite promotion |
| `src/setup.rs`, `src/agent.rs` | No Reason cloud setup/detection or `REASON_BIN` service environment injection; local integrations retained |
| `src/migrate.rs` | No Reason-owned install-location/CLI-presence bypass; ordinary same-binary legacy migration retained, no download added |
| `src/render.rs`, `src/skill.md` | No Reason-specific cloud reply treatment; source-only, local command guidance and unsupported-cloud boundary |
| `src/team.rs`, `src/net.rs` | Ticket parsing/encoding, signed membership/admission, peer framing and transport unchanged; legacy hosted URLs are data only |
| Default iroh/n0 lookup, relay and LAN discovery | Unchanged, explicitly deferred to P3; no independent-mode/no-n0 runtime claim |
| Installers, updater, release workflow | P1 refusals retained; release workflow remains an unauthorised publication hazard, not an approved channel |

## Evidence and reproduction

First build the candidate with `cargo build --locked`. On macOS:

```sh
python3 tests/reason_independence.py --binary target/debug/reason-network
```

The harness reexecutes under `sandbox-exec` with outbound networking denied except local-host IP and Unix
sockets. Before spawning fixtures it requires external TCP and UDP probes to fail with `EPERM`, rather
than treating DNS failure, timeout or an unreachable network as isolation evidence. Child environments
allow only fixture HOME/state, tools-only PATH and disabled tray/service/mDNS. Every local-agent BIN lookup
is explicitly pinned to an absent fixture path: PATH alone does not prevent global executable fallback.
A harmless fallback Claude sentinel verifies the pin blocks lookup, with an unpinned positive control proving
that dry-run setup would otherwise execute the fixture. No real agents, services,
profile wiring or application installation are used. Temporary child processes and files are cleaned up.
This guard is test isolation, not a production worker sandbox. Other OS execution is explicitly unsupported
by this harness, not silently run without a guard.

Observed classes:

- RED on the accepted P1 binary: the trap recorded cloud session enumeration, cloud delivery and managed
  workspace relay execution. These are behavioral failures, not source-string assertions. P1 already removed
  hosted-page generation; its distribution/invitation tests remain the baseline control for that behavior.
- GREEN: local daemon startup, explicit legacy-true diagnostics, existing local session registration and
  message/inbox round trips with Reason absent and with the trap present; managed-directory/legacy executable
  environment traps; cloud-label delivery and dry-run setup cannot invoke the upstream CLI.
- GREEN: two real daemon processes create a team and redeem a raw ticket over local QUIC, persist admission
  and restart into that team, with both missing and trap-present Reason CLI configurations under outbound denial.
- Rust/unit controls cover default/legacy configuration, client-name classification and existing signed
  membership/ticket parsing, invitation rendering and peer logic. They are distinct from process evidence.

For the additional denied-external peer-reconnect attempt:

```sh
python3 tests/reason_independence.py --binary target/debug/reason-network --transport
```

This optional case currently FAILS after admission/restart: peer session discovery does not converge while
external address lookup and mDNS are denied, so remote message delivery is not reached. The default suite
reports the case as skipped, not passed. Admission succeeded, but that does not prove post-restart peer
messaging. Do not remove the guard or silently permit public discovery to turn this into a green result.
Resolving and validating the connectivity gap is a separate P3 concern; P2 does not provision a relay or
change discovery semantics. The broader Reason-denied acceptance item in VALIDATION.md stays unchecked.

## Compatibility and remaining gates

Retained compatibility includes the Cargo/package/executable name and inherited version, wire ALPN/frame
identifiers, `tincan1` tickets and hosted URL parsing, `REASON_NETWORK_*`/`TINCAN_*` environment names,
`~/.reason/network` state and legacy state migration. These names are not executable Reason dependencies,
fork publisher identity, trusted command authority or a reason to perform a blanket rename.

Required gaps remain visible: post-restart peer messaging under outbound denial, operator-owned relay/no-n0
traffic evidence (including reconnect and offline-member changes), separate physical machines, native
Windows/WSL and Linux process coverage, real Codex/Claude/Hermes sessions, and P4-P8 authorization/task/result
semantics. Passing local gates or hosted CI does not satisfy those gates. See VALIDATION.md, TRUST.md and
IMPLEMENTATION.md. No merge, release, deployment, real agent configuration or relay spend is implied.
