#!/usr/bin/env python3
"""Execute the actual AArch64 shim in Unicorn, without phone hardware.

Needs clang + llvm-objcopy, or ZIG=/path/to/zig, plus Python unicorn.
"""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from test_hackios import ROOT, container, entry
try:
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_PC
except ImportError:
    Uc = None


@unittest.skipUnless(Uc, 'install Python unicorn to execute BootShim')
class ShimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        zig = os.environ.get('ZIG')
        if zig:
            cls.cc = [zig, 'cc', '-target', 'aarch64-freestanding']
            cls.objcopy = [zig, 'objcopy']
        elif shutil.which('clang') and shutil.which('llvm-objcopy'):
            cls.cc = ['clang', '--target=aarch64-linux-gnu']
            cls.objcopy = ['llvm-objcopy']
        else:
            raise unittest.SkipTest('AArch64 assembler/objcopy unavailable')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.payload = container(entry('loader.efi', b'test EFI bytes') + bytes(24))
        cls.compile(len(cls.payload), True)
        cls.shim = (cls.base / 'shim.bin').read_bytes()
        symbols = subprocess.check_output(['readelf', '-sW', str(cls.base / 'shim.o')], text=True)
        cls.dead = int(next(line.split()[1] for line in symbols.splitlines()
                           if line.split() and line.split()[-1] == '_Dead'), 16)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def compile(cls, size, enabled):
        cmd = cls.cc + ['-g0', '-c', str(ROOT / 'BootShim/BootShim.S'),
            '-o', str(cls.base / 'shim.o'), '-DREQUIRES_KERNEL_HEADER=1',
            '-DFD_BASE=0x9fc00000', '-DFD_SIZE=0x300000',
            f'-DHACKIOS_ENABLE={int(enabled)}', f'-DXNUP_SIZE={size}',
            '-DPAYLOAD_BASE=0xf0000000', '-DPAYLOAD_MAX=0x4000000']
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            subprocess.run(cls.objcopy + ['-O', 'binary', str(cls.base / 'shim.o'),
                           str(cls.base / 'shim.bin')], check=True)
        return r

    def execute(self, source, payload=None, blocked=False):
        fd, dest = 0x9fc00000, 0xf0000000
        firmware = b'\x5a' * 0x300000
        payload = payload if payload is not None else self.payload
        blob = self.shim + firmware + payload + bytes(-len(payload) % 16)
        ranges = sorted([(source & ~4095, (source + len(blob) + 4095) & ~4095),
                         (fd, fd + len(firmware)), (dest, dest + 65536)])
        merged = []
        for lo, hi in ranges:
            if merged and lo <= merged[-1][1]: merged[-1][1] = max(hi, merged[-1][1])
            else: merged.append([lo, hi])
        uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        for lo, hi in merged: uc.mem_map(lo, hi - lo)
        uc.mem_write(source, blob)
        before = bytes(uc.mem_read(fd, len(firmware)))
        stops = []
        def hook(emulator, address, size, user_data):
            if address in (fd, source + self.dead):
                stops.append(address)
                emulator.emu_stop()
        uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(source, 0, count=2000000)
        self.assertEqual(stops, [source + self.dead] if blocked else [fd])
        if blocked:
            self.assertEqual(bytes(uc.mem_read(fd, len(firmware))), before)
        else:
            self.assertEqual(bytes(uc.mem_read(fd, len(firmware))), firmware)
            copied = bytes(uc.mem_read(dest, len(payload)))
            if payload[:4] != b'XNUP': self.assertEqual(copied[:8], bytes(8))
            else: self.assertEqual(copied, payload)

    def test_header_and_copy(self):
        self.assertEqual(struct.unpack_from('<Q', self.shim, 16)[0],
            len(self.shim) + 0x300000 + ((len(self.payload) + 15) & ~15))
        self.execute(0x82000000)

    def test_already_at_fd(self):
        self.execute(0x9fc00000 - len(self.shim))

    def test_fd_source_overlap_refused(self):
        self.execute(0x9fc00000 - 65536, blocked=True)

    def test_payload_source_overlap_refused(self):
        self.execute(0xf0000000 - 65536, blocked=True)

    def test_bad_magic_clears_header_and_continues(self):
        self.execute(0x82000000, b'BAD!' + self.payload[4:])

    def test_oversized_build_rejected(self):
        self.assertNotEqual(self.compile(0x4000001, True).returncode, 0)

    def test_disabled_build(self):
        self.assertEqual(self.compile(0, False).returncode, 0)
        self.assertEqual(struct.unpack_from('<Q', (self.base / 'shim.bin').read_bytes(), 16)[0], 0x300000)


if __name__ == '__main__':
    unittest.main()
