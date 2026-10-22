#if HACKIOS_ENABLE
#if XNUP_SIZE < 32 || XNUP_SIZE > PAYLOAD_MAX || (FD_SIZE & 15) != 0 || (PAYLOAD_BASE & 15) != 0
#error Invalid HackiOS payload or FD geometry
#endif
#if PAYLOAD_BASE < FD_BASE + FD_SIZE && FD_BASE < PAYLOAD_BASE + PAYLOAD_MAX
#error HackiOS payload reservation overlaps UEFI FD
#endif
#endif

_Head:
  adr   x1, _Payload    /* Set _Entry address */
  b     _Start          /* Jump to the real code */

#if REQUIRES_KERNEL_HEADER == 1
_StackBase:
  .quad FD_BASE         /* Text Offset */

_StackSize:
#if HACKIOS_ENABLE
  /* Full source image, including appended container and 16-byte padding. */
  .quad _Payload - _Head + FD_SIZE + ((XNUP_SIZE + 15) & ~15)
#else
  .quad FD_SIZE         /* Image Size */
#endif
  .quad 0               /* Flags */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .ascii "ARM\x64"      /* ARM64 Magic */
  .long 0               /* Reserved */
#endif

_Start:
#if HACKIOS_ENABLE
  // Refuse overlapping source/destination ranges before writing either one.
  ldr   x10, =FD_SIZE
  add   x11, x1, x10
  ldr   x12, =((XNUP_SIZE + 15) & ~15)
  adds  x13, x11, x12
  b.cs  _Dead
  ldr   x14, =FD_BASE
  add   x15, x14, x10
  cmp   x1, x14
  beq   1f
  cmp   x1, x15
  b.hs  1f
  cmp   x14, x13
  b.lo  _Dead
1:
  ldr   x14, =PAYLOAD_BASE
  ldr   x15, =PAYLOAD_MAX
  add   x15, x14, x15
  cmp   x1, x15
  b.hs  2f
  cmp   x14, x13
  b.lo  _Dead
2:
#endif
  mov   x4, x1
  ldr   x5, =FD_BASE
  cmp   x4, x5
#if HACKIOS_ENABLE
  b.ne  3f
  ldr   x6, =FD_SIZE
  add   x4, x4, x6
  b     _CopyPayload
3:
#else
  beq   _Entry
#endif
  ldr   x6,  =FD_SIZE

_CopyLoop:
  ldp   x2, x3, [x4], #16
  stp   x2, x3, [x5], #16
  subs  x6, x6, #16
  b.ne  _CopyLoop

#if HACKIOS_ENABLE
_CopyPayload:
  // No header-sized read beyond the compile-time source image.
  ldr   w2, [x4]
  ldr   w3, =0x50554E58
  cmp   w2, w3
  b.ne  _BadPayload
  ldr   w2, [x4, #4]
  ldr   w3, =(XNUP_SIZE - 8)
  cmp   w2, w3
  b.ne  _BadPayload
  ldr   x6, =((XNUP_SIZE + 15) & ~15)
  ldr   x5, =PAYLOAD_BASE
_CopyXnup:
  ldp   x2, x3, [x4], #16
  stp   x2, x3, [x5], #16
  subs  x6, x6, #16
  b.ne  _CopyXnup
  b     _PayloadDone
_BadPayload:
  // Invalidate a previous run's header and let normal firmware boot continue.
  ldr   x5, =PAYLOAD_BASE
  str   xzr, [x5]
_PayloadDone:
#endif
  ldr   x5, =FD_BASE

_Entry:
  br    x5

_Dead:
  b     _Dead

.text
.align 4
.ltorg
.align 4

_Payload:
