import mmap, os, re, struct, zlib

from .katsuki_sub_codecs import (
    decompress as codec_decompress,
    decompress_classic_split_zlib_streams,
    decompress_pairtable_split_zlib_members,
    decompress_split_zlib_streams,
    read_classic_split_zlib_layout as codec_read_classic_split_zlib_layout,
    read_pairtable_split_zlib_wrapper,
    u16_le,
    u32_le,
)

EXT4 = {
    b"_MHK": ".khm",
    b"KFTK": ".ktf",
    b"GT1G": ".g1t",
    b"_M1G": ".g1m",
    b"_S1G": ".g1s",
    b"_S2G": ".g2s",
    b"ME1G": ".g1em",
    b"_E1G": ".g1e",
    b"_A1G": ".g1a",
    b"_A2G": ".g2a",
    b"XF1G": ".g1fx",
    b"OC1G": ".g1c",
    b"_L1G": ".g1l",
    b"_N1G": ".g1n",
    b"_H1G": ".g1h",
    b"SV1G": ".g1vs",
    b"LCSK": ".kscl",
    b"TLSK": ".kslt",
    b"KTSR": ".ktsl2stbin",
    b"KTSC": ".ktsl2asbin",
    b"KTSS": ".ktss",
    b"KOVS": ".kvs",
    b"_SPK": ".postfx",
    b"_OLS": ".sebin",
    b"OggS": ".ogg",
    b"RIFF": ".riff",
    b"1DHW": ".sed",
    b"_HBW": ".wbh",
    b"_DBW": ".wbd",
    b"KPMG": ".gmpk",
    b"KPML": ".lmpk",
    b"KPAG": ".gapk",
    b"KPEG": ".gepk",
    b"0KPB": ".bpk",
    b"KPTR": ".rtrpk",
    b"KLMD": ".mdlk",
    b"RLDM": ".mdlpack",
    b"TLDM": ".mdltexpack",
    b"GRAX": ".exarg",
    b"RFFE": ".effectpack",
    b"DAEH": ".exhead",
    b"RRRT": ".ktfkpack",
    b"RLOC": ".colpack",
    b"APDT": ".tdpack",
    b"_DRK": ".rdb",
    b"IDRK": ".rdb.bin",
    b"PDRK": ".fdata",
    b"_RNK": ".name",
    b"IRNK": ".name.bin",
    b"_DOK": ".kidsobjdb",
    b"IDOK": ".kidsobjdb.bin",
    b"RDOK": ".kidsobjdb.bin",
    b"MDLS": ".mdls",
    b"DXBC": ".dxbc",
    b"FP1G": ".fp1g",
    b"HWYX": ".hwyx",
    b"SCM_": ".scm",
    b"DLV0": ".dlv0",
    b"DLV4": ".dlv4",
    b"SV00": ".sv00",
    b"SV01": ".sv01",
    b"SV02": ".sv02",
    b"SV03": ".sv03",
    b"SV20": ".sv20",
    b"SV30": ".sv30",
    b"SV40": ".sv40",
    b"SV41": ".sv41",
    b"Act_": ".act",
    b"ET00": ".et00",
    b"ET01": ".et01",
    b"ET02": ".et02",
    b"ET03": ".et03",
    b"FT02": ".ft02",
    b"SARC": ".sarc",
    b"CRAE": ".elixir",
    b"SPKG": ".spkg",
    b"SCEN": ".scene",
    b"KPS3": ".shaderpack",
    b"QGWS": ".swg",
    b"EVIR": ".river",
    b"BGIR": ".rig",
    b"RTRE": ".ertr",
    b"DATD": ".datd",
    b"D0CL": ".lcd0",
    b"HDDB": ".hdb",
    b"RTXE": ".extra",
    b"LLOC": ".coll",
    b"ONUN": ".nuno",
    b"VNUN": ".nunv",
    b"SNUN": ".nuns",
    b"TFOS": ".soft",
    b"RIAH": ".hair",
    b"TNOC": ".cont",
    b"pkgi": ".pkginfo",
    b"DDS ": ".dds",
    b"char": ".chardata",
    b"clip": ".clip",
    b"body": ".bodybase",
    b"MSBP": ".material",
    b"tdpa": ".tdpack",
    b"HIUB": ".hiub",
    b"MDLK": ".MDLK",
    b"ipu2": ".ipu2",
    b"MESC": ".MESC",
    b"OFNI": ".INFO",
    b"_COK": ".KOC",
    b"SWGQ": ".SWGQ",
    b"DJBO": ".OBJD",
    b"WHD1": ".whd",
    b"DMIG": ".G1MD",
    b"LHSK": ".KSHL"
    
}

EXT3 = {
    b"XFT": ".xft",
    b"GT1": ".g1t",
}

EXT2 = {
    b"BM": ".bmp",
    b"XL": ".XL",
}

def log_comp_failure(log_dir: str, message: str):
    """
    Append a decompression failure message to comp_log.txt in the given folder
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "comp_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

def log_subcontainer_skip(log_dir: str, message: str):
    """
    Append subcontainer detection skip/debug messages to subcontainer_log.txt
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "subcontainer_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

def hex_head(blob: bytes, size: int = 16) -> str:
    return blob[:size].hex(" ").upper()


def ascii_head(blob: bytes, size: int = 16) -> str:
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in blob[:size])

def should_recurse_nested_payload(ext: str, chunk: bytes) -> bool:
    ext = (ext or "").lower()

    if ext in (".bin", ".kvs", ".mdlk", ".kshl"):
        return True

    # Magic based fallback, safer than relying only on extension
    if chunk[:4] in (b"MDLK", b"LHSK", b"KOVS"):
        return True

    if looks_like_split_zlib_pairtable_wrapper(chunk):
        return True

    if looks_like_classic_split_zlib(chunk):
        return True

    if read_universal_subcontainer_layout(chunk):
        return True

    return False

def looks_like_classic_split_zlib(raw: bytes) -> bool:
    return codec_read_classic_split_zlib_layout(raw) is not None


def looks_like_split_zlib(raw: bytes) -> bool:
    return looks_like_classic_split_zlib(raw) or looks_like_split_zlib_pairtable_wrapper(raw)


def looks_like_split_zlib_pairtable_wrapper(raw: bytes, *, max_count: int = 4096) -> bool:
    entries = read_pairtable_split_zlib_wrapper(raw, max_count=max_count)
    if not entries:
        return False
    for payload_off, payload_size in entries:
        if not looks_like_classic_split_zlib(raw[payload_off:payload_off + payload_size]):
            return False
    return True


def looks_like_nested_subcontainer_structure(raw: bytes, *, max_count: int = 100_000) -> bool:
    """
    Shallow structural probe for nested subcontainers, this intentionally avoids
    the heavier signature scoring so outer wrappers with inner .bin payloads can
    still be recognized as valid subcontainers
    """
    n = len(raw)
    if n < 12:
        return False

    try:
        count = struct.unpack_from("<I", raw, 0)[0]
    except struct.error:
        return False

    if 1 <= count <= max_count:
        pair_table_end = 4 + count * 8
        if pair_table_end <= n:
            positive = 0
            last_off = -1
            valid = True
            for idx in range(count):
                ent_off = 4 + idx * 8
                off = int.from_bytes(raw[ent_off:ent_off + 4], "little", signed=False)
                sz = int.from_bytes(raw[ent_off + 4:ent_off + 8], "little", signed=False)
                if sz <= 0:
                    continue
                if off < pair_table_end or off + sz > n or off < last_off:
                    valid = False
                    break
                last_off = off
                positive += 1
            if valid and positive > 0:
                return True

    if count >= 2:
        toc_table_end = 4 + count * 4
        if toc_table_end <= n:
            offsets = [int.from_bytes(raw[4 + idx * 4:8 + idx * 4], "little", signed=False) for idx in range(count)]
            valid_offsets = [off for off in offsets if toc_table_end <= off < n]
            if len(valid_offsets) >= 2:
                return True

            sizes = offsets
            if sum(sizes) > 0 and toc_table_end + sum(sizes) <= n:
                return True

    return False


def payload_looks_meaningful(raw: bytes, *, allow_split_wrapper: bool = False) -> bool:
    if not raw:
        return False
    
    if match_known_signature(raw, 0):
        return True

    if looks_like_nested_subcontainer_structure(raw):
        return True

    if allow_split_wrapper and (
        looks_like_split_zlib(raw) or looks_like_split_zlib_pairtable_wrapper(raw)
    ):
        return True

    return False


def build_contiguous_pairtable_blob(chunks: list[bytes]) -> bytes:
    rebuilt = bytearray()
    rebuilt.extend(int(len(chunks)).to_bytes(4, "little", signed=False))

    header_end = 4 + (len(chunks) * 8)
    cursor = align_up(header_end, 16)
    payload_offsets: list[int] = []
    for chunk in chunks:
        payload_offsets.append(cursor)
        rebuilt.extend(int(cursor).to_bytes(4, "little", signed=False))
        rebuilt.extend(int(len(chunk)).to_bytes(4, "little", signed=False))
        cursor = align_up(cursor + len(chunk), 16)

    if payload_offsets and len(rebuilt) < payload_offsets[0]:
        rebuilt.extend(b"\x00" * (payload_offsets[0] - len(rebuilt)))

    for chunk, payload_off in zip(chunks, payload_offsets):
        if len(rebuilt) < payload_off:
            rebuilt.extend(b"\x00" * (payload_off - len(rebuilt)))
        rebuilt.extend(chunk)
        pad_len = align_up(len(rebuilt), 16) - len(rebuilt)
        if pad_len:
            rebuilt.extend(b"\x00" * pad_len)

    return bytes(rebuilt)


def should_preserve_split_wrapper_members(members: list[tuple[bytes, str]]) -> bool:
    if not members:
        return False

    for member_blob, _member_ext in members:
        if not member_blob:
            return False
        if detect_ext(member_blob) != ".bin":
            continue
        if looks_like_nested_subcontainer_structure(member_blob):
            continue
        return False

    return True

def decompress_split_zlib_for_unpack(raw: bytes) -> tuple[bytes, str]:
    if looks_like_split_zlib_pairtable_wrapper(raw):
        members = decompress_pairtable_split_zlib_members(raw)
        if should_preserve_split_wrapper_members(members):
            return build_contiguous_pairtable_blob([member_blob for member_blob, _member_ext in members]), ".bin"
    return decompress_split_zlib_streams(raw)


def prepare_split_zlib_entry_for_unpack(raw: bytes) -> tuple[bytes, str | None, bool]:
    if looks_like_split_zlib_pairtable_wrapper(raw):
        return raw, None, False
    data, ext_hint = decompress_split_zlib_for_unpack(raw)
    return data, ext_hint, True


def read_classic_split_zlib_layout(blob: bytes):
    layout = codec_read_classic_split_zlib_layout(blob)
    if not layout:
        return None

    original_chunk_unc_sizes: list[int] = []
    chunk_offsets: list[int] = []
    between_gaps: list[bytes] = []
    previous_end = None
    for chunk in layout["chunks"]:
        ptr = chunk["offset"]
        data_start = chunk["payload_off"]
        data_end = data_start + chunk["payload_size"]
        if previous_end is None:
            leading_gap = blob[layout["header_end"]:ptr]
        else:
            between_gaps.append(blob[previous_end:ptr])
        chunk_offsets.append(ptr)
        if data_end > len(blob):
            return None
        if chunk["compressed"]:
            try:
                decomp = zlib.decompress(blob[data_start:data_end])
            except Exception:
                return None
            original_chunk_unc_sizes.append(len(decomp))
        else:
            original_chunk_unc_sizes.append(chunk["payload_size"])
        previous_end = data_end

    if previous_end is None:
        return None

    return {
        "unk0": layout["unk0"].to_bytes(2, "little", signed=False),
        "unk1": layout["unk1"].to_bytes(2, "little", signed=False),
        "file_type": layout["file_type"],
        "chunk_count": layout["chunk_count"],
        "total_unc": layout["total_unc"],
        "header_end": layout["header_end"],
        "sizes": list(layout["sizes"]),
        "chunks": [dict(chunk) for chunk in layout["chunks"]],
        "chunk_offsets": chunk_offsets,
        "leading_gap": leading_gap,
        "between_gaps": between_gaps,
        "trailing_gap": blob[previous_end:],
        "original_chunk_unc_sizes": original_chunk_unc_sizes,
    }


def resolve_unpacked_extension(data: bytes, ext_hint: str | None = None) -> str:
    ext = detect_ext(data)
    if ext in (".ini", ".txt") and b"\x00" in data[:64]:
        return ".bin"
    if ext != ".bin":
        return ext
    if ext_hint == ".g1m" and data.startswith(b"\x5F\x4D\x31\x47"):
        return ".g1m"
    if ext_hint == ".g1t" and data[:3] == b"GT1":
        return ".g1t"
    return ".bin"


def unpack_classic_split_zlib_resource(path: str, blob: bytes) -> bool:
    if not looks_like_classic_split_zlib(blob):
        return False

    try:
        merged, ext_hint = decompress_classic_split_zlib_streams(blob)
    except Exception:
        return False

    base_dir, fname = os.path.split(path)
    name_no_ext, _ = os.path.splitext(fname)
    out_dir = os.path.join(base_dir, name_no_ext)
    os.makedirs(out_dir, exist_ok=True)

    ext = resolve_unpacked_extension(merged, ext_hint)
    out_path = os.path.join(out_dir, f"000{ext}")
    with open(out_path, "wb") as handle:
        handle.write(merged)

    if ext in (".bin", ".kvs"):
        unpack_nested_resource(out_path, blob=merged)

    return True


