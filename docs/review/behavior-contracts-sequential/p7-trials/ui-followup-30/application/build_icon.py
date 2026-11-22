"""Build the trial's small folder favicon using the standard-library ICO format.

This is an application-owned static asset, not an observer route or runtime hook.
It fixes Chromium's default /favicon.ico request without changing bound app code.
"""

import argparse
from pathlib import Path
import struct


def folder_icon():
    """Encode a 32 x 32 BGRA bitmap and its transparency mask in one ICO entry."""
    size = 32
    pixels, mask = bytearray(), bytearray()
    for y in reversed(range(size)):
        mask_row = 0
        for x in range(size):
            tab = 5 <= x < 16 and 7 <= y < 12
            body = 4 <= x < 28 and 11 <= y < 25
            opaque = tab or body
            # Teal folder with a light top fold, matching the trial's file cabinet.
            rgb = (122, 185, 179) if body and y < 14 else (31, 110, 107)
            pixels.extend((*reversed(rgb), 255) if opaque else (0, 0, 0, 0))
            if not opaque:
                mask_row |= 1 << (31 - x)
        mask.extend(struct.pack(">I", mask_row))
    dib = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    body = dib + pixels + mask
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(body), 22) + body


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_bytes(folder_icon())
