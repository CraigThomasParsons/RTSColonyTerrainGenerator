#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
from pathlib import Path


def build_crypt_table() -> list[int]:
    table = [0] * 0x500
    seed = 0x00100001
    for index in range(0x100):
        for i in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp1 = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp2 = seed & 0xFFFF
            table[i * 0x100 + index] = temp1 | temp2
    return table


_CRYPT_TABLE = build_crypt_table()


def hash_string(name: str, hash_type: int) -> int:
    seed1 = 0x7FED7FED
    seed2 = 0xEEEEEEEE
    for ch in name.upper():
        value = ord(ch)
        seed1 = _CRYPT_TABLE[(hash_type << 8) + value] ^ (seed1 + seed2)
        seed1 &= 0xFFFFFFFF
        seed2 = value + seed1 + seed2 + ((seed2 << 5) & 0xFFFFFFFF) + 3
        seed2 &= 0xFFFFFFFF
    return seed1 & 0xFFFFFFFF


def hash_for_table(name: str) -> int:
    seed1 = 0x7FED7FED
    seed2 = 0xEEEEEEEE
    hash_type = 3
    for ch in name.upper():
        value = ord(ch)
        seed1 = _CRYPT_TABLE[(hash_type << 8) + value] ^ (seed1 + seed2)
        seed1 &= 0xFFFFFFFF
        seed2 = value + seed1 + seed2 + ((seed2 << 5) & 0xFFFFFFFF) + 3
        seed2 &= 0xFFFFFFFF
    return seed1 & 0xFFFFFFFF


def decrypt_table(data: bytes, key: int) -> bytes:
    seed1 = key & 0xFFFFFFFF
    seed2 = 0xEEEEEEEE
    out = bytearray()
    length = len(data) - (len(data) % 4)
    for i in range(0, length, 4):
        seed2 = (seed2 + _CRYPT_TABLE[0x400 + (seed1 & 0xFF)]) & 0xFFFFFFFF
        value = struct.unpack("<I", data[i : i + 4])[0]
        decrypted = (value ^ (seed1 + seed2)) & 0xFFFFFFFF
        seed1 = (((~seed1 << 0x15) + 0x11111111) | (seed1 >> 0x0B)) & 0xFFFFFFFF
        seed2 = (decrypted + seed2 + ((seed2 << 5) & 0xFFFFFFFF) + 3) & 0xFFFFFFFF
        out.extend(struct.pack("<I", decrypted))
    return bytes(out)


def find_block_index(
    name: str, hash_table: bytes, hash_entries: int
) -> int | None:
    hash_a = hash_string(name, 1)
    hash_b = hash_string(name, 2)
    start = hash_a % hash_entries
    for i in range(hash_entries):
        idx = (start + i) % hash_entries
        entry = hash_table[idx * 16 : (idx + 1) * 16]
        ha, hb, _locale, _platform, block_index = struct.unpack("<IIHHI", entry)
        if block_index == 0xFFFFFFFF:
            continue
        if ha == hash_a and hb == hash_b:
            return block_index
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_scm.py <path-to-map.scm>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[SCM] Missing file: {path}")
        return 1

    data = path.read_bytes()
    if len(data) < 32 or data[:4] != b"MPQ\x1a":
        print("[SCM] Missing MPQ header")
        return 1

    header_size, archive_size, fmt_ver, sector_shift = struct.unpack_from("<I I H H", data, 4)
    hash_off, block_off, hash_entries, block_entries = struct.unpack_from("<I I I I", data, 16)
    if hash_entries == 0 or block_entries == 0:
        print("[SCM] Missing MPQ tables")
        return 1

    hash_bytes = data[hash_off : hash_off + hash_entries * 16]
    block_bytes = data[block_off : block_off + block_entries * 16]
    if len(hash_bytes) < hash_entries * 16 or len(block_bytes) < block_entries * 16:
        print("[SCM] MPQ tables truncated")
        return 1

    hash_table = decrypt_table(hash_bytes, hash_for_table("(hash table)"))
    block_table = decrypt_table(block_bytes, hash_for_table("(block table)"))

    chk_name = "staredit\\scenario.chk"
    block_index = find_block_index(chk_name, hash_table, hash_entries)
    if block_index is None or block_index >= block_entries:
        print("[SCM] Missing staredit\\scenario.chk")
        return 1

    entry = block_table[block_index * 16 : (block_index + 1) * 16]
    offset, comp_size, file_size, flags = struct.unpack("<IIII", entry)
    if file_size == 0 or comp_size == 0:
        print("[SCM] staredit\\scenario.chk size invalid")
        return 1

    print("[SCM] Found staredit\\scenario.chk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
