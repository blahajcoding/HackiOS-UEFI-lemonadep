# HackiOS on lemonadep: firmware integration

This branch integrates a source-only OnePlus 9 Pro (8 GB variant) board package
with the HackiOS XNUP firmware handoff. It has **not** been built into a complete
firmware image or booted on hardware. It does not implement the XNU hardware port.

For the next device session, read the [agent handoff](AGENT-HANDOFF-lemonadep.md).

## Provenance

| Input | Pinned revision |
| --- | --- |
| Project-Silicium/Mu-Silicium | `e51cd877e31c8fbb322032dc4cb6715e83d25ad3` |
| blahajcoding/op9pro-mainline-poc | `46ecf3cadd1b09ed944e4b0c64c13aa8f07962cd` |
| blahajcoding/hackios-xnu-kernel (fork of oosexgang) | `8e61187098f2c26c5daee8f9f72b6416aa64b9ab` |

The board package preserves the PoC's own-firmware memory/configuration tables
and driver lists. Its hardware results apply to that PoC, not this integration.
Adaptations to the pinned Mu base include the TOML schema, SMBIOS PCD, package
paths, and removal of obsolete SchedulerInterfaceAddr/InitCardSlot PCD settings.
Port work should use the user's [kernel/loader fork](https://github.com/blahajcoding/hackios-xnu-kernel)
and [userland fork](https://github.com/blahajcoding/hackios-xnu-userland).
Their inspected `main` heads still match the original pinned upstream snapshots;
keep upstream attribution and inspect subsequent fork changes before building.
No Linux GPL driver patches were imported. Upstream copyright/license notices
remain in place; the PoC describes its UEFI work as under upstream terms.

## Behavior

Normal builds do not enable the XNU hook or reserve its payload region.
With `--hackios-payload`, BootShim copies an appended XNUP container into the
fixed HackiOS ABI region and the board map reserves that range before DXE.
After console/device setup, BDS loads the container's `loader.efi` as an EFI
application without calling ExitBootServices. A missing/invalid container or a
returned EFI application leaves normal boot handling available.

The firmware glue has no raw-partition logging, RAM persistence probe, or forced
reset. It does not start Linux or DOOM automatically and does not include the
PoC's DWC3 debug register-poking driver. Vendor drivers and the external loader
still have their own behavior: this is not a general guarantee of zero writes.

## Inputs and build

1. Initialize pinned submodules with `git submodule update --init --recursive`.
   Follow upstream setup requirements. Do not use `--update` for this integration.
2. Populate `Binaries/lemonadep/` from the target phone's XBL firmware using the
   PoC extraction procedure. Apply the appropriate upstream vendor-binary fixes.
   Put its DTB at `Resources/DTBs/lemonadep.dtb`. These files remain local.
3. Supply a **lemonadep-adapted** HackiOS `loader.efi` and a compatible XNUP
   container, made with HackiOS's `xnuloader/mkpayload.py`. Do not use the redwood
   prebuilt loader. Its framebuffer-based board selection, watchdog/USB paths,
   storage addresses, `logdump` writes and partition-write assumptions require
   adaptation. These changes belong in the external HackiOS repository.
4. Make a JSON declaration alongside that loader:

   ```json
   {
     "board": "lemonadep",
     "storage_writes": false,
     "sha256": "SHA256 of the adapted loader.efi bytes"
   }
   ```

   This declaration binds the operator's compatibility claim to exact bytes; it
   is not code analysis or proof that the loader cannot write. The build checks
   its hash, board, flag and PE architecture/subsystem, with no prebuilt fallback.

5. Build with:

   ```sh
   python3 build_uefi.py -d lemonadep -r DEBUG \
     --hackios-payload /absolute/path/to/payload.bin \
     --hackios-loader-manifest /absolute/path/to/loader.json
   ```

   Both options are required together. No device command is run by the builder.
   Without local firmware, DTB and an adapted loader it stops at preflight.

No Apple artifacts, proprietary firmware, DTBs, or boot images are distributed.
The stock HackiOS `mkxnuimg.py` must not be used to wrap this branch: its defaults
describe redwood and a different boot-image format. Use this branch's builder.

## Address and wire contract

- UEFI FD: `0x9fc00000`, size `0x300000`; boot-header version 3, gzip plus DTB.
- XNUP destination/reservation: `[0xf0000000, 0xf4000000)` (64 MiB including header).
  This carves the PoC's conventional high-memory row and preserves its endpoint.
  It is an integration candidate, not a new hardware measurement: confirm the
  full range against actual firmware, carve-outs and the target RAM variant.
- XNUP: little-endian magic `0x50554e58`, u32 body size excluding the 8-byte header.
  Each entry has `char name[16]`, u32 data size, u32 zero reserved field; data is
  padded to 16 bytes. A zero 24-byte entry terminates the body.
- Exactly one nonempty `loader.efi` must be present. Host checks validate the
  container before packing; firmware validates it again before LoadImage.
- BootShim has compile-time bounds and overlap checks, runtime source-overlap
  checks, complete image-size accounting, and handles an FD already in place.
  A corrupt payload header is invalidated before continuing into firmware.
- The payload region is separate from the eventual XNU managed arena. The
  external loader must claim only suitable free EFI memory, leaving UEFI resident.

The CPU page size, UFS logical sector size and EFI 4 KiB allocation unit are
separate. Nothing here changes XNU's 16 KiB page configuration.

## Validation

Run host tests (a native C compiler is required for the sanitized wire parser):

```sh
python3 -m pip install unicorn==2.1.4
python3 -m unittest discover -s tests -v
```

BootShim execution tests additionally require clang/llvm-objcopy, or `ZIG` set
to a Zig executable. They execute the assembled AArch64 code in Unicorn,
checking actual copy results, in-place FD handling, invalid magic, overlapping
source ranges, oversized builds, disabled mode, and header size accounting.
Protocol tests exercise all truncations of a valid sample under ASan/UBSan,
malformed entries, manifest/architecture rejection, packaging, memory-map
reservation continuity, and missing firmware with no board fallback.

Locally verified during integration:

- 14 unittest groups passed, including actual BootShim emulation.
- XnuLoader.c cross-compiled in enabled and disabled modes against pinned Mu
  headers with `-Wall -Wextra -Werror` using Zig's AArch64 compiler.
- The enabled board MemoryMapLib.c cross-compiled against pinned Mu headers.
- Python source parsing and whitespace checks passed.

Full firmware linking was not attempted: target Binaries/lemonadep and the target
DTB are absent. Host tests do not qualify vendor binary patches, GOP geometry,
storage stability, UEFI/XNU CPU coexistence, or hardware memory ownership.

Hardware gates, in order: preserve known-working images/backups; qualify the
firmware memory map/GOP; run the adapted EFI loader; single-core XNU/minimal PID 1;
then storage reads and matched iOS userspace. The PoC's USB cable-event reset and
display artifacts remain open issues. Do not overwrite its opluslog ESP or an
existing HFS userdata installation while testing this firmware integration.

## Repository and branch

The integration lives on `hackios-lemonadep` in
[blahajcoding/HackiOS-UEFI-lemonadep](https://github.com/blahajcoding/HackiOS-UEFI-lemonadep/tree/hackios-lemonadep).
The fork's `main` branch retains upstream state. The integration deliberately
uses the pinned HackiOS Mu base above rather than incorporating later upstream
KEP and submodule changes without validation.

```sh
git clone --branch hackios-lemonadep https://github.com/blahajcoding/HackiOS-UEFI-lemonadep.git
cd HackiOS-UEFI-lemonadep
```

The accompanying patch archive can also be applied to a checkout at the pinned
Mu base with `git am --keep-cr patches/*.patch` (the upstream boot-manager files
use CRLF). Do not apply it to arbitrary upstream HEAD.
