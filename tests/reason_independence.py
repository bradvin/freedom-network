#!/usr/bin/env python3
"""Isolated P2 process regressions; no real agents, services or internet access.

macOS: python3 tests/reason_independence.py --binary target/debug/reason-network
For a local peer transport attempt also pass --transport.
The parent reexecutes under sandbox-exec, denying outbound IP except loopback
only. TCP/UDP denial controls must pass before fixtures.
This is same-host process evidence, NOT cross-machine/custom-relay acceptance.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--binary", type=Path, required=True)
PARSER.add_argument("--transport", action="store_true", help="attempt same-host peer admission under loopback-only guard")
PARSER.add_argument("--guarded", action="store_true", help=argparse.SUPPRESS)
ARGS, REST = PARSER.parse_known_args()
BINARY = ARGS.binary.resolve()


def guard():
    if sys.platform != "darwin":
        raise SystemExit("This harness requires macOS sandbox-exec; other OS runtime coverage is pending")
    if not ARGS.guarded:
        profile = '(version 1)(allow default)(deny network-outbound)'
        profile += '(allow network-outbound (remote unix-socket))'
        profile += '(allow network-outbound (remote ip "localhost:*"))'
        raise SystemExit(subprocess.call(["/usr/bin/sandbox-exec", "-p", profile,
                                         sys.executable, str(Path(__file__).resolve()),
                                         *sys.argv[1:], "--guarded"]))
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(socket.AF_INET, kind) as probe:
            probe.settimeout(1)
            try:
                if kind == socket.SOCK_STREAM:
                    probe.connect(("1.1.1.1", 443))
                else:
                    probe.sendto(b"guard", ("1.1.1.1", 53))
            except OSError as exc:
                if exc.errno != errno.EPERM:
                    raise SystemExit(f"guard must deny with EPERM, got {exc}")
            else:
                raise SystemExit("external network guard failed")
    print("GUARD PASS: external TCP and UDP denied with EPERM", flush=True)


class Rpc:
    def __init__(self, state):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(45)
        try:
            self.sock.connect(str(state / "network.sock"))
        except OSError:
            self.sock.close()
            raise
        self.stream = self.sock.makefile("rwb")
        self.seq = 0

    def close(self):
        self.stream.close()
        self.sock.close()

    def call(self, op, **fields):
        self.seq += 1
        self.stream.write((json.dumps(dict(id=self.seq, op=op, **fields)) + "\n").encode())
        self.stream.flush()
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("daemon disconnected")
            reply = json.loads(line)
            if reply.get("id") == self.seq:
                if reply.get("error"):
                    raise RuntimeError(reply["error"])
                return reply.get("result")


class ReasonIndependence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p2-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.trace = self.root / "executed"
        self.processes = []
        self.addCleanup(self.stop_all)
        # An allowlisted environment and tools-only PATH cannot discover real agents.
        self.env = dict(HOME=str(self.root), USERPROFILE=str(self.root), USER="fixture",
                        PATH=str(self.tools), TMPDIR=str(self.root), TRACE=str(self.trace),
                        CLAUDE_CONFIG_DIR=str(self.root / "claude"),
                        CODEX_HOME=str(self.root / "codex"),
                        REASON_NETWORK_NO_PROMPT="1", REASON_NETWORK_NO_TRAY="1",
                        REASON_NETWORK_NO_MDNS="1", REASON_NETWORK_NO_SERVICE="1")

    def trap_reason(self):
        trap = self.tools / "reason"
        trap.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE"\nexit 73\n')
        trap.chmod(0o755)
        self.env["REASON_NETWORK_REASON_BIN"] = str(trap)
        self.env["TINCAN_REASON_BIN"] = str(trap)

    def state(self, who, legacy=True):
        state = self.root / who
        state.mkdir()
        (state / "config.toml").write_text(
            f"reason = {str(legacy).lower()}\ntray = false\nlan = false\nshare_unmanaged = false\n")
        return state

    def start(self, state, binary=BINARY):
        env = self.env | dict(REASON_NETWORK_HOME=str(state), REASON_NETWORK_MACHINE=state.name)
        log = open(state / "process.log", "a+")
        self.addCleanup(log.close)
        process = subprocess.Popen([str(binary), "daemon"], env=env,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        self.processes.append(process)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail((state / "process.log").read_text())
            try:
                rpc = Rpc(state)
                self.addCleanup(rpc.close)
                return process, rpc
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.05)
        self.fail("daemon did not listen: " + (state / "process.log").read_text())

    def stop_all(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def assert_no_reason(self):
        self.assertFalse(self.trace.exists(), self.trace.read_text() if self.trace.exists() else "")

    def register(self, rpc, name, agent="fixture", tier="pull"):
        return rpc.call("register", session=dict(key=f"{agent}:{name}", agent=agent,
                        cwd=str(self.root), agent_session_id=name, tier=tier, name=name))

    def test_missing_reason_legacy_config_keeps_local_messaging(self):
        state = self.state("a")
        _, rpc = self.start(state)
        self.register(rpc, "sender")
        self.register(rpc, "receiver")
        rpc.call("send", **{"from": "fixture:sender", "to": "fixture/receiver", "body": "offline fixture"})
        inbox = rpc.call("inbox", key="fixture:receiver")
        self.assertIn("offline fixture", json.dumps(inbox))
        self.assertIn("Reason cloud integration is disabled", (state / "process.log").read_text())
        self.assert_no_reason()

    def test_trap_reason_legacy_config_cannot_discover_cloud_sessions(self):
        self.trap_reason()
        state = self.state("a")
        _, rpc = self.start(state)
        self.register(rpc, "control")
        time.sleep(1)
        self.assert_no_reason()
        self.assertIn("Reason cloud integration is disabled", (state / "process.log").read_text())

    def test_managed_directory_cannot_spawn_workspace_relay(self):
        self.trap_reason()
        managed = self.root / ".reason" / "bin" / BINARY.name
        managed.parent.mkdir(parents=True)
        shutil.copy2(BINARY, managed)
        state = self.state("a", legacy=False)
        _, rpc = self.start(state, managed)
        self.register(rpc, "control")
        time.sleep(1)
        self.assert_no_reason()

    def test_reason_session_label_cannot_launch_cli_delivery(self):
        self.trap_reason()
        state = self.state("a", legacy=False)
        _, rpc = self.start(state)
        self.register(rpc, "sender")
        self.register(rpc, "oldcloud", agent="reason", tier="push")
        rpc.call("send", **{"from": "fixture:sender", "to": "fixture/oldcloud", "body": "untrusted message"})
        time.sleep(0.5)
        self.assert_no_reason()

    def test_setup_does_not_offer_reason_cloud_agent(self):
        self.trap_reason()
        state = self.state("a")
        result = subprocess.run([str(BINARY), "setup", "--dry-run", "--no-service"],
                                env=self.env | dict(REASON_NETWORK_HOME=str(state)),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Reason:", result.stdout + result.stderr)
        self.assertNotIn("lists your live Reason sessions", result.stdout + result.stderr)
        self.assert_no_reason()

    @unittest.skipUnless(ARGS.transport, "pass --transport to attempt loopback-only QUIC process coverage")
    def test_standalone_raw_ticket_admission_and_peer_messaging(self):
        for present in (False, True):
            with self.subTest(reason_present=present):
                if present:
                    self.trap_reason()
                a = self.state("c" if present else "a")
                b = self.state("d" if present else "b")
                pa, ra = self.start(a)
                created = ra.call("create_team", name="fixture-team", person="alice", relay=None)
                self.assertEqual(created["name"], "fixture-team")
                pa.wait(timeout=10)
                _, ra = self.start(a)
                ticket = ra.call("link", new=False)["url"]
                self.assertTrue(ticket.startswith("tincan1"), ticket)
                self.assertNotIn("://", ticket)
                pb, rb = self.start(b)
                joined = rb.call("join", ticket=ticket, person="bob")
                self.assertEqual(joined["name"], "fixture-team")
                pb.wait(timeout=10)
                _, rb = self.start(b)
                self.register(ra, "sender")
                self.register(rb, "receiver")
                deadline = time.monotonic() + 15
                peers = None
                while time.monotonic() < deadline:
                    peers = ra.call("who", all=True)
                    if "bob/receiver" in json.dumps(peers):
                        break
                    time.sleep(0.1)
                else:
                    self.fail("peer session not announced: " + json.dumps(peers))
                ra.call("send", **{"from": "fixture:sender", "to": "bob/receiver", "body": "ordinary peer fixture"})
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    inbox = rb.call("inbox", key="fixture:receiver")
                    if "ordinary peer fixture" in json.dumps(inbox):
                        break
                    time.sleep(0.1)
                else:
                    self.fail("peer message not received")
                self.assert_no_reason()


if __name__ == "__main__":
    guard()
    unittest.main(argv=[__file__, *REST], verbosity=2)
