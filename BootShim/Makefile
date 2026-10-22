ARCH              = arm64
TARGET            = aarch64-linux-gnu
CC                = clang
CFLAGS            = --target=$(TARGET)
OBJCOPY           = llvm-objcopy
HACKIOS_ENABLE   ?= 0
XNUP_SIZE        ?= 0
PAYLOAD_BASE     ?= 0xF0000000
PAYLOAD_MAX      ?= 0x04000000

all: BootShim.elf BootShim.bin

BootShim.bin: BootShim.elf
	$(OBJCOPY) -O binary $< $@

BootShim.elf: BootShim.S FORCE
	$(CC) ${CFLAGS} -c $< -o $@ -DREQUIRES_KERNEL_HEADER=$(REQUIRES_KERNEL_HEADER) -DFD_BASE=$(FD_BASE) -DFD_SIZE=$(FD_SIZE) -DHACKIOS_ENABLE=$(HACKIOS_ENABLE) -DXNUP_SIZE=$(XNUP_SIZE) -DPAYLOAD_BASE=$(PAYLOAD_BASE) -DPAYLOAD_MAX=$(PAYLOAD_MAX)

BootShim.S:

.PHONY: FORCE
FORCE:
