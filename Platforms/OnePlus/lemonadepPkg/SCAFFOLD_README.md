# lemonadep package

Imported from blahajcoding/op9pro-mainline-poc commit
46ecf3cadd1b09ed944e4b0c64c13aa8f07962cd and adapted to Mu-Silicium
commit e51cd877e31c8fbb322032dc4cb6715e83d25ad3.

The published hardware results apply to the source PoC, not this integration.
The memory map targets its 8 GB unit. Other variants require their own map.
Supply Binaries/lemonadep from the target firmware and
Resources/DTBs/lemonadep.dtb locally. Neither is distributed here.
See docs/hackios-lemonadep.md for build and validation instructions.

Adaptations: current TOML schema, SMBIOS PCD and source paths; no obsolete
SchedulerInterfaceAddr/InitCardSlot PCDs; no ACPI table or DOOM dependency.