def unpack_split_zlib_wrapper_blob(path: str, blob: bytes) -> bool:
    if not looks_like_split_zlib_pairtable_wrapper(blob):
        return False

    entries = read_pairtable_split_zlib_wrapper(blob)
    if not entries:
        return False

    base_dir, fname = os.path.split(path)
    name_no_ext, _ = os.path.splitext(fname)
    out_dir = os.path.join(base_dir, name_no_ext)
    os.makedirs(out_dir, exist_ok=True)

    for index, (payload_off, payload_size) in enumerate(entries):
        payload = blob[payload_off:payload_off + payload_size]
        child_path = os.path.join(out_dir, f"{index:03d}.bin")
        with open(child_path, "wb") as handle:
            handle.write(payload)
        unpack_nested_resource(child_path, blob=payload)

    return True

NUM_RE = re.compile(r"(\d+)")

def match_known_signature(data: bytes, off: int):
    if off < 0 or off + 4 > len(data):
        return None

    tail = data[off:]
    sig4 = data[off:off + 4]
    hit = EXT4.get(sig4)
    if hit:
        return hit

    if off + 3 <= len(data):
        sig3 = data[off:off + 3]
        hit = EXT3.get(sig3)
        if hit:
            return hit

    if off + 2 <= len(data):
        sig2 = data[off:off + 2]
        hit = EXT2.get(sig2)
        if hit:
            return hit
    hit = detect_dx9_shader_ext(data, off)
    if hit:
        return hit

    if off + 12 <= len(data):
        try:
            total_out, csize = struct.unpack_from("<II", data, off)
            if 0 < total_out <= 0x40000000 and 0 < csize <= (len(data) - (off + 8)):
                if is_zlib_header(data[off + 8:off + 10]):
                    return "zl"
        except struct.error:
            pass

    if looks_like_split_zlib(tail) or looks_like_nested_subcontainer_structure(tail):
        return ".bin"

    return None

def read_subcontainer_toc(data: bytes, *, max_count: int = 100_000):
    """
    Reads: u32 count, then count u32 offsets
    Returns count, offsets, table_end, or None
    """
    n = len(data)
    if n < 8:
        return None

    try:
        count = struct.unpack_from("<I", data, 0)[0]
    except struct.error:
        return None

    if count < 2 or count > max_count:
        return None

    table_end = 4 + count * 4
    if table_end > n:
        return None

    try:
        offsets = list(struct.unpack_from("<" + "I" * count, data, 4))
    except struct.error:
        return None

    return count, offsets, table_end


def is_real_subcontainer(raw_data: bytes, offsets: list[int], table_end: int, probe_limit: int = 8) -> bool:
    """
    Treat as a real subcontainer only if several offsets point at recognizable inner resources
    """
    uniq = sorted(set(off for off in offsets if table_end <= off < len(raw_data)))
    if len(uniq) < 2:
        return False

    hits = 0
    for off in uniq[:probe_limit]:
        if match_known_signature(raw_data, off):
            hits += 1

    return hits >= 2


def offset_layout_slot_offsets(offsets: list[int], table_end: int, blob_len: int) -> tuple[list[int], list[int] | None]:
    valid_pairs = [
        (idx, int(off))
        for idx, off in enumerate(offsets)
        if table_end <= int(off) <= blob_len
    ]
    if valid_pairs and all(left[1] <= right[1] for left, right in zip(valid_pairs, valid_pairs[1:])):
        return [off for _idx, off in valid_pairs], [idx for idx, _off in valid_pairs]

    unique_offsets = sorted(set(int(off) for off in offsets if table_end <= int(off) < blob_len))
    return unique_offsets, None


def offset_layout_slots(blob: bytes, layout: dict) -> list[tuple[int, int]]:
    blob_len = len(blob)
    slot_offsets = [int(off) for off in layout.get("slot_offsets", layout.get("unique_offsets", []))]
    slots: list[tuple[int, int]] = []
    for idx, start in enumerate(slot_offsets):
        if start < 0 or start > blob_len:
            continue
        end = slot_offsets[idx + 1] if idx + 1 < len(slot_offsets) else blob_len
        if end < start:
            continue
        slots.append((start, min(end, blob_len) - start))
    return slots


def detect_dx9_shader_ext(data: bytes, off: int = 0) -> str | None:
    """
    Detect old Direct3D 9 shader bytecode

    Common first DWORDs:
      0xFFFE0300 = vs_3_0
      0xFFFF0300 = ps_3_0
    """
    if off < 0 or off + 12 > len(data):
        return None

    token = struct.unpack_from("<I", data, off)[0]

    # Low bytes are minor/major version, high word identifies shader type
    shader_type = token & 0xFFFF0000
    major = (token >> 8) & 0xFF
    minor = token & 0xFF

    if shader_type not in (0xFFFE0000, 0xFFFF0000):
        return None

    # Keep it conservative
    if major == 0 or major > 3:
        return None

    # Strong marker seen in these blobs followed by CTAB
    if data[off + 8:off + 12] != b"CTAB":
        return None

    if shader_type == 0xFFFE0000:
        return ".vsh"
    return ".psh"

def is_zlib_header(blob: bytes) -> bool:
    if len(blob) < 2:
        return False
    cmf, flg = blob[0], blob[1]
    if (cmf & 0x0F) != 8 or (cmf >> 4) > 7:
        return False
    return ((cmf << 8) + flg) % 31 == 0


def decompress_zl_bytes(buf: bytes) -> bytes:
    if len(buf) < 8:
        raise ValueError("ZL buffer too small")

    total_out, csize = struct.unpack_from("<II", buf, 0)
    off = 8
    out = bytearray()
    chunk_idx = 0

    if csize > len(buf) - off and is_zlib_header(buf[4:6]):
        return zlib.decompress(buf[4:])

    while len(out) < total_out:
        if csize <= 0:
            raise ValueError(f"ZL chunk {chunk_idx}: invalid comp_size={csize}")
        if off + csize > len(buf):
            raise ValueError(f"ZL chunk {chunk_idx}: comp_size overruns file")

        comp = buf[off:off + csize]
        if not is_zlib_header(comp[:2]):
            break

        out.extend(zlib.decompress(comp))
        off += csize
        chunk_idx += 1

        if len(out) >= total_out:
            break
        if off + 4 > len(buf):
            break

        csize = struct.unpack_from("<I", buf, off)[0]
        off += 4

    if len(out) < total_out:
        raise ValueError(f"ZL decompressed short: got {len(out)} expected {total_out}")
    return bytes(out[:total_out])

