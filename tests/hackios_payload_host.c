/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint8_t UINT8;
typedef uint32_t UINT32;
typedef size_t UINTN;
typedef char CHAR8;
typedef void VOID;
typedef int BOOLEAN;
#define STATIC static
#define CONST const
#define TRUE 1
#define FALSE 0
#include "../Silicon/Silicium/SiliciumPkg/Library/BootManagerLib/XnuPayload.h"

int main(int argc, char **argv) {
  if (argc != 2) { return 2; }
  FILE *f = fopen(argv[1], "rb");
  if (!f) { return 2; }
  fseek(f, 0, SEEK_END);
  long length = ftell(f);
  rewind(f);
  if (length < 0 || length > (long)XNU_PAYLOAD_MAX_SIZE) { fclose(f); return 2; }
  UINT8 *data = malloc(length ? (size_t)length : 1);
  if (!data || fread(data, 1, length, f) != (size_t)length) { return 2; }
  fclose(f);
  const void *image;
  size_t size;
  int valid = XnuFindLoader(data, length, &image, &size);
  free(data);
  return valid ? 0 : 1;
}
