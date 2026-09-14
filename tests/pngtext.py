"""Read the chunks and the tEXt fields of a PNG. Test helper, stdlib only."""

import struct
import zlib


def png_chunks(data):
    """Return [(tag, payload)] in file order. Raise on a bad CRC."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    chunks = []
    pos = 8
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        payload = data[pos + 8:pos + 8 + length]
        crc, = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(tag + payload) & 0xFFFFFFFF, \
            f"bad CRC on {tag!r}"
        chunks.append((tag, payload))
        pos += 12 + length
    return chunks


def png_text(data):
    """Return the tEXt fields of a PNG as {keyword: text}."""
    fields = {}
    for tag, payload in png_chunks(data):
        if tag == b"tEXt":
            keyword, _, text = payload.partition(b"\x00")
            fields[keyword.decode("latin-1")] = text.decode("latin-1")
    return fields
