# Agent handoff: start the HackiOS lemonadep device port

Prepared 22 October 2026. Read this before executing any device commands.

## Objective and first action

Bring up HackiOS on the user's OnePlus 9 Pro (`lemonadep`, SM8350) using their
Mu-Silicium port and a bundled RAM payload. Preserve the existing shim/HFS XNU
work as a separate baseline. First prove the firmware-to-EFI-application handoff,
then XNU and minimal userspace, then matched iOS userspace and software graphics.

**First device-session action:** establish the phone's actual model/RAM/firmware,
current installation, available root/recovery access, and backup state. The
public PoC's installation history is not evidence of this phone's current layout.
Then capture its live FDT and own firmware before choosing addresses or binaries.

Do not start by running `common/run.sh redwood`, booting a redwood prebuilt,
flashing a root image, or executing the Linux PoC's installation instructions.
The next engineering deliverable is a diagnostic EFI application that returns
to UEFI, bundled as `loader.efi`, not a claim that the full XNU port already works.

## Repositories and verified starting state

| Component | Source / revision |
| --- | --- |
| Firmware integration | [HackiOS-UEFI-lemonadep, branch hackios-lemonadep](https://github.com/blahajcoding/HackiOS-UEFI-lemonadep/tree/hackios-lemonadep), code publication `8c8ce8ed3c632538bfa380655efee724341c8704` |
| Mu base | `Project-Silicium/Mu-Silicium` at `e51cd877e31c8fbb322032dc4cb6715e83d25ad3` |
| User's Linux/UEFI PoC | [op9pro-mainline-poc](https://github.com/blahajcoding/op9pro-mainline-poc/tree/46ecf3cadd1b09ed944e4b0c64c13aa8f07962cd), `46ecf3cadd1b09ed944e4b0c64c13aa8f07962cd` |
| HackiOS kernel/loader | [hackios-xnu-kernel](https://github.com/oosexgang/hackios-xnu-kernel/tree/8e61187098f2c26c5daee8f9f72b6416aa64b9ab), `8e61187098f2c26c5daee8f9f72b6416aa64b9ab` |
| HackiOS userland | [hackios-xnu-userland](https://github.com/oosexgang/hackios-xnu-userland/tree/906425b75e02b4f99eb5d7bb1ef7c9583472d772), `906425b75e02b4f99eb5d7bb1ef7c9583472d772` |
| Separate shim/HFS baseline | [ios-lemonadep](https://github.com/blahajcoding/ios-lemonadep/tree/0ac36c8ffa1f9d17d62483c41e09ca201a327cc2), `0ac36c8ffa1f9d17d62483c41e09ca201a327cc2`; read its AGENTS.md and newest NOTES.md entries |

Use the firmware integration branch, not the fork's upstream `main`. Check remote
heads for subsequent user changes before editing; preserve existing work and do
not force-push. The pinned snapshots above are a reproducibility baseline, not an
instruction to discard later fixes. Keep submodule revisions pinned.

**Verified here:** the source integration is committed and pushed. Fourteen host
test groups passed locally and in [GitHub run 39747592746](https://github.com/blahajcoding/HackiOS-UEFI-lemonadep/actions/runs/39747592746).
Tests include ASan/UBSan payload parsing and execution of assembled BootShim in
Unicorn. New EFI glue cross-compiled in both enabled and disabled modes against
pinned Mu headers; the enabled board memory-map source also cross-compiled.

**Not verified:** full firmware linking, a boot of this integration, runtime
payload-region ownership, an adapted HackiOS loader, XNU under this UEFI, or iOS
on this path. Target proprietary firmware and DTB were not present in the build
workspace. A loader manifest is an operator declaration tied to a hash, not proof
of compatibility or absence of writes.

**User/repository-reported:** the separate Linux PoC boots through Mu-Silicium,
reads its kernel from UFS, runs Phosh, and has S3908 touch and A660 rendering.
It reports framebuffer artifacts and USB cable-event freezes/resets. The separate
XNU shim notes report minimal PID 1, then a UFS-root attempt aborting in an
inherited USB probe, followed by source fixes. Do not promote these reports into
results for this integration.

## Architecture and current implementation

```text
temporary fastboot boot of a combined Android boot image
  BootShim + lemonadep Mu-Silicium FD + appended XNUP container
    BootShim copies XNUP into an explicitly reserved RAM region
      UEFI BDS -> container's loader.efi via LoadImage/StartImage
        adapted HackiOS loader -> XNU -> test ramdisk / matched iOS root
```

There is no requirement to install a kernel in `oplusreserve5`, `opluslog`, or an
ESP. The intended first path bundles it in RAM. A full iOS system may exceed the
small payload capacity; do not solve that by overwriting a partition implicitly.

Read [hackios-lemonadep.md](hackios-lemonadep.md) for the format and build options.
Implementation entry points:

| Subsystem | Files / behavior |
| --- | --- |
| Board | `Platforms/OnePlus/lemonadepPkg/`, `Resources/Configs/lemonadep.toml`; adapted from the user's 8 GB PoC |
| Packaging | `build_uefi.py`, `Resources/Scripts/hackios_payload.py`; opt-in XNUP, manifest validation, no board/prebuilt fallback |
| Early copy | `BootShim/BootShim.S`, `BootShim/Makefile`; image-size accounting, bounds and source-overlap checks |
| EFI entry | `Silicon/Silicium/SiliciumPkg/Library/BootManagerLib/XnuLoader.c` and `XnuPayload.h`; bounded parser and EFI application launch |
| Tests | `tests/test_hackios.py`, `tests/test_bootshim.py`, `tests/hackios_payload_host.c` |

Without `--hackios-payload`, the hook is disabled. The imported firmware glue has
no raw storage logging or persistence probes. This does not constrain proprietary
drivers or the separately supplied HackiOS loader. Firmware does not call
ExitBootServices on this path; qualify resident services and CPU ownership before
using them concurrently with XNU.

## Initial session: inventory, capture, and reproduce

1. Read relevant local AGENTS.md instructions. Identify the attached device and
   its current mode with the user; never operate on a different attached phone.
   Use explicit adb/fastboot device selection when more than one is present.
2. In Android, query only needed properties: model/device, firmware fingerprint,
   slot suffix, bootloader state and RAM. Check `adb shell id`. Do not unlock,
   root, format or install recovery as an incidental part of this task.
3. If root is already available, capture `/sys/firmware/fdt`, the active XBL,
   partition by-name symlinks, logical block sizes/capacities and GPT information
   read-only. Read from discovered names, never guessed `/dev/sdaN` nodes. The
   PoC's `uefi/new-files/Resources/dump_lemonadep.sh` is a useful reference; it is
   not included in this firmware branch. Inspect it before using it.
4. Preserve off-device originals needed for recovery: relevant boot/slot images,
   partition tables and calibration/persist data; preserve valuable userdata.
   Record hashes and actual coverage. Never claim a backup exists from old notes.
   If root/dumps are unavailable, progress on host work and identify the exact
   missing inputs rather than changing the installation to obtain them.
5. Keep dumps, firmware, serials and credentials in private local storage outside
   git. Keep a private inventory with the model, RAM, firmware, active slot,
   artifact sizes/hashes and extraction tool revision. Publish only redacted
   evidence. Do not stage the local `Binaries` contents or dumped DTB.
6. Extract Qualcomm components from this phone's own firmware. Reconcile driver
   names, order and required vendor-binary fixes against the PoC and pinned Mu
   base. Review the map/config comments rather than assuming every inherited row
   was measured. Build ordinary lemonadep UEFI first and compare with the user's
   known-working firmware image, if available.

The base config describes an **8 GB unit**. Do not use it unchanged for a 12 GB
unit. Stock panel resolution is not automatically active scanout geometry.

## Hardware milestones and acceptance gates

### A. UEFI plus an inert diagnostic EFI payload

Develop a small EFI application named `loader.efi` that reports to console/GOP
and returns. It must not touch raw block devices, reconfigure peripherals, reset
the phone, or start XNU. Report CurrentEL, supported CPU feature registers,
CNTFRQ, GOP base/size/geometry/pixel format, and the EFI memory map. Avoid speculative
register probes, especially inherited physical-timer accesses.

Before bundling it, reconcile:

- FD candidate: `0x9fc00000`, size `0x300000`, from the PoC package.
- XNUP candidate: `[0xf0000000, 0xf4000000)`, 64 MiB **including header/padding**.
- Actual boot-image placement, total size and ABL download limit.
- Static and dynamic carve-outs, protected/shared regions, loader allocations,
  framebuffer and DMA reservations; absence from one FDT list is not ownership.

Keep constants synchronized across BootShim, firmware parser/map, builder, and
the future HackiOS loader. A changed address requires tests and a full rebuild.
Use this branch's boot-image builder, not redwood's `mkxnuimg.py` defaults.

Acceptance: three temporary boots reach diagnostics and return through the
normal firmware path, with matching artifact hashes and captured display/map
evidence. Host emulation alone does not pass this gate. Avoid repeated USB
replugging during experimental kernels given the PoC's reported cable-event bug.

### B. Adapt the real HackiOS EFI loader before booting XNU

Work in a separate kernel/loader branch; preserve the upstream redwood path.
Primary file: `xnuloader/loader.c`. Implement and test:

- Explicit lemonadep selection, rejecting unknown boards; stock selection by
  framebuffer address silently falls back to QEMU and is unsuitable here.
- Runtime GOP handoff and verified SoC/GIC/PSCI/CPU descriptions. Use actual
  affinities and boot EL; the old shim's EL1 entry does not establish UEFI's EL.
- Disable all raw log writes (`find_log_partition`/`write_logs`), block-write
  commands and persistent logging. `ufs_write=0` alone does not disable logdump
  writes. Audit USB command paths, watchdog and charger setup separately.
- Claim an exclusively owned XNU arena through EFI allocation. Keep firmware,
  payload, framebuffer and DMA memory outside it. Do not use forced placement
  to bypass failed allocation or describe a whole RAM bank as free.
- Disable unqualified native UFS takeover, GPIO/PMIC, GPU, Wi-Fi, audio, camera,
  haptics, frequency and charging paths. Audit actual initialization call sites;
  do not assume a guessed `feature=0` argument guards every access.

Create the manifest only for the rebuilt/adapted binary, after reviewing its
write paths. First prove loader diagnostics and normal return, without XNU.
Do not enable HackiOS's custom USB transport just to collect logs: its register
path is not yet qualified. Screen/video or a qualified console is sufficient.

### C. XNU and a tiny RAM root

Start with one XNU execution CPU, conservative firmware clocks, and all optional
hardware disabled. Reserve any firmware service CPU explicitly; `cpus=1` does not
mean UEFI and XNU may use the same CPU concurrently. Do not copy redwood's
`bootcpu=7` setting without checking the selected core and resident-service design.

Validate 16 KiB CPU translation support, PSCI conduit, GIC redistributor matching,
timer IRQ and cache/translation transitions at the actual entry EL. Retain
64-bit physical-address arithmetic, including the above-4-GiB pmap fix. EFI 4 KiB
units, UFS sectors, filesystem blocks and GPU pages are independent of XNU pages.

Acceptance: captured early XNU stages, working timer/SGI, minimal PID 1 and 60 s
of heartbeat; repeat without unexplained resets. Establish panic/exception
diagnostics and a recovery path before expanding CPU count or peripherals.

### D. Matched iOS userspace and software graphics

For this HackiOS experiment use its matched iPhone X iOS **16.5 / 20F66** inputs.
The separate shim/HFS baseline uses **16.7.16 / 20H392**. Keep their caches, jobs,
injected libraries and roots distinct. Do not replace the existing HFS root to
test this route; document any later storage proposal separately.

Prove dynamic execution/dyld, launchd, minimal service startup, IOSurface sharing,
then framebuffer presentation and SpringBoard. Verify selector numbers, structure
offsets, ownership, seeds, planes and pixel formats together. Injection code uses
20F66 shared-cache addresses and vtable slots: require matching cache UUID/build
and expected original bytes/pointers before modifying them.

### E. Independent peripheral work

- **UFS:** qualify reads against existing ABL/UEFI state, actual LUNs and GPT bounds,
  high-address DMA, ownership and restoration. Never import redwood's darwin LBAs,
  GUIDs or write offsets. Initial work is read-only and needs no new partition.
- **Touch:** use the PoC's S3908/TCM report and power-sequencing evidence, not Goodix.
  It uses GPIO I2C because GENI FIFO/GPI was unavailable in that boot path; GPIO197
  requires EGPIO ownership. The parser describes a 7-byte prefix and 12-byte
  contact records. Qualify firmware format, releases and coordinate transforms.
  Preserve shared panel rails; do not update controller firmware during bring-up.
- **Display/GPU:** start with sustained CPU framebuffer updates. Adreno 660 needs
  its own power/GMU/SMMU/firmware qualification; redwood targets 642L. Identical
  `a660_*` filenames do not identify identical firmware. Separate GPU-render
  correctness from the PoC's unresolved render-to-scanout artifacts.
- **Wi-Fi:** source evidence points to QCA6490 PCIe/CNSS, not redwood's WCN6750
  WPSS/AHB path. Confirm device/revision, transport, firmware and calibration
  before implementing PCIe/MSI/MHI/IOMMU integration. Do not load qca6750/wpss
  images as a shortcut. Review licensing before copying Linux driver code.

## Host checks and build command

```sh
git clone --branch hackios-lemonadep https://github.com/blahajcoding/HackiOS-UEFI-lemonadep.git
cd HackiOS-UEFI-lemonadep
git submodule update --init --recursive
python3 -m pip install unicorn==2.1.4
python3 -m unittest discover -s tests -v
```

Require actual execution of the BootShim tests, not a skipped result: install
clang plus llvm-objcopy, or set `ZIG` to a Zig executable. Follow upstream build
dependency instructions separately. Do not use `build_uefi.py --update`.

After the milestone-A inputs and placement checks are satisfied:

```sh
python3 build_uefi.py -d lemonadep -r DEBUG \
  --hackios-payload /absolute/path/to/payload.bin \
  --hackios-loader-manifest /absolute/path/to/loader.json
```

Use HackiOS's `xnuloader/mkpayload.py` to construct XNUP. Follow
[the manifest/build contract](hackios-lemonadep.md#inputs-and-build). The host
manifest check intentionally rejects a non-AArch64 EFI application, a wrong hash,
or a loader declared for redwood. No generated boot image is currently provided.

## Session record and stopping point

Maintain a concise redacted bring-up log in this repository and keep raw evidence
privately. For every attempted boot record:

```text
Device/firmware/RAM variant:
Repo + submodule commits:
Stage and expected observation:
Image + loader + DTB + payload SHA256 and sizes:
Boot arguments; CPU/service ownership:
Memory/GOP facts and their evidence source:
Actual observation; exception ESR/ELR/FAR when available:
Storage operations performed (none for initial stages):
Recovery outcome:
Verified conclusion vs hypothesis:
Next single experiment:
```

Keep baseline images and hashes before rebuilding. Make one diagnostic change
per experiment when debugging a failure; do not infer success from a dark screen
or absence of logs. Never transfer MMIO addresses, firmware identities, or raw
partition nodes between boards. Unlocking, flashing, filesystem creation,
repartitioning, raw logging and persistent writes are outside the initial scope.

Update this handoff after milestones with exact commits, CI links, results and
remaining blockers. Commit source/docs and push the integration branch when
checks pass; never commit proprietary or per-device artifacts. Report host-test
success separately from full firmware linking and actual device boot results.
