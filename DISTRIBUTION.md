# Distribution safety policy

## Current policy: source only, no self-replacement

Freedom Network is developed in `bradvin/freedom-network`. There is no approved binary distribution channel in this slice. `install.sh` and `install.ps1` unconditionally fail before downloads, prompts, environment overrides, binary writes, PATH changes or delegation to the Reason CLI. This includes missing releases, unknown publishers, invalid versions, mirrors and missing/invalid checksums: none is eligible for installation. There is no upstream fallback.

`reason-network upgrade` fails before legacy migration, daemon access or installer execution, including binaries located in an inherited managed directory. The daemon no longer polls releases or runs any update installer. `auto_update` defaults to false; an inherited explicit `true` is accepted as configuration compatibility but produces a visible refusal, not an updater. The old updater's migration-copy helper is removed. Ordinary legacy state/name migration remains unchanged and does not download binaries.

Generated invitations use an already available local `reason-network join` command and quote invitation data for POSIX shell or PowerShell. Long invitations are emitted as raw tickets, not links to an upstream page that could offer an installer. This does not change ticket encoding, membership authorization or transport. Previously shared hosted links can still be parsed; do not use the hosted page's installation instructions.

For development, build a reviewed revision from this fork with `cargo build --locked`. This builds in the checkout; it does not install a service or modify agent configuration. Do not run `cargo install`, `setup`, an inherited installer, or a downloaded release as part of this policy. Local setup/configuration changes require their own authorization.

## Version and publisher identity

The inherited Cargo version `0.10.7`, executable name `reason-network`, ticket/wire identifiers and state paths are retained for compatibility. `--version` alone cannot distinguish this fork from upstream and is not publisher verification. Use the reviewed source commit and fork repository as the development identity. Cargo metadata now names this fork; licenses and original attribution remain intact.

Before any binary distribution is re-enabled, a separately authorized and reviewed slice must define:

- A fork-owned version/tag namespace that cannot be confused with inherited upstream versions.
- An exact fork repository, source commit and approved publisher identity, tied to the build/artifact provenance; an arbitrary repository or mirror environment variable is not authority.
- Artifact verification anchored independently of an archive/checksum pair from the same server. A matching SHA-256 alone establishes consistency, not publisher authenticity.
- Validation of versions, targets, archive contents, publisher/provenance and rollback policy before any execution or replacement. Missing, conflicting or unverifiable inputs must fail closed.
- Explicit manual update consent and separately reviewed opt-in if unattended updates are ever introduced. No fallback to upstream, Reason CLI installation or a mutable remote script pipeline.

No particular fork release tag, signed artifact or release readiness is claimed here.

## Inventory and deferred hazards

| Surface | P1 disposition |
| --- | --- |
| Shell and PowerShell installer defaults, mirror/repo/version overrides and first-run account prompt | Retired entrypoints; unconditional failure, no install or Reason CLI handoff |
| Explicit and background updater, including inherited `auto_update = true` | Removed binary replacement/polling; explicit upgrade refuses and old opt-in logs refusal |
| Generated commands and hosted join links (CLI and guided wizard) | Existing local executable only; raw long tickets; no hosted installer page |
| CLI/MCP join hints, upgrade help, skill and README | No upstream install/update instructions; source-only policy; binary and compatibility names retained |
| Migration | Local state/name/wiring migration retained; update-copy helper removed; upgrade refuses before migration. External legacy updaters/install managers are not controlled by this fork |
| Tray/UI | No installer launch path; compatibility branding/identifiers retained |
| Cargo metadata | Repository and description point to this fork; package/binary version/name intentionally unchanged |
| Release artifacts/scripts | Inherited packaging still uses `reason-network-*` and Cargo version. Retired scripts would be packaged if a release were run; that is not distribution approval |
| Release workflow | Audited, unchanged; `v*` tag push and `workflow_dispatch` can build and publish with `contents: write`. No fork version/provenance/approval gate is established. Do not create tags or dispatch it |

The release workflow's dependency/action pins do not prove fork publisher identity or artifact provenance. Its archives and adjacent checksums are not an approved distribution mechanism. Workflow/settings changes, release signing/provenance design and release execution require a later authorized slice.

P1 alone did not establish cloud independence. P2 subsequently removes Reason cloud/workspace CLI bridges, cloud-session setup and managed-directory coupling; see [REASON_INDEPENDENCE.md](REASON_INDEPENDENCE.md). Default n0 transport/discovery remains inherited for P3. An external package manager can still overwrite a binary, and neither slice validates real workers, Windows/WSL or cross-machine/custom-relay behavior.

## Reproducible checks

- `cargo fmt --check`
- `cargo clippy --all-targets --locked -- -D warnings`
- `cargo test --locked`
- `cargo build --locked`
- `python3 tests/distribution_safety.py --binary target/debug/reason-network`
- With a separately available PowerShell runtime: append `--powershell /path/to/pwsh` to exercise the PowerShell refusal. macOS PowerShell is not native Windows acceptance.

The fixture harness substitutes local executables and temporary state. It never downloads or installs an application binary. PATH interception is not a general network sandbox: the reviewed candidate has no native download path, and the isolated no-team daemon does not start transport. For stronger execution isolation, run the harness under an OS-level outbound-network denial where available. Skipped checks are printed explicitly and are not passes. Real agent/cross-machine/OS acceptance remains governed by [VALIDATION.md](VALIDATION.md).
