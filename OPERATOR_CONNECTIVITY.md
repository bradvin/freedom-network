# Guarded operator connectivity (B-local)

`tests/operator_connectivity.py` is an optional macOS same-host process harness.
It starts a disposable, explicitly configured custom relay and two private daemons.
It does not install anything, alter application transport policy, execute real
agents, or establish cross-NAT/forced-relay independence.

## Prerequisite: independently verified relay

Prepare `iroh-relay` **1.3.0**, binary feature `server`, in a private workspace.
The approved crates.io archive SHA-256 is
`ee116a8233f84980574bb8d11e4517503080cd2c3605bafca04ee9c35d708bd9`.
Its unchanged packaged `Cargo.lock` SHA-256 is
`e3ab330ffbdc4902d3c932cc247586072a2b09b9768c3dc618159302f8e8611d`.
This is a fixture dependency, not a new production manifest dependency.

Dependency acquisition requires operator authorization, verified HTTPS and a
credential-free private Cargo home. Do not inherit source replacements, change
the packaged lock, substitute another version, or run fetched build scripts with
network permission. Build with the unchanged lock, `--features server --bin
iroh-relay --locked --offline`, `CARGO_NET_OFFLINE=true`, bounded concurrency,
a private target directory, and an outbound-denied OS sandbox. Cargo offline
mode alone does not prevent build-script networking. Preserve archive/lock
checksums, exact dependency versions and archive checksums, build command/output,
binary hash and `--version` output privately. Do not use `cargo install`.

Before use, actually launch the binary under a loopback-only guard with an
explicit existing TOML config:

```toml
http_bind_addr = "127.0.0.1:PORT"
enable_relay = true
enable_metrics = false
enable_quic_addr_discovery = false
```

Replace `PORT` with an owned disposable port. Do not use bare `--dev`: defaults
can bind wildcard addresses. Verify process-owned sockets with `lsof`: exactly
the intended IPv4 loopback TCP listener, no metrics, UDP/QUIC or wildcard listener.
Verify external TCP/UDP denial with EPERM and owned-child cleanup. Record the
resulting readiness manifest with these exact fields (replace the binary hash):

```json
{
  "schema": 1,
  "status": "passed",
  "crate": "iroh-relay",
  "version": "1.3.0",
  "archive_sha256": "ee116a8233f84980574bb8d11e4517503080cd2c3605bafca04ee9c35d708bd9",
  "packaged_lock_sha256": "e3ab330ffbdc4902d3c932cc247586072a2b09b9768c3dc618159302f8e8611d",
  "binary_sha256": "REPLACE_WITH_VERIFIED_BINARY_SHA256",
  "offline_build": true,
  "outbound_denied_build": true,
  "loopback_listener_verified": true,
  "metrics_disabled": true,
  "quic_disabled": true
}
```

The manifest is an operator evidence attestation, not a signature or substitute
for inspecting source/build provenance. The runner checks its required fields
and executable hash before execution, rechecks the hash before each relay
launch, and verifies actual listeners on each launch. Missing/unverified
prerequisites exit nonzero as BLOCKED, never a successful skip.

## Run

Use absolute private paths for relay, readiness manifest and a **new** output
directory. The runner requires only Python's standard library, sandbox-exec and
lsof; it does not download or build dependencies.

```sh
python3 tests/operator_connectivity_checks.py
python3 tests/operator_connectivity.py \
  --binary /absolute/private/target/debug/reason-network \
  --relay-bin /absolute/private/target/debug/iroh-relay \
  --relay-sha256 VERIFIED_BINARY_SHA256 \
  --readiness-manifest /absolute/private/readiness.json \
  --scratch-dir /absolute/private/short-scratch \
  --output-dir /absolute/private/new-b-local-results
```

Default whole-run deadline: 600 seconds (`--timeout`). Receipts, state databases
and phase logs remain private in the output directory. They contain ephemeral
identities, paths and invitation-related metadata: do not commit or publish them.
The runner owns its child process group and terminates children on normal exit,
failure and timeout. Exit 0 means the assertions passed; 2 means prerequisites
blocked; 124 means deadline exceeded; other nonzero results are failures.

## Assertions and interpretation

Both Reason-absent and trap-present variants exercise:

- Private HOME/state/temp, services/tray/mDNS disabled, all real-agent binary
  lookups pinned absent, and negative/positive harmless fallback sentinel controls.
- External IPv4/IPv6 TCP and UDP EPERM controls, loopback positive controls and
  mDNS denial (IPv6 unsupported status is recorded where socket creation fails).
- Initial custom-relay create, long-ticket join, durable two-member roster,
  peer/session presence, bidirectional unique ordinary messages, exact receiver
  inbox IDs/body, sender acknowledgement and durable outbox settlement.
- Individual and simultaneous daemon restart from retained metadata, synthetic
  session re-registration and fresh messages without rejoin/ticket replay.
- Malformed/unreachable create/set rejection without persisting bad metadata or
  replacing the healthy relay; relay outage, both peers restarted while down,
  local IPC/persisted relay retention and recovery at the same relay address.
- Exclusive relay listener ownership on each launch and owned-child cleanup.

The fixture runner denies non-loopback outbound IP, allows local IPC and loopback
transport, and validates the guard before fixtures. Its parent supervisor launches
the relay separately under an exact-port inbound/bind guard with all outbound
networking denied: macOS does not permit nested sandbox application. The inherited
socketpair accepts only fixed start/stop operations for this one relay. Daemon direct
loopback QUIC paths may survive relay loss: outage observations are not proof of
relay-only delivery. This is B-local, not B-real or a forced-relay test.

No packet capture or complete blocked-attempt/DNS-attribution trace is claimed.
OS-delegated DNS can occur outside the process sandbox; empty traffic observations
are not proof of no n0 lookup. Literal loopback relay configuration, no mDNS,
Minimal/custom-relay application policy, guard controls and runtime receipts are
complementary evidence, not universal internet-independence acceptance.

The existing `tests/reason_independence.py --transport` C0 failure remains
unchanged and separate; B-local must not waive or relabel it. Offline-member
two-relay change, real/cross-NAT relay, LAN, native Linux/Windows/WSL and actual
Codex/Claude/Hermes sessions remain final P3/P8 gaps. Ordinary message receipt is
not task execution/completion and provides no exactly-once guarantee.
