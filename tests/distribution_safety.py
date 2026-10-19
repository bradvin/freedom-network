#!/usr/bin/env python3
"""Offline distribution regression harness. Never downloads or installs a binary.

Run: python3 tests/distribution_safety.py [--binary target/debug/reason-network]
Optional: --powershell /path/to/pwsh executes the PowerShell guard as well.
Only temporary fixture executables are invoked; all writes stay in a private temp dir.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARSER = argparse.ArgumentParser()
PARSER.add_argument("--binary", type=Path)
PARSER.add_argument("--powershell", type=Path)
ARGS, REST = PARSER.parse_known_args()
BINARY = ARGS.binary.resolve() if ARGS.binary else None
POWERSHELL = ARGS.powershell.resolve() if ARGS.powershell else None


class DistributionSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="distribution-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.tools = self.home / "tools"
        self.tools.mkdir()
        self.trace = self.home / "executed"
        for tool in ("curl", "wget", "reason", "powershell", "pwsh", "reason-network", "tincan"):
            fake = self.tools / tool
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$TRACE"\nexit 73\n')
            fake.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("REASON_", "TINCAN_", "ARA_"))}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home),
                        PATH=str(self.tools) + os.pathsep + os.environ.get("PATH", ""),
                        TRACE=str(self.trace), REASON_NETWORK_HOME=str(self.home / "state"),
                        REASON_NETWORK_BIN_DIR=str(self.home / "installed"),
                        REASON_NETWORK_NO_PROMPT="1", REASON_NETWORK_NO_TRAY="1",
                        REASON_NETWORK_NO_MDNS="1", REASON_NETWORK_NO_SERVICE="1")

    def assert_blocked(self, command, overrides=None):
        env = self.env | (overrides or {})
        result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("disabled", (result.stdout + result.stderr).lower())
        self.assertFalse(self.trace.exists(), self.trace.read_text() if self.trace.exists() else "")
        self.assertFalse((self.home / "installed").exists())
        self.assertFalse((self.home / "state").exists(), "must fail before starting a daemon/migrating state")

    def test_shell_installer_rejects_all_distribution_inputs_before_io(self):
        cases = ({}, {"REASON_NETWORK_REPO": "reason-machines/reason-network"},
                 {"REASON_NETWORK_REPO": "bradvin/freedom-network", "REASON_NETWORK_VERSION": "v0.10.7"},
                 {"REASON_NETWORK_DOWNLOAD_BASE": "https://mirror.invalid/releases", "REASON_NETWORK_VERSION": "latest"},
                 {"REASON_NETWORK_VERSION": "v999.999.999"},
                 {"REASON_NETWORK_VERSION": "../invalid", "REASON_NETWORK_REPO": "unknown/publisher"},
                 {"REASON_NETWORK_DOWNLOAD_BASE": "file:///untrusted", "REASON_NETWORK_VERSION": "v1.0.0"},
                 {"REASON_NETWORK_NO_PROMPT": ""})
        for overrides in cases:
            for args in ([], ["init", "fixture", "--as", "fixture"], ["join", "fixture-code"]):
                with self.subTest(overrides=overrides, args=args):
                    self.assert_blocked(["/bin/sh", str(ROOT / "install.sh"), *args], overrides)

    def test_retired_entrypoints_preserve_existing_installation(self):
        installed = self.home / "installed"
        installed.mkdir()
        binary = installed / "reason-network"
        binary.write_bytes(b"existing binary fixture")
        commands = [[str(ROOT / "install.sh")]]
        if POWERSHELL:
            commands.append([str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive",
                             "-File", str(ROOT / "install.ps1")])
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(command, env=self.env, text=True, capture_output=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("disabled", (result.stdout + result.stderr).lower())
                self.assertEqual(binary.read_bytes(), b"existing binary fixture")
                self.assertEqual(sorted(p.name for p in installed.iterdir()), ["reason-network"])
                self.assertFalse(self.trace.exists())

    @unittest.skipUnless(POWERSHELL, "PowerShell unavailable; static coverage is not runtime coverage")
    def test_powershell_installer_rejects_overrides_before_io(self):
        for overrides in ({}, {"REASON_NETWORK_REPO": "reason-machines/reason-network"},
                          {"REASON_NETWORK_DOWNLOAD_BASE": "https://mirror.invalid", "REASON_NETWORK_VERSION": "v999"},
                          {"REASON_NETWORK_REPO": "unknown/publisher", "REASON_NETWORK_VERSION": "../invalid"}):
            with self.subTest(overrides=overrides):
                self.assert_blocked([str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
                                     str(ROOT / "install.ps1")], overrides)

    def test_powershell_guard_has_no_download_or_execution_path(self):
        lines = [line.strip() for line in (ROOT / "install.ps1").read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(len(lines), 1, "retired installer must contain only an unconditional throw")
        self.assertTrue(lines[0].startswith("throw "))
        self.assertIn("disabled", lines[0])

    @unittest.skipUnless(BINARY, "pass --binary after cargo build for CLI process coverage")
    def test_explicit_upgrade_fails_before_daemon_or_installer(self):
        for overrides in ({}, {"REASON_NETWORK_REPO": "reason-machines/reason-network"},
                          {"REASON_NETWORK_DOWNLOAD_BASE": "https://mirror.invalid"},
                          {"REASON_NETWORK_MANAGED": "1", "REASON_NETWORK_AUTO_UPDATE": "true"}):
            with self.subTest(overrides=overrides):
                self.assert_blocked([str(BINARY), "upgrade"], overrides)

    @unittest.skipUnless(BINARY, "pass --binary for legacy/managed path coverage")
    def test_upgrade_cannot_handoff_under_a_legacy_or_managed_name(self):
        assert BINARY is not None
        legacy = self.home / ".tincan"
        legacy.mkdir()
        marker = legacy / "tincan.db"
        marker.write_bytes(b"fixture state must not migrate")
        managed_dir = self.home / ".reason" / "bin"
        managed_dir.mkdir(parents=True)
        for target in (self.tools / "tincan", managed_dir / "reason-network"):
            shutil.copyfile(BINARY, target)
            target.chmod(0o755)
            self.assert_blocked([str(target), "upgrade"])
            self.assertEqual(marker.read_bytes(), b"fixture state must not migrate")

    @unittest.skipUnless(BINARY, "pass --binary for isolated daemon policy coverage")
    def test_daemon_refuses_old_update_opt_in_without_launching_updater(self):
        state = self.home / "state"
        state.mkdir()
        # No team, tray, local service, agent integration or transport is started.
        (state / "config.toml").write_text("auto_update = true\ntray = false\nreason = false\nlan = false\n")
        process = subprocess.Popen([str(BINARY), "daemon"], env=self.env,
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                process.communicate(timeout=2)
        finally:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=5)
        self.assertIn("auto_update is disabled", stderr, stdout + stderr)
        self.assertFalse(self.trace.exists(), self.trace.read_text() if self.trace.exists() else "")
        self.assertFalse((self.home / "installed").exists())

    def test_no_runtime_download_scripts_or_updater_survive(self):
        for relative in ("src/main.rs", "src/daemon/update.rs", "src/migrate.rs"):
            text = (ROOT / relative).read_text()
            for forbidden in ("releases/latest/download", "Command::new(\"curl\")", "keep_waiting_copy", "crate::installer"):
                self.assertNotIn(forbidden, text, relative)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *REST], verbosity=2)
