# Proposed architecture and trust boundaries

Planned contract, not implemented capability. Read [SCOPE.md](SCOPE.md) for baseline and exclusions.

## Layers

Generic orchestrator (Hermes first) -> versioned MCP/API task interface -> local daemon admission/policy and durable task store -> authenticated peer transport -> worker daemon admission/policy -> opted-in existing worker session -> local agent permission/approval system.

Results follow the reverse path, with durable state queries and resumable event cursors so an unattended orchestrator can recover missed notifications. Keep the adapter thin: no Hermes core patches, no requirement that other orchestrators impersonate Hermes, and no new remote session launcher. Presence and ordinary peer messaging remain distinct from the control plane.

## Identity and admission

- Pin coordinator public keys locally; a coordinator display name, session name, message prefix or claimed role is never authority. Bind each authenticated request to the pinned identity, team, policy version and target capability. Specify key rotation/revocation and reject stale credentials; no trust-on-first-message.
- Separate membership administration from ordinary membership. Only explicitly authorized administrators may invite, admit, remove or change relay/policy metadata. A compatible old peer cannot bypass these restrictions: reject unsupported privileged operations or isolate incompatible peers. Prevent rollback/replayed roster state from restoring authority.
- Workers opt in locally, default off. Capabilities bind coordinator, permitted operations, repository identity/root and exact session incarnation, not just a reusable display name. Validate paths without exposing host paths to other peers. Closed/replaced sessions do not silently inherit task authority or unread task execution.
- Missing, malformed, conflicting, stale or unsupported policy fails closed for privileged operations. Enforce at receiving daemon/control API, not solely in prompts or the Hermes adapter. Local IPC identity and file/socket permissions must not allow ordinary peers to impersonate a local coordinator; local account compromise is outside this boundary.
- Typed authenticated task/control envelopes cannot be supplied through ordinary `send_message` text. Peer messages are untrusted input even when transport-authenticated. Prompt injection can still induce actions already allowed by the worker's local agent permissions: this is not an OS sandbox. Do not elevate permissions or turn messaging into unrestricted command execution.

Transport authenticates machines and protects message content; it does not itself grant orchestration authority. Relay operators can observe metadata/availability and disrupt delivery; possession of a team invitation is not coordinator authorization. Compromised authorized coordinators/workers remain a risk within granted capability. Minimize directory/task metadata and result disclosure; do not send secrets or arbitrary repository contents by default.

## Task semantics and recovery

Caller supplies stable task and idempotency IDs. Persist authorization, payload digest, worker/session incarnation, attempt ID, lease/fencing generation and transitions before acknowledging acceptance. Repeating the same identity/key/payload returns the same task; reuse with different content conflicts. Bound retention and document expiry so deduplication is never silently promised forever.

States: accepted (durably admitted), running (worker reports execution), succeeded/failed (terminal evidence), cancel-requested (request only), cancelled (confirmed stopped under the supported mechanism), unknown (execution/effects cannot be determined). Receipt/transport acknowledgments are not accepted execution or success. Define permitted transitions and event ordering; no late success may overwrite an already authoritative terminal state.

Bound leases and fence stale attempts/results. Worker and coordinator restarts, lease expiry or lost connectivity can leave work running: mark uncertain work unknown; do not silently replay or reassign it. Explicit retry/reassignment policy must acknowledge possible duplicate external effects and issue a new fenced attempt. Fencing protects protocol state, not already-running tools or external systems that lack fencing.

Cancellation is best effort until confirmed. Revocation blocks new admission and result acceptance from the revoked authority; it neither terminates running work nor undoes effects. Preserve audit evidence without treating a revoked/stale result as authoritative. Provide an explicit reconciliation path for humans when no trusted terminal report is available.

Results include task/attempt/fence identity, terminal status, summary, validation evidence and artifact references with provenance and access scope. An artifact reference is not proof of artifact integrity or success. Query/reconnect and notification deduplication must recover durable terminal state without resubmitting work.

## Approvals

Approvals bind task, attempt, action, repository/session scope and expiry; reject reuse for a different action or after revocation. Existing host agent permissions remain authoritative, including interactive denial. Unattended operation must surface “awaiting approval” as a nonterminal condition rather than silently approve, report success or hang without inspectable state. Production needs explicit human authorization; network membership and orchestrator trust never supply it.
