##
#  Copyright (c) 2011 - 2022, ARM Limited. All rights reserved.
#  Copyright (c) 2014, Linaro Limited. All rights reserved.
#  Copyright (c) 2015 - 2020, Intel Corporation. All rights reserved.
#  Copyright (c) 2018, Bingxing Wang. All rights reserved.
#  Copyright (c) Microsoft Corporation.
#
#  SPDX-License-Identifier: BSD-2-Clause-Patent
##

################################################################################
#
# Defines Section - statements that will be processed to create a Makefile.
#
################################################################################
[Defines]
  DEFINE HACKIOS_ENABLE = 0
  PLATFORM_NAME                  = lemonadep
  PLATFORM_GUID                  = 852438DA-FB03-4EE1-8F2D-1B3DB2575C03
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/lemonadepPkg
  SUPPORTED_ARCHITECTURES        = AARCH64
  BUILD_TARGETS                  = RELEASE|DEBUG
  SKUID_IDENTIFIER               = DEFAULT
  FLASH_DEFINITION               = lemonadepPkg/lemonadep.fdf
  USE_CUSTOM_DISPLAY_DRIVER      = 0

  #
  # 0 = SM8350
  # 1 = SM8350-AB
  # 2 = SM8350-AC
  #
  SOC_TYPE                       = 0

!include LahainaPkg/LahainaPkg.dsc.inc

[PcdsFixedAtBuild]
  #
  # DDR Memory
  #
  # CONFIRMED from lemonadep uefiplat.cfg [Config] UnusableDDRMemoryStartAddr = 0x80000000.
  gArmTokenSpaceGuid.PcdSystemMemoryBase|0x80000000

  #
  # UEFI Stack
  #
  # CONFIRMED from lemonadep uefiplat.cfg [MemoryMap] "UEFI Stack" = 0x9FF90000 (+0x40000).
  gArmPlatformTokenSpaceGuid.PcdCPUCoresStackBase|0x9FF90000
  gArmPlatformTokenSpaceGuid.PcdCPUCorePrimaryStackSize|0x40000

  #
  # SMBIOS
  #
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemManufacturer|"Oneplus"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemModel|"9 Pro"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailModel|"lemonadep"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailSku|"9_Pro_lemonadep"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemBoardModel|"9 Pro"

  #
  # Simple Frame Buffer
  #
  # TODO(lemonadep): THE one fiddly value. These are inherited from lemonade (OP9, 1080x2400).
  # The OP9 Pro panel is 1440x3216 native, but the SimpleFb inherits ABL's cont_splash surface,
  # which may be downscaled. Source the real geometry from the cont_splash / framebuffer node in
  # the 9 Pro's dumped DTS (Resources/DTBs/lemonadep.dts). Wrong dims = garbled-but-present image
  # (safe to iterate), not a hang.
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferWidth|1080
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferHeight|2400
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferColorDepth|32

  #
  # Platform PEI
  #
  gQcomPkgTokenSpaceGuid.PcdPlatformType|"LA"
[LibraryClasses]
  #
  # Memory Libraries
  #
  MemoryMapLib|lemonadepPkg/Library/MemoryMapLib/MemoryMapLib.inf

  #
  # QCOM Libraries
  #
  ConfigurationMapLib|lemonadepPkg/Library/ConfigurationMapLib/ConfigurationMapLib.inf

  #
  # Ram Manager (Null - avoid Qualcomm RamManagerLib that needs RAM Partition Protocol)
  #
  RamManagerLib|SiliciumNullPkg/Library/RamManagerLibNull/RamManagerLibNull.inf

[BuildOptions]
  *_CLANGPDB_AARCH64_CC_FLAGS = -DHACKIOS_ENABLE=$(HACKIOS_ENABLE)
