/**
  Launch HackiOS's EFI loader from the reserved XNUP container.
  XNUP protocol derived from oosexgang/hackios-xnu-kernel at 8e61187098f2.
  No raw storage logging, persistence probes, reset, or ExitBootServices.
  SPDX-License-Identifier: BSD-2-Clause-Patent
**/
#include <Uefi.h>
#include <Library/DebugLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiLib.h>
#include <Library/UefiBootManagerLib.h>
#if defined(HACKIOS_ENABLE) && HACKIOS_ENABLE
#include "XnuPayload.h"
#endif

VOID
XnuLoaderMain (VOID)
{
#if defined(HACKIOS_ENABLE) && HACKIOS_ENABLE
  CONST VOID *Image;
  UINTN Size;
  EFI_HANDLE Handle;
  EFI_STATUS Status;

  if (!XnuFindLoader ((CONST UINT8 *)(UINTN)XNU_PAYLOAD_BASE,
                      XNU_PAYLOAD_MAX_SIZE, &Image, &Size)) {
    Print (L"HackiOS: missing or invalid XNUP loader; continuing normal boot.\r\n");
    return;
  }
  // Make BlockIo/FAT handles available before the resident loader starts.
  EfiBootManagerConnectAll ();
  Status = gBS->LoadImage (FALSE, gImageHandle, NULL, (VOID *)Image, Size, &Handle);
  if (EFI_ERROR (Status)) {
    Print (L"HackiOS: LoadImage failed: %r\r\n", Status);
    return;
  }
  Print (L"HackiOS: starting loader.efi; firmware remains resident.\r\n");
  Status = gBS->StartImage (Handle, NULL, NULL);
  Print (L"HackiOS: loader returned: %r\r\n", Status);
  gBS->UnloadImage (Handle);
#endif
}
