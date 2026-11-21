"""CORALIS poster entrypoint.

Copies the approved poster image (assets/entry.png) into the contest
output directory as entry.png. The image itself is a fixed asset; this
program only moves it to where the harness expects it.
"""

import os
import sys
from pathlib import Path

# Valid image signatures we accept for the bundled poster.
PNG_HEAD = b"\x89PNG\r\n\x1a\n"
JPEG_HEAD = b"\xff\xd8\xff"


def poster_bytes():
    """Read the bundled poster and check it is a real PNG or JPEG."""
    here = Path(__file__).resolve().parent
    poster = here / "assets" / "entry.png"
    if not poster.is_file():
        raise SystemExit(f"poster asset missing: {poster}")
    data = poster.read_bytes()
    if data.startswith(PNG_HEAD):
        kind = "PNG"
    elif data.startswith(JPEG_HEAD):
        kind = "JPEG"
    else:
        found = data[:8].hex()
        raise SystemExit(f"poster asset has an unknown image header: {found}")
    if len(data) == 0:
        raise SystemExit("poster asset is empty")
    return data, kind


def main():
    data, kind = poster_bytes()
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    target.write_bytes(data)
    # Re-read the written file so a partial write is caught at once.
    written = target.read_bytes()
    if written != data:
        raise SystemExit(f"output mismatch: {target} does not match the asset")
    print(f"wrote {target} ({kind}, {len(data)} bytes)")


if __name__ == "__main__":
    main()
