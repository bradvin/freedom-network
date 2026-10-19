# Security

For upstream vulnerabilities, please report privately through
[GitHub's private reporting](https://github.com/reason-machines/reason-network/security/advisories/new), not in a
public issue. Say what an attacker can do and how to reproduce it.

That link belongs to upstream, not this fork. A fork-specific private reporting channel has not been verified;
arrange private contact with the fork maintainer rather than publishing vulnerability details publicly.

What matters most:

- Someone outside a team joining it, reading its messages or sessions, or sending into it.
- A team member speaking for another person or machine.
- Another local user or process talking to the daemon, or posing as it.
- A message making an agent do more than its user would see in the `<reason-message>` block.

Upstream historically shipped fixes through releases installed by the Reason CLI. This fork does not install
those releases or hand off to the Reason CLI; use a reviewed source revision under [DISTRIBUTION.md](DISTRIBUTION.md).
