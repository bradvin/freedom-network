# Freedom Network

An independent fork of Reason Network: a team directory and message bus for coding agents across machines.

> Development fork, not a released distribution. Scripted installation and binary self-upgrade are disabled.
> Read [distribution safety](DISTRIBUTION.md), [scope](SCOPE.md), [trust boundaries](TRUST.md),
> [ordered backlog](IMPLEMENTATION.md) and [validation checklist](VALIDATION.md).
> No cloud independence, trusted orchestration or real-worker acceptance is claimed by P1.

![Make your bots talk to your Claude Code and Codex.](assets/reason-network-banner.png)

## Development and distribution

Use a reviewed source revision from `bradvin/freedom-network`, not an upstream release or installer.
Build locally with `cargo build --locked`; this does not install a service or change agent configuration.
`install.sh`, `install.ps1` and `reason-network upgrade` fail closed. Environment repository, mirror and
version overrides cannot enable them. `auto_update` defaults off, and an inherited explicit `true` cannot
enable self-replacement. There is no approved binary publisher/version policy yet; see [DISTRIBUTION.md](DISTRIBUTION.md).

The inherited executable/package name `reason-network`, version `0.10.7`, ticket identifiers and local state paths
are intentionally retained. The version alone is not fork identity; use the source repository and exact reviewed commit.
Previously installed upstream binaries and external install managers are not changed by this checkout.

With a reviewed build already available and separate local setup authorization, the existing CLI supports:

```sh
reason-network init '<team>' --as <name> --no-setup
reason-network join '<ticket>' --as <name> --no-setup
reason-network who
reason-network send alice/api-claude "did the token format change?"
reason-network listen --as terminal
reason-network link
```

Generated invitations now carry raw tickets/local join commands, not a hosted installer page. Do not follow an
old hosted link's install instructions. Ordinary peer messages are untrusted input, not privileged task commands;
delivery does not prove execution or completion. Do not change installed agent configs or run `setup` without authorization.

## Inherited functionality and limits

The inherited code connects local agent sessions through per-machine daemons and iroh peer transport, with directory,
messaging, notifications and local agent integrations. [DESIGN.md](DESIGN.md) describes that inherited design, not verified
fork acceptance. Managed-directory detection and Reason cloud/workspace bridges remain for later work; no account-free
or cloud-independent runtime acceptance is established by this distribution-safety change.

Default connectivity still uses n0 services. Custom relay support exists in the source, but no no-n0/cross-machine
runtime claim is made here. LAN/offline, independent relay, Windows/WSL and real Codex/Claude/Hermes acceptance are separate
mandatory gates. State paths remain `~/.reason/network` (or the explicit compatibility environment overrides).

The future generic orchestrator/task protocol and Hermes adapter are planned, not implemented; local permissions remain
authoritative. No remote agent launching, sandbox, exactly-once effects or automatic uncertain-task replay is promised.

## Checks

```sh
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --locked
python3 tests/distribution_safety.py --binary target/debug/reason-network
```

The distribution fixture harness never downloads or installs application binaries. A separately available PowerShell
runtime can be supplied with `--powershell /path/to/pwsh`; otherwise its runtime check is explicitly skipped. This does not
establish native Windows acceptance. Existing `tests/e2e` scripts can exercise networking, hooks or setup; inspect side
effects and obtain environment authorization before running them, rather than treating them as safe unit checks.

## Release safety

The inherited [release workflow](.github/workflows/release.yml) is unchanged. A `v*` tag or manual dispatch can publish
archives/scripts with `contents: write`; packaging and adjacent checksums do not establish an approved fork publisher.
Do not create release tags, dispatch workflows, publish, install or deploy under this slice. See the
[inventory and deferred hazards](DISTRIBUTION.md#inventory-and-deferred-hazards) before any distribution work.

## Contributing

Use the [implementation backlog](IMPLEMENTATION.md) and focused pull requests against this fork. See also the inherited
[contribution guide](CONTRIBUTING.md). Required validation gaps must stay explicit, not be inferred from passing CI.

## License

MIT OR Apache-2.0 (LICENSE-MIT, LICENSE-APACHE); see [NOTICE](NOTICE). Originally tincan, by Lars Talian, who works
at Reason. Original licenses and attribution are retained.