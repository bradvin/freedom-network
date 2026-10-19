#!/usr/bin/env python3
"""Guarded macOS B-local process test, not cross-NAT or real-worker acceptance.

Requires an independently prepared, pinned iroh-relay 1.3.0 readiness manifest.
No downloads, installs, real agents, services, or application policy changes.
See OPERATOR_CONNECTIVITY.md. All receipts stay in a new private output directory.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

ARCHIVE_SHA256 = 'ee116a8233f84980574bb8d11e4517503080cd2c3605bafca04ee9c35d708bd9'
LOCK_SHA256 = 'e3ab330ffbdc4902d3c932cc247586072a2b09b9768c3dc618159302f8e8611d'
AGENTS = ('claude', 'codex', 'grok', 'cursor-agent', 'gemini', 'copilot', 'opencode', 'pi', 'dsh')


class Blocked(RuntimeError):
    """Prerequisites not met; a nonzero result, never a passing skip."""


def digest(path):
    with path.open('rb') as stream:
        result = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
        return result.hexdigest()


def validate_relay(binary, expected, manifest):
    required = dict(schema=1, status='passed', crate='iroh-relay', version='1.3.0',
                    archive_sha256=ARCHIVE_SHA256, packaged_lock_sha256=LOCK_SHA256,
                    binary_sha256=expected, offline_build=True, outbound_denied_build=True,
                    loopback_listener_verified=True, metrics_disabled=True, quic_disabled=True)
    try:
        if not binary.is_absolute() or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('absolute relay path and lowercase SHA-256 required')
        data = json.loads(manifest.read_text())
        if not isinstance(data, dict) or any(type(data.get(k)) is not type(v) or data.get(k) != v
                                             for k, v in required.items()):
            raise ValueError('pinned-version readiness fields missing or inconsistent')
        if digest(binary) != expected:
            raise ValueError('relay executable SHA-256 mismatch')
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise Blocked(str(exc)) from exc


def wait_for(check, description, seconds=25):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        last = check()
        if last:
            return last
        time.sleep(.1)
    raise AssertionError(f'timeout: {description}; last={last!r}')


def relay_sockets(output, port):
    """One loopback listener; accepted loopback TCP streams are not listeners."""
    rows = output.splitlines()[1:]
    if not rows:
        return False
    listener = f'TCP 127.0.0.1:{port} (LISTEN)'
    assert sum(row.endswith(listener) for row in rows) == 1, rows
    for row in rows:
        assert row.endswith(listener) or re.search(
            rf'TCP 127\.0\.0\.1:{port}->127\.0\.0\.1:[0-9]+ \([A-Z_]+\)$', row), rows
    return True


class Rpc:
    def __init__(self, state):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(40)
        try:
            self.sock.connect(str(state / 'network.sock'))
        except BaseException:
            self.sock.close()
            raise
        self.stream = self.sock.makefile('rwb')
        self.seq = 0

    def close(self):
        self.stream.close()
        self.sock.close()

    def call(self, op, **fields):
        self.seq += 1
        self.stream.write((json.dumps(dict(id=self.seq, op=op, **fields))+'\n').encode())
        self.stream.flush()
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError('daemon disconnected')
            reply = json.loads(line)
            if reply.get('id') == self.seq:
                if reply.get('error'):
                    raise RuntimeError(reply['error'])
                return reply.get('result')


class RelayOwner:
    """Unsandboxed supervisor; relay itself is always strictly sandboxed.

    macOS rejects nested sandbox_apply. Only fixed start/stop operations cross
    the inherited socketpair, never arbitrary commands, paths or network URLs.
    """
    def __init__(self, args):
        self.args = args
        self.process = None
        self.logs = []
        self.events = []
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            self.port = reservation.getsockname()[1]

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.events.append(dict(phase='relay-stopped', pid=self.process.pid,
                                    exit_code=self.process.returncode))
            self.process = None
        for log in self.logs:
            log.close()
        self.logs.clear()
        (self.args.output_dir/'relay-owner.json').write_text(json.dumps(self.events, indent=2)+'\n')

    def start(self):
        assert self.process is None, 'relay already running'
        args, port = self.args, self.port
        config = args.output_dir/'relay.toml'
        config.write_text(f'http_bind_addr = "127.0.0.1:{port}"\nenable_relay = true\nenable_metrics = false\nenable_quic_addr_discovery = false\n')
        profile = args.output_dir/'relay.sb'
        profile.write_text(f'(version 1)(allow default)(deny network*)'
                           f'(allow network-bind network-inbound (local tcp "localhost:{port}"))')
        assert digest(args.relay_bin) == args.relay_sha256, 'relay changed since validation'
        log = (args.output_dir/'relay.log').open('a')
        self.logs.append(log)
        env = dict(HOME=str(args.output_dir), PATH='/usr/bin:/bin', TMPDIR=str(args.output_dir))
        self.process = subprocess.Popen(['/usr/bin/sandbox-exec', '-f', str(profile),
                                        str(args.relay_bin), '--config-path', str(config)],
                                       env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        process = self.process
        def listening():
            assert process.poll() is None, 'relay exited'
            result = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-p', str(process.pid), '-i'],
                                    text=True, capture_output=True, timeout=5)
            return result.stdout if relay_sockets(result.stdout, port) else None
        observed = wait_for(listening, 'exclusive relay TCP listener', 10)
        self.events.append(dict(phase='relay-listener', pid=self.process.pid, lsof=observed,
                                config=config.read_text(), profile=profile.read_text()))
        (args.output_dir/'relay-owner.json').write_text(json.dumps(self.events, indent=2)+'\n')
        return self.process.pid


def guard_controls():
    denied = []
    for family, address in ((socket.AF_INET, '1.1.1.1'), (socket.AF_INET6, '2606:4700:4700::1111')):
        for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            try:
                probe = socket.socket(family, kind)
            except OSError as exc:
                if family == socket.AF_INET6 and exc.errno == errno.EAFNOSUPPORT:
                    denied.append(dict(address=address, unsupported=True))
                    continue
                raise
            with probe:
                probe.settimeout(1)
                try:
                    if kind == socket.SOCK_STREAM:
                        probe.connect((address, 443))
                    else:
                        probe.sendto(b'guard', (address, 53))
                except OSError as exc:
                    assert exc.errno == errno.EPERM, exc
                    denied.append(dict(address=address, kind=kind, errno=exc.errno))
                else:
                    raise AssertionError('external network guard failed')
    for family, local in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
        try:
            listener = socket.socket(family)
        except OSError as exc:
            if family == socket.AF_INET6 and exc.errno == errno.EAFNOSUPPORT:
                continue
            raise
        with listener:
            listener.bind((local, 0))
            listener.listen()
            with socket.create_connection(listener.getsockname()[:2], timeout=1):
                accepted, _ = listener.accept()
                accepted.close()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.sendto(b'guard', ('224.0.0.251', 5353))
        except OSError as exc:
            assert exc.errno == errno.EPERM, exc
        else:
            raise AssertionError('mDNS guard failed')
    return dict(external_denials=denied, loopback_positive=True, mdns_denied=True)


class Fixture:
    def __init__(self, args, root):
        self.args, self.root = args, root
        self.children, self.logs, self.rpcs = [], [], []
        self.receipts = []
        self.tools = root / 'tools'
        self.tools.mkdir()
        self.trace = root / 'executed'
        self.env = dict(HOME=str(root), USERPROFILE=str(root), USER='fixture',
                        PATH=str(self.tools), TMPDIR=str(root), TRACE=str(self.trace),
                        CLAUDE_CONFIG_DIR=str(root/'claude'), CODEX_HOME=str(root/'codex'),
                        REASON_NETWORK_NO_PROMPT='1', REASON_NETWORK_NO_TRAY='1',
                        REASON_NETWORK_NO_MDNS='1', REASON_NETWORK_NO_SERVICE='1')
        for name in AGENTS:
            self.env[f'REASON_NETWORK_{name.upper()}_BIN'] = str(root/'absent'/name)
        for name in ('REASON_NETWORK_REASON_BIN', 'TINCAN_REASON_BIN', 'REASON_BIN'):
            self.env[name] = str(root/'absent/reason')

    def record(self, phase, **data):
        self.receipts.append(dict(phase=phase, **data))
        (self.root/'receipts.json').write_text(json.dumps(self.receipts, indent=2)+'\n')

    def spawn(self, command, name, env=None):
        log = (self.root/f'{name}.log').open('a')
        self.logs.append(log)
        process = subprocess.Popen(command, env=self.env if env is None else env,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        self.children.append(process)
        self.record('spawn', name=name, pid=process.pid, command=command)
        return process

    def stop(self, process):
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def cleanup(self):
        for rpc in self.rpcs:
            rpc.close()
        for process in reversed(self.children):
            self.stop(process)
        for log in self.logs:
            log.close()
        self.record('cleanup', children=[dict(pid=p.pid, exit_code=p.returncode) for p in self.children])
        assert all(p.poll() is not None for p in self.children)

    def no_execution(self):
        assert not self.trace.exists(), self.trace.read_text() if self.trace.exists() else ''

    def sentinel_controls(self):
        sentinel = self.root/'.local/bin/claude'
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE"\nexit 73\n')
        sentinel.chmod(0o755)
        state = self.state('control')
        env = self.env | dict(REASON_NETWORK_HOME=str(state))
        command = [str(self.args.binary), 'setup', '--dry-run', '--no-service']
        first = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
        assert first.returncode == 0, first.stderr
        self.no_execution()
        del env['REASON_NETWORK_CLAUDE_BIN']
        second = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
        assert second.returncode == 0, second.stderr
        assert 'mcp get reason-network' in self.trace.read_text()
        self.record('sentinel-controls', negative=first.returncode, positive=self.trace.read_text())
        self.trace.unlink()
        sentinel.unlink()

    def state(self, name):
        state = self.root/name
        state.mkdir()
        (state/'config.toml').write_text('reason = true\ntray = false\nlan = false\nshare_unmanaged = false\n')
        return state

    def start(self, state):
        env = self.env | dict(REASON_NETWORK_HOME=str(state), REASON_NETWORK_MACHINE=state.name)
        process = self.spawn([str(self.args.binary), 'daemon'], state.name, env)
        def connect():
            assert process.poll() is None, f'daemon exited: {state}'
            try:
                return Rpc(state)
            except (FileNotFoundError, ConnectionRefusedError):
                return None
        rpc = wait_for(connect, 'daemon IPC', 10)
        self.rpcs.append(rpc)
        return process, rpc

    def relay(self, port):
        pid = self.relay_control('start')
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            pass
        self.record('relay-started', pid=pid, port=port)

    def relay_control(self, op):
        channel = self.args.control
        channel.sendall(op.encode()+b'\n')
        reply = b''
        while not reply.endswith(b'\n'):
            chunk = channel.recv(4096)
            if not chunk:
                raise RuntimeError('relay supervisor disconnected')
            reply += chunk
        data = json.loads(reply)
        assert data['ok'], data
        return data.get('pid')

    def register(self, rpc, name):
        return rpc.call('register', session=dict(key=f'fixture:{name}', agent='fixture',
                        cwd=str(self.root), agent_session_id=name, tier='pull', name=name))

    def db(self, state, query, params=()):
        with sqlite3.connect(f'file:{state / "network.db"}?mode=ro', uri=True) as db:
            return db.execute(query, params).fetchall()

    def team_metadata(self, state):
        return self.db(state, "SELECT value FROM kv WHERE key = 'team'")

    def rejected(self, rpc, op, **fields):
        try:
            rpc.call(op, **fields)
        except RuntimeError as exc:
            self.record('rejected', op=op, fields=fields, error=str(exc))
        else:
            raise AssertionError(f'{op} unexpectedly accepted {fields}')

    def presence(self, ra, rb, relay):
        def connected():
            teams = [rpc.call('team') for rpc in (ra, rb)]
            directories = [rpc.call('who', all=True) for rpc in (ra, rb)]
            self.record('presence-observation', teams=teams, directories=directories)
            return (all(t['relay'] == relay and t['relay_connected'] is True and
                        len(t['machines']) == 2 and all(m['online'] for m in t['machines']) for t in teams)
                    and all(any(s['address'] == address for s in d['sessions'])
                            for d, address in zip(directories, ('bob/receiver', 'alice/sender'))))
        wait_for(connected, 'two durable members and bidirectional session presence', 30)

    def message(self, sender, receiver, state, source, target, receiver_key, phase):
        body = f'ordinary fixture {phase} {uuid.uuid4().hex}'
        sent = sender.call('send', **{'from': source, 'to': target, 'body': body})
        assert len(sent['ids']) == 1, sent
        mid = sent['ids'][0]
        def received():
            inbox = receiver.call('inbox', key=receiver_key, peek=True)
            return next((m for m in inbox['messages'] if m['id'] == mid and m['body'] == body), None)
        message = wait_for(received, 'receiver inbox ID/body')
        wait_for(lambda: not self.db(state, 'SELECT id FROM outbox WHERE id = ?', (mid,)), 'sender outbox settled')
        # Pull-session inbox admission is acknowledged as "queued"; this is
        # distinct from a transport queue awaiting peer acknowledgement.
        recipient = sent['recipients'][0]
        assert recipient['state'] == 'queued', sent
        assert recipient['note'] == 'queued: this agent only sees it when it checks its inbox', sent
        self.record('message', label=phase, send=sent, received=message, outbox_settled=True)

    def exchange(self, ra, rb, a, b, relay, phase):
        self.register(ra, 'sender')
        self.register(rb, 'receiver')
        self.presence(ra, rb, relay)
        self.message(ra, rb, a, 'fixture:sender', 'bob/receiver', 'fixture:receiver', phase+'-ab')
        self.message(rb, ra, b, 'fixture:receiver', 'alice/sender', 'fixture:sender', phase+'-ba')
        self.no_execution()

    def run(self, trap_present):
        if trap_present:
            trap = self.tools/'reason'
            trap.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE"\nexit 73\n')
            trap.chmod(0o755)
            for name in ('REASON_NETWORK_REASON_BIN', 'TINCAN_REASON_BIN', 'REASON_BIN'):
                self.env[name] = str(trap)
        self.sentinel_controls()
        port = self.args.relay_port
        relay = f'http://127.0.0.1:{port}'
        self.relay(port)
        a, b = self.state('a'), self.state('b')
        pa, ra = self.start(a)
        if self.args.fault == 'failure':
            raise AssertionError('injected cleanup failure')
        if self.args.fault == 'timeout':
            time.sleep(self.args.timeout + 10)
        for url in ('not a relay', 'http://127.0.0.1:1'):
            self.rejected(ra, 'create_team', name='fixture-team', person='alice', relay=url)
            assert not self.team_metadata(a), 'failed create persisted metadata'
        created = ra.call('create_team', name='fixture-team', person='alice', relay=relay)
        assert created['relay'] == relay
        pa.wait(timeout=10)
        pa, ra = self.start(a)
        before = self.team_metadata(a)
        for url in ('not a relay', 'http://127.0.0.1:1'):
            self.rejected(ra, 'set_relay', url=url)
            assert self.team_metadata(a) == before, 'failed set replaced healthy metadata'
            assert ra.call('team')['relay'] == relay
        ticket = ra.call('link', new=False)['ticket']
        assert ticket.startswith('tincan1') and '://' not in ticket
        pb, rb = self.start(b)
        assert rb.call('join', ticket=ticket, person='bob')['relay'] == relay
        pb.wait(timeout=10)
        pb, rb = self.start(b)
        self.exchange(ra, rb, a, b, relay, 'initial')
        roster = [self.team_metadata(state) for state in (a, b)]
        for phase, restart_a, restart_b in (('restart-a', True, False), ('restart-b', False, True),
                                           ('restart-both', True, True)):
            if restart_a:
                self.stop(pa)
                pa, ra = self.start(a)
            if restart_b:
                self.stop(pb)
                pb, rb = self.start(b)
            assert [self.team_metadata(state) for state in (a, b)] == roster
            self.exchange(ra, rb, a, b, relay, phase)
        self.relay_control('stop')
        # Existing direct connections may survive: observe, never count this as relay delivery.
        self.record('relay-down-existing-paths', teams=[rpc.call('team') for rpc in (ra, rb)])
        self.stop(pa)
        self.stop(pb)
        pa, ra = self.start(a)
        pb, rb = self.start(b)
        self.register(ra, 'sender')
        self.register(rb, 'receiver')
        assert all(rpc.call('team')['relay'] == relay for rpc in (ra, rb))
        assert [self.team_metadata(state) for state in (a, b)] == roster
        self.record('relay-down-restarted', teams=[rpc.call('team') for rpc in (ra, rb)],
                    ipc_available=True, retained_metadata=True)
        self.relay(port)
        self.exchange(ra, rb, a, b, relay, 'relay-recovered')
        self.no_execution()
        self.record('passed', trap_present=trap_present, no_ticket_replay=True,
                    limitation='B-local only; link may upgrade to direct; no forced-relay/cross-NAT proof')
        self.relay_control('stop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--relay-bin', type=Path, required=True)
    parser.add_argument('--relay-sha256', required=True)
    parser.add_argument('--readiness-manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='new private receipt directory')
    parser.add_argument('--scratch-dir', type=Path, required=True, help='private short-path temporary parent')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--fault', choices=('failure', 'timeout'), help=argparse.SUPPRESS)
    parser.add_argument('--guarded', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--control-fd', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--relay-port', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if not __debug__:
            raise Blocked('Python optimization disables assertions; run without -O/PYTHONOPTIMIZE')
        validate_relay(args.relay_bin, args.relay_sha256, args.readiness_manifest)
        if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
            raise Blocked('macOS sandbox-exec required; other platforms remain unverified')
        args.binary = args.binary.resolve(strict=True)
        if (args.timeout < 1 or not args.output_dir.is_absolute() or
                not args.scratch_dir.is_absolute() or not args.scratch_dir.is_dir()):
            raise Blocked('positive timeout and absolute private output directory required')
        if not args.guarded:
            args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
            owner = RelayOwner(args)
            parent, child = socket.socketpair()
            profile = ('(version 1)(allow default)(deny network-outbound)'
                       '(allow network-outbound (remote unix-socket))'
                       '(allow network-outbound (remote ip "localhost:*"))')
            command = ['/usr/bin/sandbox-exec', '-p', profile, sys.executable,
                       str(Path(__file__).resolve()), *sys.argv[1:], '--guarded',
                       '--control-fd', str(child.fileno()), '--relay-port', str(owner.port)]
            env = dict(HOME=str(args.output_dir), PATH='/usr/bin:/bin', TMPDIR=str(args.scratch_dir))
            process = subprocess.Popen(command, env=env, start_new_session=True,
                                       pass_fds=(child.fileno(),))
            child.close()
            deadline = time.monotonic()+args.timeout
            result = 1
            pending = b''
            try:
                while process.poll() is None:
                    if time.monotonic() > deadline:
                        result = 124
                        break
                    if select.select([parent], [], [], .1)[0]:
                        chunk = parent.recv(4096)
                        if not chunk:
                            break
                        pending += chunk
                        while b'\n' in pending:
                            op, pending = pending.split(b'\n', 1)
                            if op == b'start':
                                reply = dict(ok=True, pid=owner.start())
                            elif op == b'stop':
                                owner.stop()
                                reply = dict(ok=True)
                            else:
                                raise AssertionError('invalid relay supervisor operation')
                            parent.sendall((json.dumps(reply)+'\n').encode())
                if result != 124:
                    result = process.wait(timeout=5)
            finally:
                owner.stop()
                parent.close()
                # Own the entire runner process group, including timeout/failure descendants.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            (args.output_dir/'runner.json').write_text(json.dumps(dict(exit_code=result, guard=profile,
                binary_sha256=digest(args.binary), relay_sha256=args.relay_sha256,
                process_group=process.pid), indent=2)+'\n')
            return result
        def interrupted(_signum, _frame):
            raise KeyboardInterrupt('runner terminated; preserving owned-child evidence')
        signal.signal(signal.SIGTERM, interrupted)
        args.control = socket.socket(fileno=args.control_fd)
        args.control.settimeout(20)
        controls = guard_controls()
        (args.output_dir/'guard.json').write_text(json.dumps(controls, indent=2)+'\n')
        # Short scratch roots avoid AF_UNIX path limits; retain logs/DBs privately before removal.
        for present in (False, True):
            with tempfile.TemporaryDirectory(prefix='p3-', dir=args.scratch_dir) as temp:
                fixture = Fixture(args, Path(temp))
                try:
                    fixture.run(present)
                finally:
                    fixture.cleanup()
                    shutil.copytree(fixture.root, args.output_dir/('trap' if present else 'absent'),
                                    ignore=shutil.ignore_patterns('*.sock'))
        print('PASS B-local: absent/trap, restart, outage; no real-worker or C0 claim')
        return 0
    except Blocked as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
