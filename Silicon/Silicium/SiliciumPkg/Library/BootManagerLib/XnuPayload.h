/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * XNUP wire format from oosexgang/hackios-xnu-kernel.
 * Included after Uefi.h (or equivalent integer typedefs in host tests).
 */
#ifndef XNU_PAYLOAD_H
#define XNU_PAYLOAD_H

#define XNU_PAYLOAD_BASE      0xF0000000ULL
#define XNU_PAYLOAD_MAX_SIZE  0x04000000ULL
#define XNU_PAYLOAD_MAGIC     0x50554E58U

STATIC UINT32
XnuRead32 (CONST UINT8 *P)
{
  return (UINT32)P[0] | ((UINT32)P[1] << 8) |
         ((UINT32)P[2] << 16) | ((UINT32)P[3] << 24);
}

/* Validate the entire container before returning a pointer into it. */
STATIC BOOLEAN
XnuFindLoader (CONST UINT8 *Data, UINTN Available,
               CONST VOID **Image, UINTN *ImageSize)
{
  CONST UINT8 *Found = NULL;
  UINTN FoundSize = 0;
  UINTN End;
  UINTN At = 8;

  *Image = NULL;
  *ImageSize = 0;
  if (Available < 8 || XnuRead32 (Data) != XNU_PAYLOAD_MAGIC) {
    return FALSE;
  }
  End = XnuRead32 (Data + 4);
  if (End < 24 || End > XNU_PAYLOAD_MAX_SIZE - 8 || End > Available - 8) {
    return FALSE;
  }
  End += 8;
  while (End - At >= 24) {
    UINTN Size = XnuRead32 (Data + At + 16);
    UINTN Padded = (Size + 15ULL) & ~15ULL;
    BOOLEAN Loader = TRUE;
    CONST CHAR8 Name[16] = "loader.efi";

    if (Data[At] == 0) {
      for (UINTN I = 0; I < 24; I++) {
        if (Data[At + I] != 0) { return FALSE; }
      }
      if (At + 24 != End || Found == NULL) { return FALSE; }
      *Image = Found;
      *ImageSize = FoundSize;
      return TRUE;
    }
    if (XnuRead32 (Data + At + 20) != 0 || Padded > End - At - 24) {
      return FALSE;
    }
    for (UINTN I = 0; I < 16; I++) {
      if (Data[At + I] != (UINT8)Name[I]) { Loader = FALSE; }
    }
    if (Loader) {
      if (Found != NULL || Size == 0) { return FALSE; }
      Found = Data + At + 24;
      FoundSize = Size;
    }
    At += 24 + Padded;
  }
  return FALSE;
}

#endif