def subcontainer_file_sort_key(path: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    nums = NUM_RE.findall(stem)
    if nums:
        try:
            return (0, int(nums[-1]), stem.lower())
        except ValueError:
            pass
    return (1, stem.lower())

def next_available_output_path(path: str) -> str:
    if not os.path.exists(path):
        return path

    root, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{root}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1

def align_up(value: int, alignment: int = 16) -> int:
    return (value + (alignment - 1)) & ~(alignment - 1)

def choose_sequential_data_start(blob: bytes, table_end: int, sizes: list[int]) -> int:
    need = sum(sizes)
    n = len(blob)
    if table_end + need > n:
        return table_end

    candidates = [table_end]
    scan_limit = min(n, table_end + 0x4000)
    for off in range(table_end, scan_limit, 4):
        if off + 4 > n:
            break
        if blob[off:off + 4] != b"\x00\x00\x00\x00":
            candidates.append(off)
            break

    best = table_end
    best_score = -1
    for cand in candidates:
        if cand < table_end or cand + need > n:
            continue
        score = 0
        cur = cand
        for sz in sizes[:min(6, len(sizes))]:
            if sz <= 0 or cur + sz > n:
                break
            if payload_looks_meaningful(blob[cur:cur + sz]):
                score += 1
            cur += sz
        if score > best_score:
            best_score = score
            best = cand
    return best

def read_sequential_subcontainer_layout(blob: bytes, *, max_count: int = 100_000):
    n = len(blob)
    if n < 8:
        return None

    try:
        count = struct.unpack_from("<I", blob, 0)[0]
    except struct.error:
        return None
    if count < 2 or count > max_count:
        return None

    table_end = 4 + count * 4
    if table_end > n:
        return None

    sizes = []
    for idx in range(count):
        off = 4 + idx * 4
        sizes.append(int.from_bytes(blob[off:off + 4], "little", signed=False))

    if sum(sizes) <= 0:
        return None

    data_start = choose_sequential_data_start(blob, table_end, sizes)
    if data_start + sum(sizes) > n:
        return None

    hits = 0
    cur = data_start
    checked = 0
    nonzero = 0
    for sz in sizes:
        if sz <= 0:
            continue
        nonzero += 1
        if cur + sz > n:
            return None
        if checked < 8:
            if payload_looks_meaningful(blob[cur:cur + sz]):
                hits += 1
            checked += 1
        cur += sz

    if nonzero < 2 or hits < 2:
        return None

    return {
        "kind": "sequential",
        "count": count,
        "sizes": sizes,
        "table_end": table_end,
        "data_start": data_start,
    }

def read_pairtable_subcontainer_layout(blob: bytes, *, max_count: int = 100_000):
    n = len(blob)
    if n < 12:
        return None

    try:
        count = struct.unpack_from("<I", blob, 0)[0]
    except struct.error:
        return None
    if count < 1 or count > max_count:
        return None

    table_end = 4 + count * 8
    if table_end > n:
        return None

    entries = []
    checked = 0
    hits = 0
    positive_indices = []
    last_off = -1
    meaningful_indices = set()

    for idx in range(count):
        ent_off = 4 + idx * 8
        off = int.from_bytes(blob[ent_off:ent_off + 4], "little", signed=False)
        sz = int.from_bytes(blob[ent_off + 4:ent_off + 8], "little", signed=False)
        entries.append((off, sz))

        if sz <= 0:
            continue
        if off < table_end or off + sz > n:
            return None
        if last_off > off:
            return None
        last_off = off
        positive_indices.append(idx)

        if checked < 8:
            if payload_looks_meaningful(blob[off:off + sz]):
                hits += 1
                meaningful_indices.add(idx)
            checked += 1

    if len(positive_indices) <= 0:
        return None
    if len(positive_indices) == 1:
        off, sz = entries[positive_indices[0]]
        if not payload_looks_meaningful(blob[off:off + sz]):
            return None
    elif hits < 2:
        positive_entries = [entries[idx] for idx in positive_indices]
        first_off, first_sz = positive_entries[0]
        leading_gap = blob[table_end:first_off]
        payload_end = max(off + sz for off, sz in positive_entries)
        trailing = blob[payload_end:n]
        tightly_packed = (
            hits >= 1
            and positive_indices[0] in meaningful_indices
            and first_off >= table_end
            and len(leading_gap) <= 0x40
            and all(b == 0 for b in leading_gap)
            and all(
                next_off == off + sz
                for (off, sz), (next_off, _next_sz) in zip(positive_entries, positive_entries[1:])
            )
            and (
                len(trailing) == 0
                or (len(trailing) <= 0x40 and all(b == 0 for b in trailing))
                or (len(trailing) == 6 and trailing[0] < 0x40 and trailing[5] in (0, 1))
            )
        )
        if not tightly_packed:
            return None

    return {
        "kind": "pairtable",
        "count": count,
        "entries": entries,
        "table_end": table_end,
        "positive_indices": positive_indices,
    }

def read_relative_pair_block(blob: bytes, start: int, block_end: int, *, max_count: int = 100_000):
    if start < 0 or block_end > len(blob) or start + 12 > block_end:
        return None

    try:
        declared_count = struct.unpack_from("<I", blob, start)[0]
        payload_base_rel = struct.unpack_from("<I", blob, start + 4)[0]
    except struct.error:
        return None

    if declared_count <= 1 or declared_count > max_count:
        return None
    if payload_base_rel < 12 or start + payload_base_rel > block_end:
        return None

    table_bytes = payload_base_rel - 12
    if table_bytes <= 0 or table_bytes % 8 != 0:
        return None

    entry_count = table_bytes // 8
    if entry_count <= 0:
        return None
    if declared_count not in (entry_count, entry_count + 1):
        return None

    entries = []
    payloads = []
    positive = 0
    hits = 0
    checked = 0
    payload_base_abs = start + payload_base_rel
    for idx in range(entry_count):
        ent_off = start + 8 + idx * 8
        rel = struct.unpack_from("<I", blob, ent_off)[0]
        sz = struct.unpack_from("<I", blob, ent_off + 4)[0]
        abs_off = payload_base_abs + rel
        if sz > 0:
            if abs_off < payload_base_abs or abs_off + sz > block_end:
                return None
            positive += 1
            payloads.append((abs_off, sz))
            if checked < 6:
                if payload_looks_meaningful(blob[abs_off:abs_off + sz]):
                    hits += 1
                checked += 1
        entries.append((rel, sz, abs_off))

    if positive <= 0:
        return None
    if checked > 0 and hits <= 0:
        return None

    reserved_start = start + 8 + entry_count * 8
    reserved = blob[reserved_start:payload_base_abs]
    return {
        "kind": "relpairblock",
        "start": start,
        "end": block_end,
        "declared_count": declared_count,
        "entry_count": entry_count,
        "payload_base_rel": payload_base_rel,
        "payload_base_abs": payload_base_abs,
        "entries": entries,
        "payloads": payloads,
        "reserved": reserved,
        "raw_bytes": blob[start:block_end],
    }

def read_relative_pairtable_block(blob: bytes, start: int, block_end: int, *, max_count: int = 100_000):
    if start < 0 or block_end > len(blob) or start + 12 > block_end:
        return None

    try:
        count = struct.unpack_from("<I", blob, start)[0]
    except struct.error:
        return None
    if count <= 0 or count > max_count:
        return None

    table_end = start + 4 + count * 8
    if table_end > block_end:
        return None

    entries = []
    last_abs = -1
    positive = 0
    hits = 0
    checked = 0
    max_payload_end = table_end
    for idx in range(count):
        ent_off = start + 4 + idx * 8
        rel = struct.unpack_from("<I", blob, ent_off)[0]
        sz = struct.unpack_from("<I", blob, ent_off + 4)[0]
        abs_off = start + rel
        if sz > 0:
            if abs_off < table_end or abs_off + sz > block_end:
                return None
            if abs_off < last_abs:
                return None
            last_abs = abs_off
            positive += 1
            max_payload_end = max(max_payload_end, abs_off + sz)
            if checked < 6:
                if payload_looks_meaningful(blob[abs_off:abs_off + sz]):
                    hits += 1
                checked += 1
        entries.append((rel, sz, abs_off))

    trailing = block_end - max_payload_end
    if positive <= 0:
        return None
    if trailing > 0x40:
        return None
    if checked > 0 and hits <= 0 and count > 1:
        return None

    return {
        "kind": "relpairtableblock",
        "start": start,
        "end": block_end,
        "count": count,
        "table_end": table_end,
        "entries": entries,
        "raw_bytes": blob[start:block_end],
    }

def read_bounded_simple_block(blob: bytes, start: int, block_end: int, *, max_count: int = 100_000):
    n = len(blob)
    if start < 0 or start + 8 > n or block_end > n or start >= block_end:
        return None

    try:
        count = struct.unpack_from("<I", blob, start)[0]
    except struct.error:
        return None
    if count <= 0 or count > min(max_count, 4096):
        return None

    entries = []
    payloads = []
    cursor = start + 4
    positive = 0
    hits = 0
    checked = 0
    for _idx in range(count):
        if cursor + 4 > block_end:
            return None
        sz = struct.unpack_from("<I", blob, cursor)[0]
        cursor += 4
        if sz < 0 or cursor + sz > block_end:
            return None
        entries.append((cursor, sz))
        if sz > 0:
            positive += 1
            payloads.append((cursor, sz))
            if checked < 6:
                if payload_looks_meaningful(blob[cursor:cursor + sz]):
                    hits += 1
                checked += 1
        cursor += sz

    trailing = block_end - cursor
    if positive <= 0 or trailing > 0x40:
        return None
    if checked > 0 and hits <= 0:
        return None

    return {
        "kind": "simpleblock",
        "start": start,
        "count": count,
        "entries": entries,
        "end": cursor,
        "block_end": block_end,
    }

def read_multiblock_subcontainer_layout(blob: bytes, *, max_count: int = 100_000):
    n = len(blob)
    if n < 0x20:
        return None

    try:
        block_count = struct.unpack_from("<I", blob, 0)[0]
        primary_block_off = struct.unpack_from("<I", blob, 4)[0]
    except struct.error:
        return None
    if block_count <= 0 or block_count > min(max_count, 4096):
        return None
    if primary_block_off < 0x10 or primary_block_off > n:
        return None

    dynamic_header_end = 8 + block_count * 4
    if dynamic_header_end > primary_block_off:
        return None

    later_block_offsets = []
    for idx in range(block_count):
        off = struct.unpack_from("<I", blob, 8 + idx * 4)[0]
        if off <= primary_block_off or off >= n:
            return None
        later_block_offsets.append(off)

    if later_block_offsets != sorted(later_block_offsets):
        return None

    tail_field_off = dynamic_header_end if dynamic_header_end + 4 <= primary_block_off else None
    last_block_span = None
    if tail_field_off is not None:
        last_block_span = struct.unpack_from("<I", blob, tail_field_off)[0]
        if last_block_span <= 0 or later_block_offsets[-1] + last_block_span > n:
            last_block_span = None

    candidate_primary_ends = sorted(set(off for off in later_block_offsets if off > primary_block_off) | {n})
    primary_block = None
    primary_block_end = None
    for candidate_end in candidate_primary_ends:
        primary_block = read_relative_pairtable_block(blob, primary_block_off, candidate_end, max_count=max_count)
        if primary_block:
            primary_block_end = candidate_end
            break
    if not primary_block:
        primary_block_end = later_block_offsets[0]
        primary_block = read_relative_pair_block(blob, primary_block_off, primary_block_end, max_count=max_count)
    if not primary_block:
        trailing_primary = read_relative_pairtable_block(blob, primary_block_off, n, max_count=max_count)
        trailer_start = min(later_block_offsets) if later_block_offsets else n
        if trailing_primary and trailer_start < n and all(b == 0 for b in blob[trailer_start:n]):
            anchor_original = int(trailing_primary["end"])
            return {
                "kind": "multiblock",
                "outer_count": block_count,
                "primary_block_off": primary_block_off,
                "tail_field_off": tail_field_off,
                "last_block_span": last_block_span,
                "later_block_offsets": later_block_offsets,
                "header_offset_deltas": [anchor_original - off for off in later_block_offsets],
                "primary_block": trailing_primary,
                "later_blocks": [],
                "wrapper_trailer": blob[anchor_original:n],
            }
        return None

    later_blocks = []
    active_later_offsets = [off for off in later_block_offsets if off >= int(primary_block["end"])]
    for idx, start in enumerate(active_later_offsets):
        if idx + 1 < len(active_later_offsets):
            end = active_later_offsets[idx + 1]
        elif last_block_span is not None:
            end = min(n, start + last_block_span)
        else:
            end = n
        if end <= start:
            return None

        block = read_relative_pairtable_block(blob, start, end, max_count=max_count)
        if not block:
            block = read_relative_pair_block(blob, start, end, max_count=max_count)
        if not block:
            block = read_bounded_simple_block(blob, start, end, max_count=max_count)
        if not block:
            if start < n and end <= n and all(b == 0 for b in blob[start:end]):
                continue
            block = {
                "kind": "rawblock",
                "start": start,
                "end": end,
                "entries": [],
                "raw_bytes": blob[start:end],
            }
        later_blocks.append(block)

    return {
        "kind": "multiblock",
        "outer_count": block_count,
        "primary_block_off": primary_block_off,
        "tail_field_off": tail_field_off,
        "last_block_span": last_block_span,
        "later_block_offsets": later_block_offsets,
        "header_offset_deltas": [
            (active_later_offsets[0] if active_later_offsets else int(primary_block["end"])) - off
            for off in later_block_offsets
        ],
        "primary_block": primary_block,
        "later_blocks": later_blocks,
        "wrapper_trailer": blob[int(primary_block["end"]):n] if not later_blocks and int(primary_block["end"]) < n and all(b == 0 for b in blob[int(primary_block["end"]):n]) else b"",
    }

def read_g1_resource_span(blob: bytes, off: int) -> int | None:
    magic4 = blob[off:off + 4]
    if magic4 == b"_M1G":
        if off + 12 > len(blob):
            return None
        size = int.from_bytes(blob[off + 8:off + 12], "little", signed=False)
    elif magic4 == b"OC1G":
        if off + 0x10 > len(blob):
            return None
        size = int.from_bytes(blob[off + 0x0C:off + 0x10], "little", signed=False)
    else:
        return None

    if size <= 0 or off + size > len(blob):
        return None
    return size

def read_known_resource_spans(blob: bytes) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []

    for magic, kind in (
        (b"MDLK", "mdlk"),
        (b"LHSK", "kshl"),
        (b"_M1G", "g1m"),
        (b"OC1G", "g1c"),
    ):
        search = 0
        while True:
            off = blob.find(magic, search)
            if off < 0:
                break

            size = None
            if kind == "mdlk":
                layout = read_mdlk_layout(blob[off:])
                if layout:
                    size = int(layout["payload_end"])
            elif kind == "kshl":
                layout = read_kshl_layout(blob[off:])
                if layout:
                    size = int(layout["size"])
            else:
                size = read_g1_resource_span(blob, off)

            if size and size > 0:
                spans.append((off, off + size, kind))
                search = off + size
            else:
                search = off + 1

    spans.sort(key=lambda item: (item[0], item[1]))
    return spans

def offsets_point_inside_known_resource_spans(blob: bytes, offsets: list[int], table_end: int) -> bool:
    candidate_offsets = sorted(set(off for off in offsets if table_end <= off < len(blob)))
    if not candidate_offsets:
        return False

    for start, end, _kind in read_known_resource_spans(blob):
        if end <= start:
            continue
        for off in candidate_offsets:
            if start < off < end:
                return True
    return False

def read_wrapper_pair_subcontainer_layout(blob: bytes, *, max_pairs: int = 512):
    """Headerless WBH/WBD wrappers store two offset/size pairs directly at byte 0"""
    n = len(blob)
    if n < 16:
        return None

    cursor = 0
    pairs = []
    entries = []
    for _pair_idx in range(max_pairs):
        if cursor + 16 > n:
            break

        try:
            wbh_off, wbh_size, wbd_off, wbd_size = struct.unpack_from("<4I", blob, cursor)
        except struct.error:
            break

        if wbh_off < 0x10 or wbh_size <= 0 or wbd_off < 0x10 or wbd_size <= 0:
            break

        wbh_abs = cursor + wbh_off
        wbd_abs = cursor + wbd_off
        wbh_end = wbh_abs + wbh_size
        wbd_end = wbd_abs + wbd_size
        if wbh_abs < cursor + 16 or wbh_end > n or wbd_abs < cursor + 16 or wbd_end > n:
            break
        if wbh_end > wbd_abs:
            break
        if blob[wbh_abs:wbh_abs + 8] != b"_HBW0000":
            break
        if blob[wbd_abs:wbd_abs + 8] != b"_DBW0000":
            break

        pair_idx = len(pairs)
        pairs.append({
            "cursor": cursor,
            "wbh_off": wbh_off,
            "wbh_size": wbh_size,
            "wbd_off": wbd_off,
            "wbd_size": wbd_size,
            "wbh_abs": wbh_abs,
            "wbd_abs": wbd_abs,
            "gap_before_wbh": blob[cursor + 16:wbh_abs],
            "gap_between": blob[wbh_end:wbd_abs],
        })
        entries.append({
            "kind": "wbh",
            "pair": pair_idx,
            "offset": wbh_abs,
            "size": wbh_size,
        })
        entries.append({
            "kind": "wbd",
            "pair": pair_idx,
            "offset": wbd_abs,
            "size": wbd_size,
        })

        next_cursor = max(wbh_end, wbd_end)
        if next_cursor <= cursor:
            break
        cursor = next_cursor

    if not pairs:
        return None

    return {
        "kind": "wrapper_pairs",
        "count": len(entries),
        "pairs": pairs,
        "entries": entries,
        "trailer": blob[cursor:],
    }

def read_universal_subcontainer_layout(blob: bytes):
    wrapper_pair_layout = read_wrapper_pair_subcontainer_layout(blob)
    if wrapper_pair_layout:
        return wrapper_pair_layout

    multiblock_layout = read_multiblock_subcontainer_layout(blob)
    if multiblock_layout:
        return multiblock_layout

    pair_layout = read_pairtable_subcontainer_layout(blob)
    if pair_layout:
        return pair_layout

    toc_info = read_subcontainer_toc(blob)
    if toc_info:
        count, offsets, table_end = toc_info
        if (
            is_real_subcontainer(blob, offsets, table_end)
            and not offsets_point_inside_known_resource_spans(blob, offsets, table_end)
        ):
            unique_offsets = sorted(set(off for off in offsets if table_end <= off < len(blob)))
            if len(unique_offsets) >= 2:
                slot_offsets, slot_source_indices = offset_layout_slot_offsets(offsets, table_end, len(blob))
                return {
                    "kind": "offsets",
                    "count": count,
                    "offsets": offsets,
                    "table_end": table_end,
                    "unique_offsets": unique_offsets,
                    "slot_offsets": slot_offsets,
                    "slot_source_indices": slot_source_indices,
                }

    return read_sequential_subcontainer_layout(blob)

def infer_sequential_alignment_from_original(blob: bytes, table_end: int, sizes: list[int]) -> int | None:
    try:
        data_start = choose_sequential_data_start(blob, table_end, sizes)
        for alignment in (4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
            if align_up(table_end, alignment) == data_start:
                return alignment
        if data_start % 16 == 0:
            return 16
        if data_start % 4 == 0:
            return 4
    except Exception:
        pass
    return None

def infer_pairtable_alignment_from_original(entries: list[tuple[int, int]], table_end: int) -> int | None:
    try:
        first_off = None
        for off, sz in entries:
            if sz > 0:
                first_off = off
                break
        if first_off is None:
            return 16

        for alignment in (4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
            if align_up(table_end, alignment) == first_off:
                return alignment
        if first_off % 16 == 0:
            return 16
        if first_off % 4 == 0:
            return 4
    except Exception:
        pass
    return None

def infer_relpair_alignment_from_original(entries: list[tuple[int, int, int]]) -> int:
    positive_rels = [rel for rel, sz, _abs_off in entries if sz > 0]
    if not positive_rels:
        return 4
    for alignment in (64, 32, 16, 8, 4):
        if all(rel % alignment == 0 for rel in positive_rels):
            return alignment
    return 4

def compute_positive_entry_gaps(entries: list[tuple], *, off_index: int = 0, size_index: int = 1) -> dict[int, int]:
    gaps: dict[int, int] = {}
    previous_end: int | None = None
    for idx, entry in enumerate(entries):
        off = int(entry[off_index])
        sz = int(entry[size_index])
        if sz <= 0:
            continue
        if previous_end is None:
            gaps[idx] = max(0, off)
        else:
            gaps[idx] = max(0, off - previous_end)
        previous_end = off + sz
    return gaps

def block_entry_offsets(block: dict) -> list[tuple[int, int]]:
    kind = block.get("kind")
    if kind in {"relpairblock", "relpairtableblock"}:
        return [(abs_off, sz) for _rel, sz, abs_off in block["entries"]]
    if kind == "simpleblock":
        return list(block["entries"])
    return []

def unique_preserve_order(items: list[int]) -> tuple[int, ...]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)

def populated_slot_indices(slots: list[tuple[int, int]]) -> list[int]:
    return [idx for idx, (_start, sz) in enumerate(slots) if sz > 0]

def unique_populated_slot_indices(slots: list[tuple[int, int]]) -> list[int]:
    seen: set[tuple[int, int]] = set()
    indices = []
    for idx, slot in enumerate(slots):
        _start, sz = slot
        if sz <= 0 or slot in seen:
            continue
        seen.add(slot)
        indices.append(idx)
    return indices

def slot_count_options(slots: list[tuple[int, int]]) -> tuple[int, ...]:
    total_count = len(slots)
    populated_count = len(populated_slot_indices(slots))
    unique_count = len(unique_populated_slot_indices(slots))
    return unique_preserve_order([unique_count, populated_count, total_count])

def format_slot_count_options(slots: list[tuple[int, int]]) -> str:
    total_count = len(slots)
    populated_count = len(populated_slot_indices(slots))
    unique_count = len(unique_populated_slot_indices(slots))

    parts = []
    if unique_count != populated_count:
        parts.append(f"{unique_count} unique populated slot(s)")
    if populated_count != total_count:
        parts.append(f"{populated_count} populated slot(s)")
    parts.append(f"{total_count} total slot(s)")
    return " or ".join(parts)

def map_chunks_to_slots(chunks: list[bytes], slots: list[tuple[int, int]], layout_label: str) -> dict[int, bytes]:
    total_count = len(slots)
    populated_indices = populated_slot_indices(slots)
    unique_indices = unique_populated_slot_indices(slots)

    if len(chunks) == total_count:
        return {idx: chunk for idx, chunk in enumerate(chunks)}

    if len(chunks) == len(populated_indices):
        return {
            slot_idx: chunk
            for slot_idx, chunk in zip(populated_indices, chunks)
        }

    if len(chunks) == len(unique_indices):
        payload_by_slot = {}
        chunk_by_range = {
            slots[slot_idx]: chunk
            for slot_idx, chunk in zip(unique_indices, chunks)
        }
        for slot_idx in populated_indices:
            payload_by_slot[slot_idx] = chunk_by_range[slots[slot_idx]]
        return payload_by_slot

    raise ValueError(
        f"Subcontainer file count mismatch. Folder has {len(chunks)} file(s), "
        f"but the original {layout_label} maps to {format_slot_count_options(slots)}."
    )

def slot_chunk_options(blob: bytes, slots: list[tuple[int, int]]) -> tuple[list[bytes], ...]:
    all_chunks: list[bytes] = []
    populated_chunks: list[bytes] = []
    unique_chunks: list[bytes] = []
    seen: set[tuple[int, int]] = set()

    for start, sz in slots:
        chunk = blob[start:start + sz] if sz > 0 else b""
        all_chunks.append(chunk)
        if sz <= 0:
            continue
        populated_chunks.append(chunk)
        slot = (start, sz)
        if slot not in seen:
            seen.add(slot)
            unique_chunks.append(chunk)

    options = []
    for chunks in (unique_chunks, populated_chunks, all_chunks):
        if not any(chunk_lists_match(chunks, existing) for existing in options):
            options.append(chunks)
    return tuple(options)

def layout_slots_from_layout(layout: dict) -> list[tuple[int, int]]:
    if layout["kind"] == "multiblock":
        slots = []
        slots.extend(block_entry_offsets(layout["primary_block"]))
        for block in layout["later_blocks"]:
            slots.extend(block_entry_offsets(block))
        return slots
    if layout["kind"] == "wrapper_pairs":
        return [(int(entry["offset"]), int(entry["size"])) for entry in layout["entries"]]
    if layout["kind"] == "sequential":
        slots = []
        cur = int(layout["data_start"])
        for sz in layout["sizes"]:
            slots.append((cur, int(sz)))
            if sz > 0:
                cur += int(sz)
        return slots
    return [(int(off), int(sz)) for off, sz in layout["entries"]]

def build_relative_pair_block(layout: dict, chunks: list[bytes]) -> bytes:
    entry_count = layout["entry_count"]
    if len(chunks) != entry_count:
        raise ValueError("Relative pair block rebuild received the wrong number of payload chunks.")

    payload_base_rel = int(layout["payload_base_rel"])
    original_entries = list(layout["entries"])
    positive_rels = [rel for rel, sz, _abs_off in original_entries if sz > 0]
    min_rel = min(positive_rels, default=0)
    preserve_layout = False
    last_end = -1
    for rel, sz, _abs_off in sorted(original_entries, key=lambda item: item[0]):
        if sz <= 0:
            continue
        if rel < last_end:
            preserve_layout = True
            break
        last_end = rel + sz

    new_entries: list[tuple[int, int]] = []
    if preserve_layout:
        for (rel, _old_sz, _abs_off), chunk in zip(original_entries, chunks):
            new_entries.append((rel if chunk else 0, len(chunk)))
    else:
        gap_before = compute_positive_entry_gaps(original_entries, off_index=0, size_index=1)
        previous_end_new: int | None = None
        for idx, chunk in enumerate(chunks):
            if chunk:
                rel_cursor = gap_before.get(idx, min_rel if previous_end_new is None else 0) if previous_end_new is None else previous_end_new + gap_before.get(idx, 0)
                new_entries.append((rel_cursor, len(chunk)))
                previous_end_new = rel_cursor + len(chunk)
            else:
                new_entries.append((0, 0))

    reserved = layout.get("reserved", b"")
    rebuilt = bytearray(layout.get("raw_bytes", b""))
    minimum_header = payload_base_rel
    if len(rebuilt) < minimum_header:
        rebuilt.extend(b"\x00" * (minimum_header - len(rebuilt)))

    struct.pack_into("<I", rebuilt, 0, int(layout["declared_count"]))
    struct.pack_into("<I", rebuilt, 4, payload_base_rel)
    for idx, (rel_off, sz) in enumerate(new_entries):
        struct.pack_into("<I", rebuilt, 8 + idx * 8, int(rel_off))
        struct.pack_into("<I", rebuilt, 8 + idx * 8 + 4, int(sz))

    reserved_start = 8 + len(new_entries) * 8
    if reserved_start + len(reserved) > len(rebuilt):
        rebuilt.extend(b"\x00" * (reserved_start + len(reserved) - len(rebuilt)))
    rebuilt[reserved_start:reserved_start + len(reserved)] = reserved
    if len(rebuilt) < payload_base_rel:
        rebuilt.extend(b"\x00" * (payload_base_rel - len(rebuilt)))
    elif len(rebuilt) > payload_base_rel:
        pass

    written_ranges: list[tuple[int, int]] = []
    for (rel_off, old_sz, _old_abs_off), chunk in zip(original_entries, chunks):
        if old_sz > len(chunk):
            abs_off = payload_base_rel + rel_off
            zero_start = abs_off + len(chunk)
            zero_end = abs_off + old_sz
            if len(rebuilt) < zero_end:
                rebuilt.extend(b"\x00" * (zero_end - len(rebuilt)))
            rebuilt[zero_start:zero_end] = b"\x00" * max(0, zero_end - zero_start)

    for (rel_off, _sz), chunk in zip(new_entries, chunks):
        if not chunk:
            continue
        abs_off = payload_base_rel + rel_off
        if len(rebuilt) < abs_off + len(chunk):
            rebuilt.extend(b"\x00" * (abs_off + len(chunk) - len(rebuilt)))
        for prev_start, prev_end in written_ranges:
            overlap_start = max(abs_off, prev_start)
            overlap_end = min(abs_off + len(chunk), prev_end)
            if overlap_start < overlap_end:
                chunk_slice = chunk[overlap_start - abs_off:overlap_end - abs_off]
                rebuilt_slice = rebuilt[overlap_start:overlap_end]
                if chunk_slice != rebuilt_slice:
                    raise ValueError(
                        "Rebuild conflict: overlapping relative-pair payloads now contain different bytes."
                    )
        rebuilt[abs_off:abs_off + len(chunk)] = chunk
        written_ranges.append((abs_off, abs_off + len(chunk)))

    return bytes(rebuilt)

def build_relative_pairtable_block(layout: dict, chunks: list[bytes]) -> bytes:
    count = layout["count"]
    if len(chunks) != count:
        raise ValueError("Relative pair-table block rebuild received the wrong number of payload chunks.")

    new_entries: list[tuple[int, int]] = []
    gap_before = compute_positive_entry_gaps(layout["entries"], off_index=0, size_index=1)
    previous_end_new: int | None = None
    for idx, ((rel, _old_sz, _abs_off), chunk) in enumerate(zip(layout["entries"], chunks)):
        if chunk:
            rel_off = gap_before.get(idx, rel) if previous_end_new is None else previous_end_new + gap_before.get(idx, 0)
            new_entries.append((rel_off, len(chunk)))
            previous_end_new = rel_off + len(chunk)
        else:
            new_entries.append((0, 0))

    rebuilt = bytearray(layout.get("raw_bytes", b""))
    minimum_header = 4 + count * 8
    if len(rebuilt) < minimum_header:
        rebuilt.extend(b"\x00" * (minimum_header - len(rebuilt)))

    struct.pack_into("<I", rebuilt, 0, int(count))
    for idx, (rel_off, sz) in enumerate(new_entries):
        struct.pack_into("<I", rebuilt, 4 + idx * 8, int(rel_off))
        struct.pack_into("<I", rebuilt, 4 + idx * 8 + 4, int(sz))

    written_ranges: list[tuple[int, int]] = []
    for (rel_off, old_sz, _old_abs_off), chunk in zip(layout["entries"], chunks):
        if old_sz > len(chunk):
            zero_start = rel_off + len(chunk)
            zero_end = rel_off + old_sz
            if len(rebuilt) < zero_end:
                rebuilt.extend(b"\x00" * (zero_end - len(rebuilt)))
            rebuilt[zero_start:zero_end] = b"\x00" * max(0, zero_end - zero_start)

    for (rel_off, _sz), chunk in zip(new_entries, chunks):
        if not chunk:
            continue
        if len(rebuilt) < rel_off + len(chunk):
            rebuilt.extend(b"\x00" * (rel_off + len(chunk) - len(rebuilt)))
        for prev_start, prev_end in written_ranges:
            overlap_start = max(rel_off, prev_start)
            overlap_end = min(rel_off + len(chunk), prev_end)
            if overlap_start < overlap_end:
                chunk_slice = chunk[overlap_start - rel_off:overlap_end - rel_off]
                rebuilt_slice = rebuilt[overlap_start:overlap_end]
                if chunk_slice != rebuilt_slice:
                    raise ValueError(
                        "Rebuild conflict: overlapping relative pair-table payloads now contain different bytes."
                    )
        rebuilt[rel_off:rel_off + len(chunk)] = chunk
        written_ranges.append((rel_off, rel_off + len(chunk)))

    return bytes(rebuilt)

def build_simple_block(chunks: list[bytes]) -> bytes:
    rebuilt = bytearray()
    rebuilt.extend(int(len(chunks)).to_bytes(4, "little", signed=False))
    for chunk in chunks:
        rebuilt.extend(int(len(chunk)).to_bytes(4, "little", signed=False))
        rebuilt.extend(chunk)
    return bytes(rebuilt)

def iter_layout_payload_ranges(blob: bytes, layout: dict) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    blob_len = len(blob)

    if layout["kind"] == "multiblock":
        for abs_off, sz in block_entry_offsets(layout["primary_block"]):
            if sz > 0 and abs_off + sz <= blob_len:
                ranges.append((abs_off, sz))
        for block in layout["later_blocks"]:
            for abs_off, sz in block_entry_offsets(block):
                if sz > 0 and abs_off + sz <= blob_len:
                    ranges.append((abs_off, sz))
        return ranges

    if layout["kind"] == "wrapper_pairs":
        for entry in layout["entries"]:
            start = int(entry["offset"])
            sz = int(entry["size"])
            if sz > 0 and start + sz <= blob_len:
                ranges.append((start, sz))
        return ranges

    if layout["kind"] == "offsets":
        for start, sz in offset_layout_slots(blob, layout):
            if sz > 0 and start + sz <= blob_len:
                ranges.append((start, sz))
        return ranges

    if layout["kind"] == "sequential":
        cur = int(layout["data_start"])
        for sz in layout["sizes"]:
            if sz <= 0:
                continue
            if cur + sz > blob_len:
                break
            ranges.append((cur, sz))
            cur += sz
        return ranges

    for off, sz in layout["entries"]:
        if sz > 0 and off + sz <= blob_len:
            ranges.append((off, sz))
    return ranges

def estimate_layout_payload_end(blob: bytes, layout: dict) -> int:
    payload_ranges = iter_layout_payload_ranges(blob, layout)
    if not payload_ranges:
        return len(blob)
    return max(start + sz for start, sz in payload_ranges)

def layout_expected_file_counts(layout: dict) -> tuple[int, ...]:
    if layout["kind"] == "offsets":
        populated_count = len(layout["unique_offsets"])
        total_count = len(layout.get("slot_offsets") or layout["unique_offsets"])
        return unique_preserve_order([populated_count, total_count])
    return slot_count_options(layout_slots_from_layout(layout))

def get_single_nested_subcontainer_payload(blob: bytes, layout: dict):
    payload_ranges = iter_layout_payload_ranges(blob, layout)
    if len(payload_ranges) != 1:
        return None

    off, sz = payload_ranges[0]
    payload = blob[off:off + sz]
    if payload[:4] == b"KOVS":
        return {"blob": payload, "kind": "kvs", "trailer": b""}
    if looks_like_split_zlib_pairtable_wrapper(payload):
        return None
    nested_layout = read_universal_subcontainer_layout(payload)
    if not nested_layout:
        return None

    payload_end = estimate_layout_payload_end(payload, nested_layout)
    if payload_end <= 0 or payload_end > len(payload):
        payload_end = len(payload)

    return {
        "blob": payload[:payload_end],
        "kind": "subcontainer",
        "layout": nested_layout,
        "trailer": payload[payload_end:],
    }

def rebuild_wrapper_pair_subcontainer_raw_from_chunks(original_raw: bytes, layout: dict, chunks: list[bytes]) -> bytes:
    entries = layout["entries"]
    slots = layout_slots_from_layout(layout)
    payload_by_slot = map_chunks_to_slots(chunks, slots, "wrapper-pair layout")
    slot_chunks = [payload_by_slot.get(idx, b"") for idx in range(len(slots))]

    rebuilt = bytearray()
    chunk_index = 0
    for pair in layout["pairs"]:
        wbh_chunk = slot_chunks[chunk_index]
        wbd_chunk = slot_chunks[chunk_index + 1]
        chunk_index += 2

        gap_before_wbh = pair.get("gap_before_wbh", b"")
        gap_between = pair.get("gap_between", b"")
        wbh_off = 16 + len(gap_before_wbh)
        wbd_off = wbh_off + len(wbh_chunk) + len(gap_between)

        rebuilt.extend(int(wbh_off).to_bytes(4, "little", signed=False))
        rebuilt.extend(int(len(wbh_chunk)).to_bytes(4, "little", signed=False))
        rebuilt.extend(int(wbd_off).to_bytes(4, "little", signed=False))
        rebuilt.extend(int(len(wbd_chunk)).to_bytes(4, "little", signed=False))
        rebuilt.extend(gap_before_wbh)
        rebuilt.extend(wbh_chunk)
        rebuilt.extend(gap_between)
        rebuilt.extend(wbd_chunk)

    rebuilt.extend(layout.get("trailer", b""))

    return bytes(rebuilt)

def rebuild_subcontainer_raw_from_chunks(original_raw: bytes, layout: dict, chunks: list[bytes]) -> bytes:
    if layout["kind"] == "multiblock":
        slots = layout_slots_from_layout(layout)
        payload_by_slot = map_chunks_to_slots(chunks, slots, "multi-block layout")
        slot_chunks = [payload_by_slot.get(idx, b"") for idx in range(len(slots))]

        chunk_iter = iter(slot_chunks)
        primary_chunks = [next(chunk_iter) for _entry in block_entry_offsets(layout["primary_block"])]

        later_chunk_groups = []
        for block in layout["later_blocks"]:
            later_chunk_groups.append([next(chunk_iter) for _entry in block_entry_offsets(block)])

        rebuilt = bytearray(original_raw[:layout["primary_block_off"]])
        if layout["primary_block"]["kind"] == "relpairtableblock":
            primary_bytes = build_relative_pairtable_block(layout["primary_block"], primary_chunks)
        else:
            primary_bytes = build_relative_pair_block(layout["primary_block"], primary_chunks)
        rebuilt.extend(primary_bytes)

        later_offsets = []
        for block, block_chunks in zip(layout["later_blocks"], later_chunk_groups):
            block_start = align_up(len(rebuilt), 4)
            original_start = int(block.get("start", block_start))
            if original_start >= block_start:
                block_start = original_start
            if len(rebuilt) < block_start:
                rebuilt.extend(b"\x00" * (block_start - len(rebuilt)))
            later_offsets.append(block_start)
            if block["kind"] == "rawblock":
                rebuilt.extend(block.get("raw_bytes", b""))
            elif block["kind"] == "simpleblock":
                rebuilt.extend(build_simple_block(block_chunks))
            elif block["kind"] == "relpairtableblock":
                rebuilt.extend(build_relative_pairtable_block(block, block_chunks))
            else:
                rebuilt.extend(build_relative_pair_block(block, block_chunks))

        struct.pack_into("<I", rebuilt, 0, int(layout["outer_count"]))
        struct.pack_into("<I", rebuilt, 4, int(layout["primary_block_off"]))
        anchor_new = later_offsets[0] if later_offsets else len(rebuilt)
        for idx, delta in enumerate(layout.get("header_offset_deltas", [])):
            struct.pack_into("<I", rebuilt, 8 + idx * 4, int(anchor_new - delta))
        wrapper_trailer = layout.get("wrapper_trailer", b"")
        if wrapper_trailer and not later_offsets:
            rebuilt.extend(wrapper_trailer)
        tail_field_off = layout.get("tail_field_off")
        if tail_field_off is not None:
            header_offsets = [
                int.from_bytes(rebuilt[8 + idx * 4:12 + idx * 4], "little", signed=False)
                for idx in range(int(layout["outer_count"]))
            ]
            last_header_offset = max(header_offsets) if header_offsets else anchor_new
            tail_span = len(rebuilt) - last_header_offset
            struct.pack_into("<I", rebuilt, tail_field_off, int(tail_span))

        return bytes(rebuilt)

    if layout["kind"] == "wrapper_pairs":
        return rebuild_wrapper_pair_subcontainer_raw_from_chunks(original_raw, layout, chunks)

    if layout["kind"] == "offsets":
        slot_offsets = list(layout.get("slot_offsets") or layout["unique_offsets"])
        slots = offset_layout_slots(original_raw, layout)
        payload_by_slot = map_chunks_to_slots(chunks, slots, "TOC")

        prefix_end = slot_offsets[0] if slot_offsets else layout["table_end"]
        rebuilt_prefix = bytearray(original_raw[:prefix_end])
        rebuilt_payload = bytearray()
        new_slot_offsets = []

        cursor = prefix_end
        for slot_idx in range(len(slot_offsets)):
            new_slot_offsets.append(cursor)
            chunk = payload_by_slot.get(slot_idx, b"")
            rebuilt_payload.extend(chunk)
            cursor += len(chunk)

        struct.pack_into("<I", rebuilt_prefix, 0, layout["count"])
        slot_source_indices = layout.get("slot_source_indices")
        if slot_source_indices is not None and len(slot_source_indices) == len(new_slot_offsets):
            for slot_idx, source_idx in enumerate(slot_source_indices):
                struct.pack_into("<I", rebuilt_prefix, 4 + int(source_idx) * 4, new_slot_offsets[slot_idx])
        else:
            offset_map = {old_offset: new_offset for old_offset, new_offset in zip(slot_offsets, new_slot_offsets)}
            for idx, old_offset in enumerate(layout["offsets"]):
                struct.pack_into("<I", rebuilt_prefix, 4 + idx * 4, offset_map.get(old_offset, old_offset))

        return bytes(rebuilt_prefix) + bytes(rebuilt_payload)

    if layout["kind"] == "sequential":
        sizes = layout["sizes"]
        slots = layout_slots_from_layout(layout)
        payload_by_slot = map_chunks_to_slots(chunks, slots, "sequential TOC")
        slot_chunks = [payload_by_slot.get(idx, b"") for idx in range(len(slots))]

        data_start = int(layout["data_start"])
        pad_len = max(0, data_start - layout["table_end"])
        rebuilt = bytearray()
        rebuilt.extend(int(layout["count"]).to_bytes(4, "little", signed=False))
        for chunk in slot_chunks:
            rebuilt.extend(int(len(chunk)).to_bytes(4, "little", signed=False))
        if pad_len:
            rebuilt.extend(b"\x00" * pad_len)
        for chunk in slot_chunks:
            rebuilt.extend(chunk)
        return bytes(rebuilt)

    entries = layout["entries"]
    slots = layout_slots_from_layout(layout)
    payload_by_slot = map_chunks_to_slots(chunks, slots, "pair-table TOC")

    header_size = 4 + len(entries) * 8
    gap_before = compute_positive_entry_gaps(entries, off_index=0, size_index=1)
    offsets = []
    sizes = []
    previous_end_new: int | None = None
    for idx, (_old_off, old_sz) in enumerate(entries):
        chunk = payload_by_slot.get(idx)
        if chunk is None:
            chunk = b"" if old_sz > 0 else b""
        sz = len(chunk)
        sizes.append(sz)
        if sz > 0:
            off = gap_before.get(idx, header_size) if previous_end_new is None else previous_end_new + gap_before.get(idx, 0)
            offsets.append(off)
            previous_end_new = off + sz
        else:
            offsets.append(0)

    rebuilt = bytearray()
    rebuilt.extend(int(layout["count"]).to_bytes(4, "little", signed=False))
    for off, sz in zip(offsets, sizes):
        rebuilt.extend(int(off).to_bytes(4, "little", signed=False))
        rebuilt.extend(int(sz).to_bytes(4, "little", signed=False))

    if offsets:
        first_positive = next((off for off, sz in zip(offsets, sizes) if sz > 0), 0)
        cur = len(rebuilt)
        if first_positive > cur:
            rebuilt.extend(b"\x00" * (first_positive - cur))

    for idx, chunk in sorted(payload_by_slot.items()):
        if not chunk:
            continue
        target_off = offsets[idx]
        cur = len(rebuilt)
        if cur < target_off:
            rebuilt.extend(b"\x00" * (target_off - cur))
        rebuilt.extend(chunk)

    return bytes(rebuilt)

def try_unpack_subcontainer_blob(blob: bytes, out_dir: str) -> bool:
    if looks_like_split_zlib_pairtable_wrapper(blob):
        return False
    layout = read_universal_subcontainer_layout(blob)
    if not layout:
        return False

    nested_payload = get_single_nested_subcontainer_payload(blob, layout)
    if nested_payload:
        os.makedirs(out_dir, exist_ok=True)
        inner_blob = nested_payload["blob"]
        if nested_payload["kind"] == "kvs":
            return unpack_kvs_blob(inner_blob, out_dir)
        return try_unpack_subcontainer_blob(inner_blob, out_dir)

    def write_payload_file(out_path: str, chunk: bytes, *, allow_nested: bool = True):
        with open(out_path, "wb") as fout:
            fout.write(chunk)
        if allow_nested:
            unpack_nested_resource(out_path, blob=chunk)

    os.makedirs(out_dir, exist_ok=True)
    if layout["kind"] == "multiblock":
        out_index = 0
        for abs_off, sz in block_entry_offsets(layout["primary_block"]):
            if sz <= 0:
                out_path = os.path.join(out_dir, f"{out_index:03d}.bin")
                with open(out_path, "wb") as fout:
                    fout.write(b"")
                out_index += 1
                continue
            chunk = blob[abs_off:abs_off + sz]
            inner_ext = resolve_nested_payload_extension(chunk)
            out_path = os.path.join(out_dir, f"{out_index:03d}{inner_ext}")
            write_payload_file(
                out_path,
                chunk,
                allow_nested=should_recurse_nested_payload(inner_ext, chunk),
            )
            out_index += 1

        for block in layout["later_blocks"]:
            for start, sz in block_entry_offsets(block):
                if sz <= 0:
                    out_path = os.path.join(out_dir, f"{out_index:03d}.bin")
                    with open(out_path, "wb") as fout:
                        fout.write(b"")
                    out_index += 1
                    continue
                chunk = blob[start:start + sz]
                inner_ext = resolve_nested_payload_extension(chunk)
                out_path = os.path.join(out_dir, f"{out_index:03d}{inner_ext}")
                write_payload_file(
                    out_path,
                    chunk,
                    allow_nested=should_recurse_nested_payload(inner_ext, chunk),
                )
                out_index += 1
    elif layout["kind"] == "wrapper_pairs":
        for idx, (start, sz) in enumerate(iter_layout_payload_ranges(blob, layout)):
            chunk = blob[start:start + sz]
            inner_ext = resolve_nested_payload_extension(chunk)
            out_path = os.path.join(out_dir, f"entry_{idx:03d}{inner_ext}")
            write_payload_file(
                out_path,
                chunk,
                allow_nested=should_recurse_nested_payload(inner_ext, chunk),
            )
    elif layout["kind"] == "offsets":
        for idx, (start, sz) in enumerate(offset_layout_slots(blob, layout)):
            if sz <= 0:
                out_path = os.path.join(out_dir, f"entry_{idx:03d}.bin")
                with open(out_path, "wb") as fout:
                    fout.write(b"")
                continue
            chunk = blob[start:start + sz]
            inner_ext = resolve_nested_payload_extension(chunk)
            out_path = os.path.join(out_dir, f"entry_{idx:03d}{inner_ext}")
            write_payload_file(
                out_path,
                chunk,
                allow_nested=should_recurse_nested_payload(inner_ext, chunk),
            )
    elif layout["kind"] == "sequential":
        cur = layout["data_start"]
        for idx, sz in enumerate(layout["sizes"]):
            if sz <= 0:
                out_path = os.path.join(out_dir, f"{idx:03d}.bin")
                with open(out_path, "wb") as fout:
                    fout.write(b"")
                continue
            if cur + sz > len(blob):
                break
            chunk = blob[cur:cur + sz]
            cur += sz
            inner_ext = resolve_nested_payload_extension(chunk)
            out_path = os.path.join(out_dir, f"{idx:03d}{inner_ext}")
            write_payload_file(
                out_path,
                chunk,
                allow_nested=should_recurse_nested_payload(inner_ext, chunk),
            )
    else:
        for idx, (off, sz) in enumerate(layout["entries"]):
            if sz <= 0:
                out_path = os.path.join(out_dir, f"{idx:03d}.bin")
                with open(out_path, "wb") as fout:
                    fout.write(b"")
                continue
            if off + sz > len(blob):
                break
            chunk = blob[off:off + sz]
            inner_ext = resolve_nested_payload_extension(chunk)
            out_path = os.path.join(out_dir, f"{idx:03d}{inner_ext}")
            write_payload_file(
                out_path,
                chunk,
                allow_nested=should_recurse_nested_payload(inner_ext, chunk),
            )
    return True

def unpack_kvs_blob(blob: bytes, out_dir: str) -> bool:
    n = len(blob)
    if n < 32 or blob[:4] != b"KOVS":
        return False

    os.makedirs(out_dir, exist_ok=True)
    pos = 0
    index = 0
    while True:
        if pos + 32 > n:
            break

        if blob[pos:pos + 4] != b"KOVS":
            found = False
            scan = pos
            while scan + 4 <= n:
                if blob[scan:scan + 4] == b"KOVS":
                    pos = scan
                    found = True
                    break
                scan += 4
            if not found:
                break

        if pos + 32 > n:
            break

        size = int.from_bytes(blob[pos + 4:pos + 8], "little", signed=False)
        if size <= 0:
            break

        data_start = pos + 32
        data_end = data_start + size
        if data_end > n:
            break

        chunk = blob[pos:data_end]
        out_path = os.path.join(out_dir, f"{index:05d}.kvs")
        with open(out_path, "wb") as fout:
            fout.write(chunk)

        index += 1
        pos = data_end
        if pos % 16 != 0:
            pos = (pos + 15) & ~0x0F

    return index > 0

def looks_like_mdlk_blob(blob: bytes) -> bool:
    return len(blob) >= 16 and blob[:4] == b"MDLK"

def looks_like_kshl_blob(blob: bytes) -> bool:
    if len(blob) < 0xB8:
        return False
    if blob[:4] != b"LHSK":
        return False

    size = int.from_bytes(blob[0x08:0x0C], "little", signed=False)
    if size < 0xB8 or size > len(blob):
        return False

    payload_start = int.from_bytes(blob[0xB0:0xB4], "little", signed=False)
    payload_size = int.from_bytes(blob[0xB4:0xB8], "little", signed=False)

    if payload_start < 0xB8:
        return False
    if payload_size <= 0:
        return False

    return payload_start + payload_size == size

def kshl_shader_ext(blob: bytes) -> str:
    hit = detect_dx9_shader_ext(blob, 0)
    if hit:
        return hit
    return ".bin"

def read_kshl_layout(blob: bytes):
    """
    KSHL/LHSK shader container

    Observed:
      0x00: b"LHSK"
      0x04: version-ish, often b"7110"
      0x08: u32 container size
      0x10: fixed-width name/label area
      0xB0: u32 shader payload start
      0xB4: u32 shader payload size
      payload_start + payload_size == kshl_size

    This layout reader discovers child shaders by scanning the payload area for
    D3D9 shader tokens, it preserves the original header bytes and later rebuild
    patches all exact old offset/size occurrences found in the header
    """
    if not looks_like_kshl_blob(blob):
        return None

    size = int.from_bytes(blob[0x08:0x0C], "little", signed=False)
    payload_start = int.from_bytes(blob[0xB0:0xB4], "little", signed=False)
    payload_size = int.from_bytes(blob[0xB4:0xB8], "little", signed=False)
    payload_end = payload_start + payload_size

    if payload_start < 0xB8 or payload_end != size or payload_end > len(blob):
        return None

    payload = blob[payload_start:payload_end]

    starts: list[int] = []
    # DX9 shader starts usually begin with 00 03 FE FF/00 03 FF FF for vs_3_0/ps_3_0
    for rel in range(0, len(payload) - 12 + 1):
        abs_off = payload_start + rel
        if detect_dx9_shader_ext(blob, abs_off):
            starts.append(abs_off)

    # De-dupe just in case
    starts = sorted(set(starts))
    if not starts:
        return None

    entries = []
    for idx, abs_off in enumerate(starts):
        next_abs = starts[idx + 1] if idx + 1 < len(starts) else payload_end
        if next_abs <= abs_off:
            return None
        entries.append({
            "index": idx,
            "offset": abs_off,
            "rel_offset": abs_off - payload_start,
            "size": next_abs - abs_off,
            "ext": kshl_shader_ext(blob[abs_off:next_abs]),
        })

    return {
        "kind": "kshl",
        "size": size,
        "payload_start": payload_start,
        "payload_size": payload_size,
        "payload_end": payload_end,
        "header": blob[:payload_start],
        "entries": entries,
        "trailer": blob[payload_end:size],
    }

def unpack_kshl_blob(blob: bytes, out_dir: str) -> bool:
    layout = read_kshl_layout(blob)
    if not layout:
        return False

    os.makedirs(out_dir, exist_ok=True)

    for entry in layout["entries"]:
        idx = entry["index"]
        off = entry["offset"]
        size = entry["size"]
        ext = entry["ext"]
        chunk = blob[off:off + size]

        out_path = os.path.join(out_dir, f"{idx:03d}{ext}")
        with open(out_path, "wb") as fout:
            fout.write(chunk)

    return True

def patch_all_u32_le(buf: bytearray, start: int, end: int, old_value: int, new_value: int) -> int:
    """
    Patch every exact u32 old_value in buf[start:end] to new_value
    Used for KSHL because its header has repeated old offsets/sizes
    """
    if old_value == new_value:
        return 0

    old_bytes = int(old_value).to_bytes(4, "little", signed=False)
    new_bytes = int(new_value).to_bytes(4, "little", signed=False)

    patched = 0
    pos = start
    while True:
        hit = buf.find(old_bytes, pos, end)
        if hit < 0:
            break
        buf[hit:hit + 4] = new_bytes
        patched += 1
        pos = hit + 4

    return patched

def rebuild_kshl_blob_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    """
    Rebuild KSHL by replacing the shader payload region and patching
        u32(0x08): KSHL size
        u32(0xB4): payload size
        old shader relative offsets in header
        old shader sizes in header
        old payload end/size-ish values when they occur in header

    This is intentionally conservative
        preserves original header up to payload_start
        preserves shader count/order
        preserves no extra padding between shaders unless the shader files contain it
    """
    layout = read_kshl_layout(original_raw)
    if not layout:
        raise ValueError("Original file is not a recognized KSHL container.")

    payload_files = [
        path for path in list_folder_payload_files(folder_path)
        if os.path.splitext(path)[1].lower() in (".vsh", ".psh", ".dxbc", ".bin")
    ]

    expected = len(layout["entries"])
    if len(payload_files) != expected:
        raise ValueError(
            f"KSHL file count mismatch. Folder has {len(payload_files)} payload file(s) "
            f"but original KSHL maps to {expected} shader slot(s)."
        )

    chunks: list[bytes] = []
    for path in payload_files:
        with open(path, "rb") as handle:
            chunk = handle.read()

        if not chunk:
            raise ValueError(f"{os.path.basename(path)} is empty.")

        ext = os.path.splitext(path)[1].lower()
        if ext in (".vsh", ".psh") and not detect_dx9_shader_ext(chunk, 0):
            raise ValueError(f"{os.path.basename(path)} does not look like a DX9 shader bytecode blob.")

        chunks.append(chunk)

    original_chunks = [
        original_raw[entry["offset"]:entry["offset"] + entry["size"]]
        for entry in layout["entries"]
    ]
    if chunk_lists_match(chunks, original_chunks):
        return original_raw

    payload_start = int(layout["payload_start"])
    old_size = int(layout["size"])
    old_payload_size = int(layout["payload_size"])
    old_payload_end = int(layout["payload_end"])

    header = bytearray(original_raw[:payload_start])

    new_payload = bytearray()
    new_entries = []
    cursor_rel = 0

    for old_entry, chunk in zip(layout["entries"], chunks):
        new_entries.append({
            "old_rel": int(old_entry["rel_offset"]),
            "old_size": int(old_entry["size"]),
            "new_rel": cursor_rel,
            "new_size": len(chunk),
        })
        new_payload.extend(chunk)
        cursor_rel += len(chunk)

    new_payload_size = len(new_payload)
    new_size = payload_start + new_payload_size

    # Main known KSHL fields
    header[0x08:0x0C] = new_size.to_bytes(4, "little", signed=False)
    header[0xB0:0xB4] = payload_start.to_bytes(4, "little", signed=False)
    header[0xB4:0xB8] = new_payload_size.to_bytes(4, "little", signed=False)

    # Patch known old relative offsets and sizes wherever they appear in the pre-payload header
    for ent in new_entries:
        patch_all_u32_le(header, 0xB8, len(header), ent["old_rel"], ent["new_rel"])
        patch_all_u32_le(header, 0xB8, len(header), ent["old_size"], ent["new_size"])

    # Patch old payload size/old end if they appear in header metadata too
    patch_all_u32_le(header, 0xB8, len(header), old_payload_size, new_payload_size)
    patch_all_u32_le(header, 0xB8, len(header), old_payload_end, new_size)
    patch_all_u32_le(header, 0xB8, len(header), old_size, new_size)

    return bytes(header) + bytes(new_payload)

def rebuild_kshl_from_folder(
    folder_path: str,
    original_kshl_path: str,
    output_path: str | None = None,
):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected KSHL folder does not exist.")
    if not os.path.isfile(original_kshl_path):
        raise ValueError("Selected original KSHL file does not exist.")

    with open(original_kshl_path, "rb") as handle:
        original_blob = handle.read()

    rebuilt_blob = rebuild_kshl_blob_from_folder(folder_path, original_blob)

    output_path = write_rebuilt_resource_output(original_kshl_path, rebuilt_blob, output_path)
    return output_path, f"Rebuilt KSHL with {len(list_folder_payload_files(folder_path))} shader payload(s)."

def read_mdlk_layout(blob: bytes):
    """
    MDLK layout observed so far:

      00-07 : magic/version
      08-09 : file count, u16 little
      0A-0B : unknown/reserved, 2 bytes
      0C-0F : b"PADD"
      10-on : embedded files

    Embedded file kinds:

      _M1G/G1M:
        signature starts at entry start
        total size is u32 at entry+8
        output chunk is blob[entry : entry+size]

      OC1G/G1C:
        signature starts at entry start
        observed total size is u32 at entry+0x0C
        output chunk is blob[entry : entry+size]
    """
    n = len(blob)
    if n < 16 or blob[:4] != b"MDLK":
        return None

    count = int.from_bytes(blob[8:10], "little", signed=False)
    if count <= 0:
        return None

    header = blob[:16]
    pos = 16
    entries = []

    for idx in range(count):
        if pos + 4 > n:
            return None

        magic4 = blob[pos:pos + 4]

        if magic4 == b"_M1G":
            if pos + 12 > n:
                return None
            size = int.from_bytes(blob[pos + 8:pos + 12], "little", signed=False)
            ext = ".g1m"

        elif magic4 == b"OC1G":
            if pos + 0x10 > n:
                return None

            size = int.from_bytes(blob[pos + 0x0C:pos + 0x10], "little", signed=False)
            ext = ".g1c"

        else:
            return None

        if size <= 0 or pos + size > n:
            return None

        entries.append({
            "index": idx,
            "offset": pos,
            "size": size,
            "magic": magic4,
            "ext": ext,
        })

        pos += size

    trailer = blob[pos:]

    return {
        "kind": "mdlk",
        "magic8": blob[:8],
        "count": count,
        "unknown": blob[10:12],
        "padd": blob[12:16],
        "header": header,
        "entries": entries,
        "payload_end": pos,
        "trailer": trailer,
    }

def unpack_mdlk_blob(blob: bytes, out_dir: str) -> bool:
    layout = read_mdlk_layout(blob)
    if not layout:
        return False

    os.makedirs(out_dir, exist_ok=True)

    for idx, entry in enumerate(layout["entries"]):
        off = entry["offset"]
        size = entry["size"]
        ext = entry["ext"]
        chunk = blob[off:off + size]

        out_path = os.path.join(out_dir, f"{idx:03d}{ext}")
        with open(out_path, "wb") as fout:
            fout.write(chunk)

    return True

def read_embedded_mdlk_layout(blob: bytes):
    if looks_like_mdlk_blob(blob):
        return None

    entries = []
    search = 0
    previous_end = 0
    while True:
        off = blob.find(b"MDLK", search)
        if off < 0:
            break

        layout = read_mdlk_layout(blob[off:])
        if not layout:
            search = off + 1
            continue

        payload_end = int(layout["payload_end"])
        if payload_end <= 16 or off + payload_end > len(blob):
            search = off + 1
            continue

        if off < previous_end:
            search = off + 1
            continue

        entries.append({
            "index": len(entries),
            "offset": off,
            "size": payload_end,
            "layout": layout,
        })
        previous_end = off + payload_end
        search = previous_end

    if not entries:
        return None

    return {
        "kind": "embedded_mdlk",
        "entries": entries,
    }

def looks_like_embedded_mdlk_blob(blob: bytes) -> bool:
    return read_embedded_mdlk_layout(blob) is not None

def resolve_nested_payload_extension(chunk: bytes) -> str:
    inner_ext = detect_ext(chunk)
    if inner_ext in (".ini", ".txt") and b"\x00" in chunk[:64]:
        return ".bin"
    if inner_ext != ".bin":
        return inner_ext
    if read_universal_subcontainer_layout(chunk):
        return ".bin"
    if looks_like_split_zlib_pairtable_wrapper(chunk) or looks_like_classic_split_zlib(chunk):
        return ".bin"
    if looks_like_embedded_mdlk_blob(chunk):
        return ".MDLK"
    return ".bin"

def unpack_embedded_mdlk_blob(blob: bytes, out_dir: str) -> bool:
    layout = read_embedded_mdlk_layout(blob)
    if not layout:
        return False

    os.makedirs(out_dir, exist_ok=True)
    for entry in layout["entries"]:
        idx = entry["index"]
        off = entry["offset"]
        size = entry["size"]
        chunk = blob[off:off + size]
        out_path = os.path.join(out_dir, f"{idx:03d}.MDLK")
        with open(out_path, "wb") as fout:
            fout.write(chunk)
        unpack_nested_resource(out_path, blob=chunk)

    return True

def unpack_nested_resource(path: str, blob: bytes | None = None) -> bool:
    if not os.path.isfile(path):
        return False

    if blob is None:
        with open(path, "rb") as handle:
            blob = handle.read()

    base_dir, fname = os.path.split(path)
    name_no_ext, _ = os.path.splitext(fname)
    out_dir = os.path.join(base_dir, name_no_ext)

    if unpack_kvs_blob(blob, out_dir):
        return True
    if unpack_mdlk_blob(blob, out_dir):
        return True
    if unpack_kshl_blob(blob, out_dir):
        return True
    if unpack_split_zlib_wrapper_blob(path, blob):
        return True
    if unpack_classic_split_zlib_resource(path, blob):
        return True
    if try_unpack_subcontainer_blob(blob, out_dir):
        return True
    return unpack_embedded_mdlk_blob(blob, out_dir)

def list_folder_payload_files(folder_path: str) -> list[str]:
    folder_files = [
        os.path.join(folder_path, name)
        for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
    ]
    folder_files.sort(key=subcontainer_file_sort_key)
    return folder_files

def read_split_zlib_wrapper_layout(blob: bytes):
    entries = read_pairtable_split_zlib_wrapper(blob)
    if not entries:
        return None

    table_end = 4 + len(entries) * 8
    leading_gap = blob[table_end:entries[0][0]]
    between_gaps: list[bytes] = []
    previous_end = entries[0][0] + entries[0][1]
    for payload_off, payload_size in entries[1:]:
        between_gaps.append(blob[previous_end:payload_off])
        previous_end = payload_off + payload_size

    return {
        "entries": entries,
        "leading_gap": leading_gap,
        "between_gaps": between_gaps,
        "trailing_gap": blob[previous_end:],
    }

def infer_classic_split_zlib_alignment(layout: dict) -> tuple[int | None, list[int]]:
    chunk_offsets = list(layout.get("chunk_offsets", []))
    chunks = list(layout.get("chunks", []))
    if len(chunk_offsets) != len(chunks) or len(chunks) < 2:
        return None, []

    for alignment in (0x80, 0x40, 0x20, 0x10, 4):
        extra_gaps: list[int] = []
        ok = True
        for idx, chunk in enumerate(chunks[:-1]):
            current_end = chunk_offsets[idx] + (4 if chunk["compressed"] else 0) + chunk["payload_size"]
            base_next = align_up(current_end, alignment)
            extra_gap = chunk_offsets[idx + 1] - base_next
            if extra_gap < 0:
                ok = False
                break
            extra_gaps.append(extra_gap)
        if ok:
            return alignment, extra_gaps

    return None, []

def rebuild_kvs_blob_from_folder(folder_path: str) -> bytes:
    kvs_files = [path for path in list_folder_payload_files(folder_path) if path.lower().endswith(".kvs")]
    if not kvs_files:
        raise ValueError("Selected KVS folder does not contain any .kvs files to rebuild.")

    rebuilt = bytearray()
    for file_path in kvs_files:
        with open(file_path, "rb") as handle:
            chunk = handle.read()
        if len(chunk) < 32 or chunk[:4] != b"KOVS":
            raise ValueError(f"Invalid KVS chunk in folder rebuild: {os.path.basename(file_path)}")
        size = int.from_bytes(chunk[4:8], "little", signed=False)
        data_end = min(len(chunk), 32 + max(0, size))
        rebuilt.extend(chunk[:data_end])
        pad_len = (-len(rebuilt)) % 16
        if pad_len:
            rebuilt.extend(b"\x00" * pad_len)
    return bytes(rebuilt)

def rebuild_mdlk_blob_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    layout = read_mdlk_layout(original_raw)
    if not layout:
        raise ValueError("Original file is not a recognized MDLK container.")

    payload_files = [
        path for path in list_folder_payload_files(folder_path)
        if os.path.splitext(path)[1].lower() in (".g1m", ".g1c")
    ]

    expected = len(layout["entries"])
    if len(payload_files) != expected:
        raise ValueError(
            f"MDLK file count mismatch. Folder has {len(payload_files)} payload file(s) "
            f"but original MDLK maps to {expected} payload slot(s)."
        )

    rebuilt = bytearray()
    rebuilt.extend(layout["magic8"])
    rebuilt.extend(len(payload_files).to_bytes(2, "little", signed=False))
    rebuilt.extend(layout["unknown"])
    rebuilt.extend(layout["padd"])

    for path, original_entry in zip(payload_files, layout["entries"]):
        with open(path, "rb") as handle:
            chunk = handle.read()

        if not chunk:
            raise ValueError(f"{os.path.basename(path)} is empty.")

        magic4 = chunk[:4]
        if magic4 not in (b"_M1G", b"OC1G"):
            raise ValueError(
                f"{os.path.basename(path)} is not a supported MDLK payload "
                f"(expected _M1G or OC1G)."
            )

        if magic4 == b"_M1G":
            if len(chunk) < 12:
                raise ValueError(f"{os.path.basename(path)} is too small for G1M.")
            declared_size = int.from_bytes(chunk[8:12], "little", signed=False)
            if declared_size != len(chunk):
                chunk = bytearray(chunk)
                chunk[8:12] = len(chunk).to_bytes(4, "little", signed=False)
                chunk = bytes(chunk)

        elif magic4 == b"OC1G":
            if len(chunk) < 0x10:
                raise ValueError(f"{os.path.basename(path)} is too small for G1C.")

            declared_size = int.from_bytes(chunk[0x0C:0x10], "little", signed=False)
            if declared_size != len(chunk):
                chunk = bytearray(chunk)
                chunk[0x0C:0x10] = len(chunk).to_bytes(4, "little", signed=False)
                chunk = bytes(chunk)

        rebuilt.extend(chunk)

    rebuilt.extend(layout.get("trailer", b""))

    return bytes(rebuilt)

def rebuild_mdlk_from_folder(
    folder_path: str,
    original_mdlk_path: str,
    output_path: str | None = None,
):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected MDLK folder does not exist.")
    if not os.path.isfile(original_mdlk_path):
        raise ValueError("Selected original MDLK file does not exist.")

    with open(original_mdlk_path, "rb") as handle:
        original_blob = handle.read()

    rebuilt_blob = rebuild_mdlk_blob_from_folder(folder_path, original_blob)

    output_path = write_rebuilt_resource_output(original_mdlk_path, rebuilt_blob, output_path)
    return output_path, f"Rebuilt MDLK with {len(list_folder_payload_files(folder_path))} payload(s)."

def rebuild_embedded_mdlk_blob_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    layout = read_embedded_mdlk_layout(original_raw)
    if not layout:
        raise ValueError("Original file does not contain supported embedded MDLK resources.")

    payload_files = [
        path for path in list_folder_payload_files(folder_path)
        if os.path.splitext(path)[1].lower() == ".mdlk"
    ]

    expected = len(layout["entries"])
    if len(payload_files) != expected:
        raise ValueError(
            f"Embedded MDLK file count mismatch. Folder has {len(payload_files)} MDLK file(s) "
            f"but the original wrapper maps to {expected} embedded MDLK resource(s)."
        )

    rebuilt = bytearray()
    cursor = 0
    for path, entry in zip(payload_files, layout["entries"]):
        start = int(entry["offset"])
        end = start + int(entry["size"])
        rebuilt.extend(original_raw[cursor:start])

        chunk = read_rebuild_chunk(path)
        if not looks_like_mdlk_blob(chunk):
            raise ValueError(f"{os.path.basename(path)} is not a recognized MDLK resource.")

        rebuilt.extend(chunk)
        cursor = end

    rebuilt.extend(original_raw[cursor:])
    return bytes(rebuilt)

def rebuild_embedded_mdlk_from_folder(
    folder_path: str,
    original_resource_path: str,
    output_path: str | None = None,
):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected embedded MDLK folder doesn't exist.")
    if not os.path.isfile(original_resource_path):
        raise ValueError("Selected original embedded MDLK wrapper does not exist.")

    with open(original_resource_path, "rb") as handle:
        original_blob = handle.read()

    rebuilt_blob = rebuild_embedded_mdlk_blob_from_folder(folder_path, original_blob)

    output_path = write_rebuilt_resource_output(original_resource_path, rebuilt_blob, output_path)
    return output_path, f"Rebuilt embedded MDLK wrapper with {len(list_folder_payload_files(folder_path))} payload(s)."

def chunk_lists_match(left: list[bytes], right: list[bytes]) -> bool:
    return len(left) == len(right) and all(a == b for a, b in zip(left, right))

def extract_original_layout_chunk_options(blob: bytes, layout: dict) -> tuple[list[bytes], ...]:
    if layout["kind"] == "multiblock":
        return slot_chunk_options(blob, layout_slots_from_layout(layout))

    if layout["kind"] == "wrapper_pairs":
        return slot_chunk_options(blob, layout_slots_from_layout(layout))

    if layout["kind"] == "offsets":
        return slot_chunk_options(blob, offset_layout_slots(blob, layout))

    if layout["kind"] == "sequential":
        return slot_chunk_options(blob, layout_slots_from_layout(layout))

    return slot_chunk_options(blob, layout_slots_from_layout(layout))

def rebuild_classic_split_zlib_raw_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    layout = read_classic_split_zlib_layout(original_raw)
    if not layout:
        raise ValueError("Original file does not look like a classic split-zlib resource.")

    folder_files = list_folder_payload_files(folder_path)
    if len(folder_files) != 1:
        raise ValueError(
            f"Classic split-zlib folders must contain exactly 1 logical payload file, found {len(folder_files)}."
        )

    payload = read_rebuild_chunk(folder_files[0])
    original_payload, _original_ext = decompress_classic_split_zlib_streams(original_raw)
    if payload == original_payload:
        return original_raw

    chunk_count = int(layout["chunk_count"])
    original_unc_sizes = list(layout["original_chunk_unc_sizes"])
    alignment, extra_gap_sizes = infer_classic_split_zlib_alignment(layout)

    pieces: list[bytes] = []
    cursor = 0
    for idx in range(chunk_count):
        if idx == chunk_count - 1:
            piece = payload[cursor:]
        else:
            take = min(original_unc_sizes[idx], max(0, len(payload) - cursor))
            piece = payload[cursor:cursor + take]
            cursor += take
        pieces.append(piece)

    rebuilt = bytearray()
    rebuilt.extend(layout["unk0"])
    rebuilt.extend(int(layout["file_type"]).to_bytes(2, "little", signed=False))
    rebuilt.extend(int(layout["chunk_count"]).to_bytes(2, "little", signed=False))
    rebuilt.extend(layout["unk1"])
    rebuilt.extend(int(len(payload)).to_bytes(4, "little", signed=False))

    rebuilt_chunks: list[tuple[bool, bytes]] = []
    for piece, chunk_info in zip(pieces, layout["chunks"]):
        if chunk_info["compressed"]:
            stored = zlib.compress(piece, level=9)
            rebuilt_chunks.append((True, stored))
            rebuilt.extend(int(4 + len(stored)).to_bytes(4, "little", signed=False))
        else:
            rebuilt_chunks.append((False, piece))
            rebuilt.extend(int(len(piece)).to_bytes(4, "little", signed=False))

    rebuilt.extend(layout["leading_gap"])
    for idx, (is_compressed, stored_chunk) in enumerate(rebuilt_chunks):
        if is_compressed:
            rebuilt.extend(int(len(stored_chunk)).to_bytes(4, "little", signed=False))
        rebuilt.extend(stored_chunk)
        if idx >= len(rebuilt_chunks) - 1:
            continue
        if alignment is not None:
            target_off = align_up(len(rebuilt), alignment)
            target_off += extra_gap_sizes[idx]
            if target_off > len(rebuilt):
                rebuilt.extend(b"\x00" * (target_off - len(rebuilt)))
        elif idx < len(layout["between_gaps"]):
            rebuilt.extend(layout["between_gaps"][idx])
    rebuilt.extend(layout["trailing_gap"])

    return bytes(rebuilt)

def rebuild_split_zlib_wrapper_raw_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    layout = read_split_zlib_wrapper_layout(original_raw)
    if not layout:
        raise ValueError("Original file does not look like a split-zlib wrapper container.")

    folder_files = list_folder_payload_files(folder_path)
    expected = len(layout["entries"])
    if len(folder_files) != expected:
        raise ValueError(
            f"Wrapper file count mismatch. Folder has {len(folder_files)} file(s) but the original wrapper has {expected} member(s)."
        )

    chunks = [read_rebuild_chunk(file_path) for file_path in folder_files]
    original_chunks = [
        original_raw[payload_off:payload_off + payload_size]
        for payload_off, payload_size in layout["entries"]
    ]
    if chunk_lists_match(chunks, original_chunks):
        return original_raw

    rebuilt = bytearray()
    rebuilt.extend(int(expected).to_bytes(4, "little", signed=False))
    rebuilt.extend(b"\x00" * (expected * 8))

    cursor = len(rebuilt)
    rebuilt.extend(layout["leading_gap"])
    cursor = len(rebuilt)

    offsets: list[int] = []
    for idx, chunk in enumerate(chunks):
        offsets.append(cursor)
        rebuilt.extend(chunk)
        cursor += len(chunk)
        if idx < len(layout["between_gaps"]):
            rebuilt.extend(layout["between_gaps"][idx])
            cursor += len(layout["between_gaps"][idx])

    rebuilt.extend(layout["trailing_gap"])

    for idx, chunk in enumerate(chunks):
        struct.pack_into("<I", rebuilt, 4 + idx * 8, offsets[idx])
        struct.pack_into("<I", rebuilt, 8 + idx * 8, len(chunk))

    return bytes(rebuilt)

def rebuild_universal_subcontainer_raw_from_folder(folder_path: str, original_raw: bytes) -> bytes:
    layout = read_universal_subcontainer_layout(original_raw)
    if not layout:
        raise ValueError("Original file does not look like a supported universal subcontainer.")

    folder_files = list_folder_payload_files(folder_path)
    if not folder_files:
        raise ValueError("Selected subcontainer folder does not contain any files to rebuild.")

    folder_chunks = [read_rebuild_chunk(file_path) for file_path in folder_files]
    for original_chunks in extract_original_layout_chunk_options(original_raw, layout):
        if chunk_lists_match(folder_chunks, original_chunks):
            return original_raw

    nested_payload = get_single_nested_subcontainer_payload(original_raw, layout)
    if nested_payload and nested_payload["kind"] == "subcontainer":
        inner_layout = nested_payload["layout"]
        outer_counts = layout_expected_file_counts(layout)
        inner_counts = layout_expected_file_counts(inner_layout)
        if len(folder_chunks) in inner_counts and len(folder_chunks) not in outer_counts:
            rebuilt_inner_raw = rebuild_subcontainer_raw_from_chunks(
                nested_payload["blob"],
                inner_layout,
                folder_chunks,
            )
            wrapped_inner = rebuilt_inner_raw + nested_payload.get("trailer", b"")
            return rebuild_subcontainer_raw_from_chunks(original_raw, layout, [wrapped_inner])

    return rebuild_subcontainer_raw_from_chunks(original_raw, layout, folder_chunks)

def read_rebuild_chunk(file_path: str) -> bytes:
    with open(file_path, "rb") as handle:
        blob = handle.read()

    nested_folder = os.path.join(
        os.path.dirname(file_path),
        os.path.splitext(os.path.basename(file_path))[0],
    )
    if not os.path.isdir(nested_folder):
        return blob

    if looks_like_mdlk_blob(blob):
        return rebuild_mdlk_blob_from_folder(nested_folder, blob)

    if looks_like_kshl_blob(blob):
        return rebuild_kshl_blob_from_folder(nested_folder, blob)

    if looks_like_split_zlib_pairtable_wrapper(blob):
        return rebuild_split_zlib_wrapper_raw_from_folder(nested_folder, blob)

    if looks_like_classic_split_zlib(blob):
        return rebuild_classic_split_zlib_raw_from_folder(nested_folder, blob)

    if blob[:4] == b"KOVS":
        return rebuild_kvs_blob_from_folder(nested_folder)

    layout = read_universal_subcontainer_layout(blob)
    if layout:
        return rebuild_universal_subcontainer_raw_from_folder(nested_folder, blob)

    if looks_like_embedded_mdlk_blob(blob):
        return rebuild_embedded_mdlk_blob_from_folder(nested_folder, blob)

    return blob

def write_rebuilt_resource_output(original_resource_path: str, rebuilt_blob: bytes, output_path: str | None = None) -> str:
    if output_path is None:
        src_dir = os.path.dirname(original_resource_path)
        src_name = os.path.basename(original_resource_path)
        base, ext = os.path.splitext(src_name)
        output_path = os.path.join(src_dir, f"{base}_rebuilt{ext}")
    output_path = next_available_output_path(output_path)

    with open(output_path, "wb") as handle:
        handle.write(rebuilt_blob)

    return output_path

def rebuild_classic_split_zlib_from_folder(folder_path: str, original_resource_path: str, output_path: str | None = None):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected split-zlib folder doesn't exist.")
    if not os.path.isfile(original_resource_path):
        raise ValueError("Selected original split-zlib file doesn't exist.")

    with open(original_resource_path, "rb") as handle:
        original_blob = handle.read()
    rebuilt_blob = rebuild_classic_split_zlib_raw_from_folder(folder_path, original_blob)
    output_path = write_rebuilt_resource_output(original_resource_path, rebuilt_blob, output_path)
    return output_path, "Rebuilt classic split-zlib resource."

def rebuild_split_zlib_wrapper_from_folder(folder_path: str, original_resource_path: str, output_path: str | None = None):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected split-zlib wrapper folder doesn't exist.")
    if not os.path.isfile(original_resource_path):
        raise ValueError("Selected original split-zlib wrapper file doesn't exist.")

    with open(original_resource_path, "rb") as handle:
        original_blob = handle.read()
    rebuilt_blob = rebuild_split_zlib_wrapper_raw_from_folder(folder_path, original_blob)
    output_path = write_rebuilt_resource_output(original_resource_path, rebuilt_blob, output_path)
    return output_path, f"Rebuilt split-zlib wrapper with {len(list_folder_payload_files(folder_path))} member(s)."

def rebuild_universal_subcontainer_file_from_folder(
    folder_path: str,
    original_subcontainer_path: str,
    output_path: str | None = None,
):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected subcontainer folder does not exist.")
    if not os.path.isfile(original_subcontainer_path):
        raise ValueError("Selected original subcontainer file does not exist.")

    with open(original_subcontainer_path, "rb") as handle:
        original_blob = handle.read()
    rebuilt_blob = rebuild_universal_subcontainer_raw_from_folder(folder_path, original_blob)
    output_path = write_rebuilt_resource_output(original_subcontainer_path, rebuilt_blob, output_path)
    return output_path, f"Rebuilt subcontainer with {len(list_folder_payload_files(folder_path))} payload(s)."

def detect_ext(data: bytes) -> str:
    """Best effort extension guess from magic bytes"""
    if not data:
        return ".bin"

    head = data[:64]
    head4 = head[:4]
    head3 = head[:3]
    head2 = head[:2]

    ext = EXT4.get(head4)
    if ext:
        if ext == ".riff":
            return ".wav" if b"WAVEfmt" in head else ".riff"
        return ext

    ext = EXT3.get(head3)
    if ext:
        return ext

    ext = EXT2.get(head2)
    if ext:
        return ext

    ext = detect_dx9_shader_ext(data, 0)
    if ext:
        return ext

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if b"JFIF" in head:
        return ".jpg"
    if head.startswith(b"TIM2") or b"TIM2" in head or head4 == b"\x00\x20\xAF\x30":
        return ".tm2"
    if data.startswith(b"SShd"):
        return ".ss2"
    if data.startswith(b"SSbd"):
        return ".ss2bd"
    if data.startswith(b"IECSsreV"):
        return ".vagbank"
    if head.startswith(b"[glo"):
        return ".ini"
    if head4 == b"\x58\x4B\x4D":
        return ".xkm"
    if head4 == b"\x45\x4D\x06\x00":
        return ".EM"

    return ".bin"

def looks_like_supported_raw(raw: bytes) -> bool:
    return (
        looks_like_mdlk_blob(raw)
        or looks_like_kshl_blob(raw)
        or looks_like_split_zlib_pairtable_wrapper(raw)
        or looks_like_classic_split_zlib(raw)
        or read_universal_subcontainer_layout(raw) is not None
        or looks_like_embedded_mdlk_blob(raw)
        or raw[:4] == b"KOVS"
    )

def natural_kvs_sort_key(name: str):
    stem = os.path.splitext(name)[0]
    nums = NUM_RE.findall(stem)
    if nums:
        try:
            num = int(nums[-1])
        except ValueError:
            num = None
        return (0, num, stem.lower(), name.lower())
    return (1, stem.lower(), name.lower())

def repack_kvs_folder(
    folder_path: str,
    kvs_files: list[str],
    out_path: str,
    status,
    progress,
) -> str | None:
    kvs_files = sorted(kvs_files, key=natural_kvs_sort_key)
    total = len(kvs_files)
    if total == 0:
        status("No .kvs files inside folder to repack.", "red")
        return None

    status(f"Repacking {total} KOVS chunks into {os.path.basename(out_path)}", "blue")

    try:
        with open(out_path, "wb") as out_f:
            for idx, name in enumerate(kvs_files):
                in_path = os.path.join(folder_path, name)
                try:
                    with open(in_path, "rb") as fin:
                        blob = fin.read()
                except OSError:
                    status(f"Could not read {name}, skipping.", "red")
                    continue

                if len(blob) < 32 or not blob.startswith(b"KOVS"):
                    status(f"{name} is not a valid KOVS file, skipping.", "red")
                    continue

                size = int.from_bytes(blob[4:8], "little", signed=False)
                if size <= 0:
                    status(f"{name} has non-positive data size, skipping.", "red")
                    continue

                data_end = min(len(blob), 32 + size)
                out_f.write(blob[:data_end])
                pad_len = (-out_f.tell()) % 16
                if pad_len:
                    out_f.write(b"\x00" * pad_len)

                if progress is not None:
                    progress(idx + 1, total, f"KVS repack: {idx + 1}/{total}")

        status(f"KVS repack complete: {out_path}", "green")
        return out_path
    except OSError as e:
        status(f"Error writing KVS file: {e}", "red")
        return None

def repack_from_folder(
    folder_path: str,
    base_file_path: str | None = None,
    status_callback=None,
    progress_callback=None,
) -> str | None:
    def status(msg: str, color: str = "blue"):
        if status_callback is not None:
            status_callback(msg, color)

    def progress(done: int, total: int, note: str | None = None):
        if progress_callback is not None:
            progress_callback(done, total, note or "Repacking")

    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        status(f"Selected path is not a folder: {folder_path}", "red")
        return None

    all_files = [
        name for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
    ]
    if not all_files:
        status(f"No files found in folder: {folder_path}", "red")
        return None

    base_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    kvs_files = [name for name in all_files if name.lower().endswith(".kvs")]
    if kvs_files:
        status(f"Detected KVS chunk folder: {base_name}", "blue")
        out_path = os.path.join(parent_dir, f"{base_name}.kvs")
        return repack_kvs_folder(
            folder_path,
            kvs_files,
            out_path,
            status,
            progress,
        )

    if not base_file_path:
        status("A base unpacked source file is required for subcontainer rebuilds.", "red")
        return None

    try:
        out_path, detail = rebuild_subcontainer_from_folder(folder_path, base_file_path)
    except Exception as e:
        status(f"Subcontainer rebuild failed: {e}", "red")
        return None

    status(detail, "green")
    progress(1, 1, "Rebuild complete")
    return out_path

def update_kvs_metadata(
    game_id: str,
    kvs_subcontainer_path: str,
    metadata_bin_path: str,
    status_callback=None,
    progress_callback=None,
) -> None:
    def status(msg: str, color: str = "blue"):
        if status_callback is not None:
            status_callback(msg, color)

    def progress(done: int, total: int, note: str | None = None):
        if progress_callback is not None:
            progress_callback(done, total, note or "Updating KVS metadata")

    if (game_id or "").upper() != "WO3":
        raise NotImplementedError("Only Warriors Orochi 3 (WO3) is supported for KVS metadata updates.")

    kvs_subcontainer_path = os.path.abspath(kvs_subcontainer_path)
    metadata_bin_path = os.path.abspath(metadata_bin_path)

    if not os.path.isfile(kvs_subcontainer_path):
        raise FileNotFoundError(f"KVS subcontainer not found: {kvs_subcontainer_path}")
    if not os.path.isfile(metadata_bin_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_bin_path}")

    with open(metadata_bin_path, "rb") as mf:
        header = mf.read(8)
        if len(header) < 8:
            raise ValueError("Metadata file too small (missing 8 byte header).")
        expected = int.from_bytes(header[0:4], "little", signed=False)
        toc_start = 8
        toc_len = expected * 8
        mf.seek(0, os.SEEK_END)
        meta_size = mf.tell()
        if expected <= 0:
            raise ValueError("Metadata has non-positive entry count.")
        if toc_start + toc_len > meta_size:
            raise ValueError(
                f"Metadata TOC points beyond file size "
                f"(expected toc_end=0x{toc_start + toc_len:X}, file=0x{meta_size:X})."
            )

    status(f"Scanning KVS for KOVS headers (expecting {expected} entries)", "blue")
    progress(0, max(1, expected), "Scanning KVS")

    offsets: list[int] = []
    sizes: list[int] = []

    with open(kvs_subcontainer_path, "rb") as kf:
        mm = mmap.mmap(kf.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            n = len(mm)
            pos = 0
            idx = 0
            while idx < expected:
                found = mm.find(b"KOVS", pos)
                if found < 0 or found + 8 > n:
                    break

                data_size = int.from_bytes(mm[found + 4:found + 8], "little", signed=False)
                chunk_size = 32 + data_size
                if data_size <= 0 or chunk_size <= 32 or found + chunk_size > n:
                    pos = found + 4
                    continue

                offsets.append(found)
                sizes.append(chunk_size)
                idx += 1
                pos = found + chunk_size

                if idx % 512 == 0 or idx == expected:
                    progress(idx, expected, f"Scanning KVS {idx}/{expected}")
        finally:
            try:
                mm.close()
            except Exception:
                pass

    found_n = len(offsets)
    if found_n == 0:
        raise ValueError("No b'KOVS' headers found in the selected KVS subcontainer.")

    status(f"Found {found_n}/{expected} KOVS entries. Writing metadata TOC", "blue")
    progress(0, max(1, expected), "Updating metadata")

    with open(metadata_bin_path, "r+b") as mf:
        for i, (off, sz) in enumerate(zip(offsets, sizes)):
            ent_pos = 8 + i * 8
            mf.seek(ent_pos)
            mf.write(off.to_bytes(4, "little", signed=False))
            mf.write(sz.to_bytes(4, "little", signed=False))

            if (i + 1) % 512 == 0 or (i + 1) == found_n:
                progress(i + 1, expected, f"Updating metadata {i + 1}/{expected}")

    if found_n != expected:
        status(
            f"Warning: metadata expects {expected} entries but found {found_n} in KVS. "
            f"Updated {found_n} entries; remaining TOC entries were left unchanged.",
            "red",
        )
    else:
        status("KVS metadata updated successfully.", "green")
        progress(expected, expected, "Metadata update complete.")

def rebuild_subcontainer_from_folder(
    folder_path: str,
    original_subcontainer_path: str,
    output_path: str | None = None,
):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected subcontainer folder does not exist.")
    if not os.path.isfile(original_subcontainer_path):
        raise ValueError("Selected original subcontainer file does not exist.")

    with open(original_subcontainer_path, "rb") as handle:
        original_blob = handle.read()

    if looks_like_mdlk_blob(original_blob):
        return rebuild_mdlk_from_folder(folder_path, original_subcontainer_path, output_path)
    if looks_like_kshl_blob(original_blob):
        return rebuild_kshl_from_folder(folder_path, original_subcontainer_path, output_path)
    if looks_like_split_zlib_pairtable_wrapper(original_blob):
        return rebuild_split_zlib_wrapper_from_folder(folder_path, original_subcontainer_path, output_path)
    if looks_like_classic_split_zlib(original_blob):
        return rebuild_classic_split_zlib_from_folder(folder_path, original_subcontainer_path, output_path)
    if looks_like_embedded_mdlk_blob(original_blob):
        return rebuild_embedded_mdlk_from_folder(folder_path, original_subcontainer_path, output_path)
    if original_blob[:4] == b"KOVS":
        output_path = write_rebuilt_resource_output(
            original_subcontainer_path,
            rebuild_kvs_blob_from_folder(folder_path),
            output_path,
        )
        return output_path, f"Rebuilt KVS with {len(list_folder_payload_files(folder_path))} chunk(s)."

    return rebuild_universal_subcontainer_file_from_folder(
        folder_path,
        original_subcontainer_path,
        output_path,
    )
