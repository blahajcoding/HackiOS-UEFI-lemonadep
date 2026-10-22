#!/usr/bin/env python3
"""Host checks for HackiOS XNUP; no device access or firmware fallback."""
import hashlib
import json
import struct
from pathlib import Path

PAYLOAD_BASE = 0xF0000000
PAYLOAD_MAX = 0x04000000
FD_BASE = 0x9FC00000
FD_SIZE = 0x300000


def parse_payload(data):
    if len(data) < 32 or len(data) > PAYLOAD_MAX:
        raise ValueError("XNUP size outside reserved region")
    magic, size = struct.unpack_from('<4sI', data)
    if magic != b'XNUP' or size != len(data) - 8:
        raise ValueError("XNUP magic/length mismatch")
    at, entries = 8, {}
    while at + 24 <= len(data):
        name, size, reserved = struct.unpack_from('<16sII', data, at)
        if name[0] == 0:
            if data[at:] != bytes(24) or 'loader.efi' not in entries:
                raise ValueError("invalid terminator or missing loader.efi")
            if not entries['loader.efi']:
                raise ValueError("empty loader.efi")
            return entries
        if reserved:
            raise ValueError("reserved entry field is nonzero")
        padded = (size + 15) & ~15
        if padded > len(data) - at - 24:
            raise ValueError("entry exceeds XNUP container")
        label = name.split(b'\0', 1)[0].decode('ascii')
        if not label or label in entries or name != label.encode().ljust(16, b'\0'):
            raise ValueError("duplicate or malformed entry name")
        entries[label] = data[at + 24:at + 24 + size]
        at += 24 + padded
    raise ValueError("missing XNUP terminator")


def validate_loader(data, manifest_path):
    entries = parse_payload(data)
    image = entries['loader.efi']
    manifest = json.loads(Path(manifest_path).read_text())
    if (manifest.get('board') != 'lemonadep' or
            manifest.get('storage_writes') is not False or
            manifest.get('sha256') != hashlib.sha256(image).hexdigest()):
        raise ValueError("loader manifest must identify this lemonadep loader and disabled storage writes")
    # Reject other architectures and non-EFI applications before calling firmware.
    if len(image) < 64 or image[:2] != b'MZ':
        raise ValueError("loader is not PE/COFF")
    pe = struct.unpack_from('<I', image, 0x3c)[0]
    if pe > len(image) - 96 or image[pe:pe + 4] != b'PE\0\0':
        raise ValueError("invalid PE header")
    machine, = struct.unpack_from('<H', image, pe + 4)
    magic, = struct.unpack_from('<H', image, pe + 24)
    subsystem, = struct.unpack_from('<H', image, pe + 24 + 68)
    if (machine, magic, subsystem) != (0xAA64, 0x20B, 10):
        raise ValueError("loader must be an AArch64 PE32+ EFI application")
    return entries


def check_inputs(root, device, data, manifest_path):
    if device != 'lemonadep':
        raise ValueError("HackiOS integration is only enabled for lemonadep")
    validate_loader(data, manifest_path)
    root = Path(root)
    dtb = root / 'Resources/DTBs/lemonadep.dtb'
    if not dtb.is_file() or dtb.read_bytes()[:4] != b'\xd0\x0d\xfe\xed':
        raise ValueError("supply the target Resources/DTBs/lemonadep.dtb")
    package = root / 'Platforms/OnePlus/lemonadepPkg/Include'
    # Every proprietary reference must exist; no lemonade/redwood substitutions.
    import re
    for inc in package.glob('*.inc'):
        text = inc.read_text()
        # This board uses SimpleFb, so panel XML in the custom-display branch
        # is not a build input. All remaining raw resources are required.
        text = re.sub(r'!if \$\(USE_CUSTOM_DISPLAY_DRIVER\) == 1.*?!endif', '', text, flags=re.S)
        text = '\n'.join(line.split('#', 1)[0] for line in text.splitlines())
        for match in re.finditer(r'\b(Binaries/[^\s]+)', text):
            path = match.group(1)
            if not path.startswith('Binaries/lemonadep/') or not (root / path).is_file():
                raise ValueError(f"missing target firmware component: {path}")


def combine_image(shim, fd, payload):
    parse_payload(payload)
    if len(fd) != FD_SIZE or len(shim) < 64:
        raise ValueError("wrong lemonadep FD size or missing BootShim")
    padded = payload + bytes(-len(payload) % 16)
    total = len(shim) + len(fd) + len(padded)
    if struct.unpack_from('<Q', shim, 16)[0] != total:
        raise ValueError("BootShim image_size does not match this FD/payload")
    if struct.unpack_from('<Q', shim, 8)[0] != FD_BASE or shim[56:60] != b'ARM\x64':
        raise ValueError("wrong BootShim board/header")
    return shim + fd + padded
