#!/usr/bin/env python3
"""Fast safety regressions for the optional operator connectivity runner."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import operator_connectivity as harness


class Prerequisites(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'relay'
        self.binary.write_bytes(b'not executable: validation must never execute it')
        self.digest = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        self.receipt = self.root / 'readiness.json'
        self.data = dict(schema=1, status='passed', crate='iroh-relay', version='1.3.0',
                         archive_sha256=harness.ARCHIVE_SHA256,
                         packaged_lock_sha256=harness.LOCK_SHA256,
                         binary_sha256=self.digest, offline_build=True,
                         outbound_denied_build=True, loopback_listener_verified=True,
                         metrics_disabled=True, quic_disabled=True)

    def validate(self):
        self.receipt.write_text(json.dumps(self.data))
        return harness.validate_relay(self.binary, self.digest, self.receipt)

    def test_valid_manifest_does_not_execute_binary(self):
        self.assertEqual(self.validate(), self.data)

    def test_missing_manifest_is_blocked(self):
        with self.assertRaises(harness.Blocked):
            harness.validate_relay(self.binary, self.digest, self.receipt)

    def test_wrong_hash_is_blocked(self):
        self.binary.write_bytes(b'changed')
        with self.assertRaises(harness.Blocked):
            self.validate()

    def test_each_required_field_fails_closed(self):
        for field in list(self.data):
            with self.subTest(field=field):
                original = self.data.pop(field)
                try:
                    with self.assertRaises(harness.Blocked):
                        self.validate()
                finally:
                    self.data[field] = original

    def test_false_readiness_is_blocked(self):
        for field in ('offline_build', 'outbound_denied_build', 'loopback_listener_verified',
                      'metrics_disabled', 'quic_disabled'):
            self.data[field] = False
            with self.assertRaises(harness.Blocked):
                self.validate()
            self.data[field] = True

    def test_relative_binary_path_is_blocked(self):
        with self.assertRaises(harness.Blocked):
            harness.validate_relay(Path('relay'), self.digest, self.receipt)

    def test_wrong_version_or_source_is_blocked(self):
        for field in ('version', 'archive_sha256', 'packaged_lock_sha256'):
            original = self.data[field]
            self.data[field] = 'wrong'
            with self.assertRaises(harness.Blocked):
                self.validate()
            self.data[field] = original


class SocketOwnership(unittest.TestCase):
    def test_listener_with_accepted_connections(self):
        output = ('header\nrelay 1 TCP 127.0.0.1:1234 (LISTEN)\n'
                  'relay 1 TCP 127.0.0.1:1234->127.0.0.1:4321 (ESTABLISHED)\n')
        self.assertTrue(harness.relay_sockets(output, 1234))

    def test_absent_listener_is_pending(self):
        self.assertFalse(harness.relay_sockets('header\n', 1234))

    def test_extra_or_wildcard_sockets_rejected(self):
        for extra in ('TCP *:1234 (LISTEN)', 'TCP 127.0.0.1:9090 (LISTEN)',
                      'UDP *:1234', 'TCP 127.0.0.1:1234->1.1.1.1:443 (ESTABLISHED)',
                      'TCP [::1]:1234 (LISTEN)'):
            with self.subTest(extra=extra), self.assertRaises(AssertionError):
                harness.relay_sockets('header\nrelay TCP 127.0.0.1:1234 (LISTEN)\n'+extra, 1234)


if __name__ == '__main__':
    unittest.main(verbosity=2)
