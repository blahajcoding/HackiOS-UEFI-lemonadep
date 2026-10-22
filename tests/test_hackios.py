#!/usr/bin/env python3
"""Host protocol, packaging and policy tests; never access a device."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Resources.Scripts import hackios_payload as hp


def entry(name, data):
    return struct.pack('<16sII', name.encode(), len(data), 0) + data + bytes(-len(data) % 16)


def container(body):
    return b'XNUP' + struct.pack('<I', len(body)) + body


def pe_image():
    data = bytearray(256)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, 0xAA64)
    struct.pack_into('<H', data, 88, 0x20B)
    struct.pack_into('<H', data, 156, 10)
    return bytes(data)


class PayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.runner = cls.base / 'parser'
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-g', '-O1', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
            '-fno-pie', '-no-pie', str(ROOT / 'tests/hackios_payload_host.c'),
            '-o', str(cls.runner)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.image = pe_image()
        self.good = container(entry('loader.efi', self.image) + bytes(24))
        self.manifest = self.base / 'loader.json'
        self.manifest.write_text(json.dumps({'board': 'lemonadep', 'storage_writes': False,
            'sha256': hashlib.sha256(self.image).hexdigest()}))

    def check_parser(self, data, expected):
        try:
            hp.parse_payload(data)
            valid = True
        except (ValueError, UnicodeError):
            valid = False
        self.assertEqual(valid, expected)
        path = self.base / 'case.bin'
        path.write_bytes(data)
        r = subprocess.run([str(self.runner), str(path)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0 if expected else 1, r.stderr)

    def test_valid_and_truncations(self):
        self.check_parser(self.good, True)
        for length in range(len(self.good)):
            with self.subTest(length=length):
                self.check_parser(self.good[:length], False)

    def test_malformed_entries(self):
        for body in [bytes(24), entry('kernel', b'k') + bytes(24),
                entry('loader.efi', b'') + bytes(24),
                entry('loader.efi', self.image),
                entry('loader.efi', self.image) * 2 + bytes(24),
                entry('loader.efi', self.image) + bytes(25)]:
            self.check_parser(container(body), False)
        for offset, value in [(4, 0xffffffff), (24, 0xffffffff), (28, 1)]:
            bad = bytearray(self.good)
            struct.pack_into('<I', bad, offset, value)
            self.check_parser(bytes(bad), False)
        self.check_parser(b'BAD!' + self.good[4:], False)

    def test_loader_manifest_and_architecture(self):
        hp.validate_loader(self.good, self.manifest)
        for field, value in [('board', 'redwood'), ('storage_writes', True), ('sha256', 'bad')]:
            manifest = json.loads(self.manifest.read_text())
            manifest[field] = value
            self.manifest.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): hp.validate_loader(self.good, self.manifest)
            self.setUp()
        bad_image = bytearray(self.image)
        struct.pack_into('<H', bad_image, 68, 0x8664)
        self.manifest.write_text(json.dumps({'board': 'lemonadep', 'storage_writes': False,
            'sha256': hashlib.sha256(bad_image).hexdigest()}))
        with self.assertRaises(ValueError):
            hp.validate_loader(container(entry('loader.efi', bad_image) + bytes(24)), self.manifest)

    def test_no_board_or_firmware_fallback(self):
        with self.assertRaisesRegex(ValueError, 'only enabled'):
            hp.check_inputs(self.base, 'redwood', self.good, self.manifest)
        with self.assertRaisesRegex(ValueError, 'target Resources'):
            hp.check_inputs(self.base, 'lemonadep', self.good, self.manifest)
        dtb = self.base / 'Resources/DTBs/lemonadep.dtb'
        dtb.parent.mkdir(parents=True, exist_ok=True)
        dtb.write_bytes(b'\xd0\x0d\xfe\xed')
        # Use the real include lists against an empty Binaries directory.
        import shutil
        shutil.copytree(ROOT / 'Platforms/OnePlus/lemonadepPkg/Include',
            self.base / 'Platforms/OnePlus/lemonadepPkg/Include', dirs_exist_ok=True)
        with self.assertRaisesRegex(ValueError, 'missing target firmware'):
            hp.check_inputs(self.base, 'lemonadep', self.good, self.manifest)

    def test_packaging_header(self):
        shim = bytearray(128)
        struct.pack_into('<Q', shim, 8, hp.FD_BASE)
        struct.pack_into('<Q', shim, 16, 128 + hp.FD_SIZE + ((len(self.good) + 15) & ~15))
        shim[56:60] = b'ARM\x64'
        out = hp.combine_image(bytes(shim), bytes(hp.FD_SIZE), self.good)
        self.assertEqual(out[128 + hp.FD_SIZE:][:len(self.good)], self.good)
        with self.assertRaises(ValueError): hp.combine_image(shim, b'', self.good)
        shim[16] ^= 1
        with self.assertRaises(ValueError): hp.combine_image(shim, bytes(hp.FD_SIZE), self.good)

    def test_opt_in_and_no_raw_log_writes(self):
        source = ROOT / 'Silicon/Silicium/SiliciumPkg/Library/BootManagerLib/XnuLoader.c'
        text = source.read_text()
        self.assertIn('#if defined(HACKIOS_ENABLE) && HACKIOS_ENABLE', text)
        for forbidden in ['WriteBlocks', 'FlushBlocks', 'ResetSystem', 'LogPersistence']:
            self.assertNotIn(forbidden, text)

    def test_memory_reservation_preserves_extent(self):
        import re
        source = (ROOT / 'Platforms/OnePlus/lemonadepPkg/Library/MemoryMapLib/MemoryMapLib.c').read_text()
        # Preprocess the real conditional map without pulling in firmware headers.
        source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
        maps = []
        for enabled in (0, 1):
            r = subprocess.run(['cc', '-E', '-P', '-x', 'c', f'-DHACKIOS_ENABLE={enabled}', '-'],
                input=source, capture_output=True, text=True, check=True)
            rows = [(name, int(base, 16), int(size, 16), kind)
                for name, base, size, kind in re.findall(
                    r'\{"([^"]+)",\s*(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+),[^\n]*?,\s*(Conv|Reserv|BsData|RtData),', r.stdout)]
            maps.append(rows)
        self.assertFalse(any(name == 'XNU Payload' for name, *_ in maps[0]))
        reserved = [row for row in maps[1] if row[0] == 'XNU Payload']
        self.assertEqual(reserved, [('XNU Payload', hp.PAYLOAD_BASE, hp.PAYLOAD_MAX, 'Reserv')])
        high = [row for row in maps[1] if row[0].startswith('RAM B2 High') or row[0] == 'XNU Payload']
        high.sort(key=lambda row: row[1])
        self.assertEqual(high[0][1], 0xe7100000)
        for left, right in zip(high, high[1:]): self.assertEqual(left[1] + left[2], right[1])
        self.assertEqual(high[-1][1] + high[-1][2], 0x280000000)
        for name, base, size, kind in maps[1]:
            if kind == 'Conv':
                self.assertFalse(base < hp.PAYLOAD_BASE + hp.PAYLOAD_MAX and hp.PAYLOAD_BASE < base + size, name)


if __name__ == '__main__':
    unittest.main()
