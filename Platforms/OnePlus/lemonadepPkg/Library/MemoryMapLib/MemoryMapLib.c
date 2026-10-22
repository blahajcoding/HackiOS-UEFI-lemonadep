#include <Library/MemoryMapLib.h>

//
// Transcribed from the OnePlus 9 Pro's own firmware:
//   _dump/lemonadep/out/BOOT.MXF.1.0-00946.1-LAHAINA-1/RawFiles/uefiplat.cfg
//   ([MemoryMap] + [RegisterMap], #-commented rows skipped). The leading "HYP"
//   region is the [Config] UnusableDDRMemoryAtBeginning (0x80000000 +0x600000).
// Column order vs the cfg: label moved to the front; all other fields verbatim.
//
// NOTE: [RegisterMap] is copied exactly as the 9 Pro cfg lists it (no PCIE entries,
// unlike lemonade — lemonade's extras are not in this device's cfg). Add only if a
// driver faults on an unmapped register window.
//

STATIC
EFI_MEMORY_REGION_DESCRIPTOR
gMemoryDescriptor[] = {
  // Name, Address, Length, HobOption, ResourceType, ResourceAttribute, MemoryType, ArmAttribute

  // DDR Regions
  {"HYP",              0x80000000, 0x00600000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN},
  {"Axon DMA",         0x80600000, 0x00100000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN},
  {"BOOT",             0x80700000, 0x00100000, AddMem, MEM_RES, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"AOP CMD DB",       0x80860000, 0x00020000, AddMem, MEM_RES, UNCACHEABLE, Reserv, UNCACHED_UNBUFFERED_XN},
  {"XBL Log Buffer",   0x80884000, 0x00010000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN},
  {"USB HLOS Shared",  0x808A0000, 0x00010000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, UNCACHED_UNBUFFERED_XN},
  {"SMEM",             0x80900000, 0x00200000, AddMem, MEM_RES, UNCACHEABLE, Reserv, UNCACHED_UNBUFFERED_XN},
  {"PIL Reserved",     0x85200000, 0x16600000, AddMem, MEM_RES, UNCACHEABLE, Reserv, UNCACHED_UNBUFFERED_XN},
  // The OEM-cfg "DXE Heap" (0x9B800000, 60 MB) sized the stock ABL's pool. Our Mu-Silicium
  // DEBUG build is far heavier and exhausts 60 MB before VariableRuntimeDxe dispatches, which
  // starves every later arch-protocol producer (Variable/Reset/RTC/Monotonic/Capsule) and trips
  // the DxeMain.c:593 assert. Known-good lemonade (OP9) deviates from its own dump for exactly
  // this reason: it puts the DXE pool in free high DDR. Keep the original 60 MB as extra
  // conventional memory and host the primary pool in the free 0xB0000000-0xD0000000 gap (between
  // the 9 Pro's "Kernel" placeholder and "Guest VM"). Physical DDR on SM8350 doesn't
  // reach 0xC0000000 — 256 MB at 0xB0000000 triggers a Synchronous External Abort at
  // 0xBFFFF000 (translation table top-of-heap).  192 MB aborts at 0xBBFFF000, so cap
  // at 128 MB (0xB8000000 endpoint) and give USB DMA a dedicated uncached region.
  {"DXE Heap LO",      0x9B800000, 0x03C00000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"Sched Heap",       0x9F400000, 0x00400000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"FV Region",        0x9F800000, 0x00200000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"ABOOT FV",         0x9FA00000, 0x00200000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN},
  {"UEFI FD",          0x9FC00000, 0x00300000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK},
  {"SEC Heap",         0x9FF00000, 0x0008C000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"CPU Vectors",      0x9FF8C000, 0x00001000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK},
  {"MMU PageTables",   0x9FF8D000, 0x00003000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"UEFI Stack",       0x9FF90000, 0x00040000, AddMem, SYS_MEM, SYS_MEM_CAP, BsData, WRITE_BACK_XN},
  {"Log Buffer",       0x9FFF7000, 0x00008000, AddMem, SYS_MEM, SYS_MEM_CAP, RtData, WRITE_BACK_XN},
  {"Info Blk",         0x9FFFF000, 0x00001000, AddMem, SYS_MEM, SYS_MEM_CAP, RtData, WRITE_BACK_XN},
  // OEM cfg reserves this for the HLOS kernel ABL would load; nothing lives here once
  // UEFI runs (FD executes from 0x9FC00000). Reclaim as conventional memory — LoadImage
  // of a 36 MB Linux Image needs ~80 MB transient and the two DXE heaps alone are too
  // fragmented for it.
  {"Kernel",           0xA0000000, 0x10000000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"DXE Heap",         0xB0000000, 0x08000000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"USB DMA",          0xB8000000, 0x00100000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   UNCACHED_UNBUFFERED_XN},
  // Remaining DDR, transcribed from the XBL-patched DT /memory node of this unit (8 GB):
  //   bank1: 0x80000000 + 0x39700000 (ends 0xB9700000)
  //   bank2: 0xC0000000 + 0x1C0000000 (ends 0x280000000)
  // Declared Conv so Linux (which boots off the EFI memory map, not DT /memory) sees full
  // RAM; holes for Guest VM / TZApps / DBI / Display carveouts kept reserved below.
  // NOTE: 12 GB units have a different bank2 length — this table is for the 8 GB variant.
  {"RAM B1 Tail",      0xB8100000, 0x01600000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"RAM B2 Low",       0xC0000000, 0x10000000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"Guest VM",         0xD0000000, 0x08800000, AddMem, SYS_MEM, SYS_MEM_CAP, Reserv, WRITE_BACK_XN},
  {"RAM B2 Mid1",      0xD8800000, 0x01800000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"TZApps Reserved",  0xDA000000, 0x07600000, HobOnlyNoCacheSetting, MEM_RES, UNCACHEABLE, Reserv, UNCACHED_UNBUFFERED_XN},
  {"RAM B2 Mid2",      0xE1600000, 0x02700000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,   WRITE_BACK_XN},
  {"DBI Dump",         0xE3D00000, 0x00F00000, NoHob,  MMAP_IO, INITIALIZED, Conv,   UNCACHED_UNBUFFERED_XN},
  {"Display Reserved", 0xE4D00000, 0x02400000, AddMem, MEM_RES, SYS_MEM_CAP, Reserv, WRITE_THROUGH_XN},
  {"RAM B2 High",      0xE7100000, 0x198F00000, AddMem, SYS_MEM, SYS_MEM_CAP, Conv,  WRITE_BACK_XN},

  // Other Memory Regions
  {"IMEM Base",        0x14680000, 0x00040000, NoHob,  MMAP_IO, INITIALIZED, Conv,   NS_DEVICE},
  {"IMEM Cookie Base", 0x146BF000, 0x00001000, AddDev, MMAP_IO, INITIALIZED, Conv,   NS_DEVICE},

  // Register Regions
  {"IPC_ROUTER_TOP",   0x00400000, 0x00100000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"SECURITY CONTROL", 0x00780000, 0x00007000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"QUP",              0x00800000, 0x00300000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"PRNG_CFG_PRNG",    0x010D0000, 0x00010000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"TCSR_TCSR_REGS",   0x01FC0000, 0x00030000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"PERIPH_SS",        0x08800000, 0x00200000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"USB",              0x0A600000, 0x04000000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"AOSS",             0x0B000000, 0x04000000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"TLMM_WEST",        0x0F100000, 0x00300000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"TLMM_SOUTH",       0x0F500000, 0x00300000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"TLMM_NORTH",       0x0F900000, 0x00300000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"SMMU",             0x15000000, 0x000D0000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE},
  {"APSS_HM",          0x17800000, 0x00D99000, AddDev, MMAP_IO, UNCACHEABLE, MmIO,   NS_DEVICE}
};

VOID
GetMemoryMap (
  OUT EFI_MEMORY_REGION_DESCRIPTOR **MemoryDescriptor,
  OUT UINT8                         *MemoryDescriptorCount)
{
  // Pass Data
  *MemoryDescriptor      = gMemoryDescriptor;
  *MemoryDescriptorCount = ARRAY_SIZE (gMemoryDescriptor);
}
