import os, sys, shutil, struct, io, zlib, logging, ctypes, threading, json
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk
from PIL import Image, ImageOps

"""
This script handles the utility logic such as unpacking, mod creation, etc
"""

LILAC = "#C8A2C8"
MOD_SIGNATURE = b'AOT2MF'
INSTALLER_SIGNATURE = b'AOT2MI'
BACKUP_FOLDER = "Backups"
LILAC_RGB = (200, 162, 200)

EXT4 = {
    b'GT1G': '.g1t',
    b'_M1G': '.g1m',
    b'_S2G': '.g1s',
    b'ME1G': '.g1em',
    b'_A1G': '.g1a',
    b'_A2G': '.g1a',
    b'XF1G': '.g1fx',
    b'OC1G': '.g1c',
    b'_L1G': '.g1l',
    b'_N1G': '.g1n',
    b'_H1G': '.g1h',
    b'SV1G': '.g1vs',
    b'LCSK': '.kscl',
    b'TLSK': '.kslt',
    b'KTSR': '.ktsl2stbin',
    b'KTSC': '.ktsl2asbin',
    b'KTSS': '.ktss',
    b'KOVS': '.kvs',
    b'_SPK': '.postfx',
    b'_OLS': '.sebin',
    b'OggS': '.ogg',
    b'RIFF': '.riff',
    b'1DHW': '.sed',
    b'_HBW': '.wbh',
    b'_DBW': '.wbd',
    b'KPMG': '.gmpk',
    b'KPML': '.lmpk',
    b'KPAG': '.gapk',
    b'KPEG': '.gepk',
    b'0KPB': '.bpk',
    b'KPTR': '.rtrpk',
    b'KLMD': '.mdlk',
    b'RLDM': '.mdlpack',
    b'TLDM': '.mdltexpack',
    b'GRAX': '.exarg',
    b'RFFE': '.effectpack',
    b'DAEH': '.exhead',
    b'RRRT': '.ktfkpack',
    b'RLOC': '.colpack',
    b'APDT': '.tdpack',
    b'_DRK': '.rdb',
    b'IDRK': '.rdb.bin',
    b'PDRK': '.fdata',
    b'_RNK': '.name',
    b'IRNK': '.name.bin',
    b'_DOK': '.kidsobjdb',
    b'IDOK': '.kidsobjdb.bin',
    b'RDOK': '.kidsobjdb.bin',
    b'MDLS': '.mdls',
    b'DXBC': '.dxbc',
    b'FP1G': '.fp1g',
    b'HWYX': '.hwyx',
    b'SCM_': '.scm',
    b'DLV0': '.dlv0',
    b'DLV4': '.dlv4',
    b'SV00': '.sv00',
    b'SV01': '.sv01',
    b'SV02': '.sv02',
    b'SV03': '.sv03',
    b'SV20': '.sv20',
    b'SV30': '.sv30',
    b'SV40': '.sv40',
    b'SV41': '.sv41',
    b'Act_': '.act',
    b'ET00': '.et00',
    b'ET01': '.et01',
    b'ET02': '.et02',
    b'ET03': '.et03',
    b'FT02': '.ft02',
    b'SARC': '.sarc',
    b'CRAE': '.elixir',
    b'SPKG': '.spkg',
    b'SCEN': '.scene',
    b'KPS3': '.shaderpack',
    b'QGWS': '.swg',
    b'EVIR': '.river',
    b'BGIR': '.rig',
    b'RTRE': '.ertr',
    b'DATD': '.datd',
    b'D0CL': '.lcd0',
    b'HDDB': '.hdb',
    b'RTXE': '.extra',
    b'LLOC': '.coll',
    b'ONUN': '.nuno',
    b'VNUN': '.nunv',
    b'SNUN': '.nuns',
    b'TFOS': '.soft',
    b'RIAH': '.hair',
    b'TNOC': '.cont',
    b'pkgi': '.pkginfo',
    b'DDS ': '.dds',
    b'char': '.chardata',
    b'clip': '.clip',
    b'body': '.bodybase',
    b'MSBP': '.material',
    b'tdpa': '.tdpack',
    b'HIUB': '.hiub',
    b'MDLK': '.KLDM',
    b'ipu2': '.ipu2',
    b'MESC': '.MESC'
}

EXT3 = {
    b'XFT': '.xft',
    b'GT1': '.g1t'
}

EXT2 = {
    b'BM': '.bmp',
    b'XL': '.XL'
}

# used for truncating, disabling all mods to be precise
BIN1_SIZE = 6_271_283_456 # A
BIN2_SIZE = 7_756_262_400 # B
BIN3_SIZE = 2_470_024_448 # C
BIN4_SIZE = 4_352 # D
BIN5_SIZE = 1_346_373_632 # DEBUG
BIN6_SIZE = 1_015_837_184 # DLC
BIN7_SIZE = 442_564_864 # DX11
BIN8_SIZE = 825_832_192 # EDEN
BIN9_SIZE = 48_940_800 # REGION_JP
BIN10_SIZE = 96_621_824 # REGION_AS
BIN11_SIZE = 69_428_224 # REFION_EDEN_AS
BIN12_SIZE = 206_677_760 # REGION_EDEN_EU
BIN13_SIZE = 32_979_200 # REGION_EDEN_JP
BIN14_SIZE = 291_377_920 # REGION_EU
BIN15_SIZE = 4_352 # EX_MASTER
BIN16_SIZE = 2_543_425_024 # PATCH_000
BIN17_SIZE = 3_648 # PATCH_EDEN_000

# used during truncating, revering metadata to original values by grabbing the data from Backups
BIN1_METADATA_SIZE = 215_280 # A
BIN2_METADATA_SIZE = 12_576 # B
BIN3_METADATA_SIZE = 150_640 # C
BIN4_METADATA_SIZE = 16 # D
BIN5_METADATA_SIZE = 7_792 # DEBUG
BIN6_METADATA_SIZE = 880 # DLC
BIN7_METADATA_SIZE = 18_016 # DX11
BIN8_METADATA_SIZE = 5_936 # EDEN
BIN9_METADATA_SIZE = 6_528 # REGION_JP
BIN10_METADATA_SIZE = 13_040 # REGION_AS
BIN11_METADATA_SIZE = 8_352 # REFION_EDEN_AS
BIN12_METADATA_SIZE = 26_512 # REGION_EDEN_EU
BIN13_METADATA_SIZE = 4_384 # REGION_EDEN_JP
BIN14_METADATA_SIZE = 39_008 # REGION_EU
BIN15_METADATA_SIZE = 16 # EX_MASTER
BIN16_METADATA_SIZE = 44_016 # PATCH_000
BIN17_METADATA_SIZE = 3_632 # PATCH_EDEN_000

GENRE_MAP = {"All": 1, "Texture": 2, "Audio": 3, "Model": 4, "Overhaul": 5}
REV_GENRE_MAP = {1: "All", 2: "Texture", 3: "Audio", 4: "Model", 5: "Overhaul"}

winmm = ctypes.WinDLL("winmm", use_last_error=True)

# BOOL PlaySoundW(LPCWSTR pszSound, HMODULE hmod, DWORD fdwSound)
# For SND_MEMORY, pszSound is interpreted as a pointer to memory
PlaySoundW = winmm.PlaySoundW
PlaySoundW.argtypes = [ctypes.c_void_p, wintypes.HMODULE, wintypes.DWORD]
PlaySoundW.restype = wintypes.BOOL

SND_ASYNC    = 0x0001
SND_NODEFAULT= 0x0002
SND_MEMORY   = 0x0004
SND_LOOP     = 0x0008
SND_PURGE    = 0x0040

TAILDATA_STRUCT = struct.Struct("<BIIIIBI")
TAILDATA_SIZE = TAILDATA_STRUCT.size
    
def setup_logging() -> str:
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    log_dir = os.path.join(base_dir, "Logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "katsuki_debug.log")

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s"))
    root.addHandler(fh)
    
    root.propagate = False
    logging.lastResort = None
    logging.raiseExceptions = False
    logging.captureWarnings(True)

    fh.flush()
    return log_path

LOG_PATH = setup_logging()
log = logging.getLogger("katsuki")
log.info("Logging initialized: %s", LOG_PATH)

def ensure_backups():
    """
    Creates a Backups folder and copies original game containers,
    preserving subdirectory structures
    """
    backup_errors = []
    
    containers = [
        "LINKDATA_A.BIN", "LINKDATA_B.BIN", "LINKDATA_C.BIN", "LINKDATA_D.BIN",
        "LINKDATA_DEBUG.BIN", "LINKDATA_DLC.BIN", "LINKDATA_PLATFORM_DX11.BIN", 
        "LINKDATA_PLATFORM_EDEN_DX11.BIN", "REGION/LINKDATA_REGION_JP.BIN",
        "REGION/LINKDATA_REGION_AS.BIN", "REGION/LINKDATA_REGION_EDEN_AS.BIN", "REGION/LINKDATA_REGION_EDEN_EU.BIN", "REGION/LINKDATA_REGION_EDEN_JP.BIN",
        "REGION/LINKDATA_REGION_EU.BIN", "EX/LINKDATA_EX_MASTER.BIN", "PATCH/LINKDATA_PATCH_000.BIN", 
        "PATCH/LINKDATA_PATCH_EDEN_000.BIN"
    ]
    
    if not os.path.exists(BACKUP_FOLDER):
        try:
            os.makedirs(BACKUP_FOLDER)
        except Exception as e:
            msg = f"Could not create Backup folder: {e}"
            log.error(msg)
            return False, "error", msg
        
    for bin_path in containers:
        dest = os.path.join(BACKUP_FOLDER, bin_path)
        
        if os.path.exists(bin_path) and not os.path.exists(dest):
            try:
                dest_dir = os.path.dirname(dest)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                shutil.copy2(bin_path, dest)
            except Exception as e:
                msg = f"Failed to back up {bin_path}: {e}"
                log.error(msg)
                backup_errors.append(msg)

    if backup_errors:
        return False, "warning", "Some backups could not be created:\n\n" + "\n".join(backup_errors)

    return True, "info", ""

def setup_lilac_styles(root: tk.Misc) -> ttk.Style:
    """
    Create/refresh lilac ttk styles for the given Tk interpreter
    """
    style = ttk.Style(master=root)
    
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("Lilac.TFrame", background=LILAC)
    style.configure("Lilac.TLabel", background=LILAC, foreground="black", padding=0)
    style.map("Lilac.TLabel", background=[("active", LILAC)])

    return style

def apply_lilac_to_root(root: tk.Misc) -> None:
    """For plain tk widgets (tk.Frame/tk.Label/etc) that rely on root bg"""
    try:
        root.configure(bg=LILAC)
    except tk.TclError:
        pass

def resize_and_pad(image_path):
    """ Resizes the image to fit 500x500 while keeping aspect ratio/pads the empty areas with the Lilac color"""
    with Image.open(image_path) as img:
        img = ImageOps.pad(img, (500, 500), color=LILAC_RGB, centering=(0.5, 0.5))
        return img

def ensure_dir(path: str):
    """If something exists and it's a file, a safe alternate folder name is used"""
    if os.path.exists(path) and not os.path.isdir(path):
        alt = path + "_dir"
        log.warning("ensure_dir: %s exists as file, using %s", path, alt)
        path = alt
    os.makedirs(path, exist_ok=True)
    return path

def match_known_signature(data: bytes, off: int):
    if off < 0 or off + 4 > len(data):
        return None

    sig4 = data[off:off+4]
    hit = EXT4.get(sig4)
    if hit:
        return hit
    if off + 12 <= len(data):
        try:
            total_out, csize = struct.unpack_from("<II", data, off)
            if 0 < total_out <= 0x40000000 and 0 < csize <= (len(data) - (off + 8)):
                if is_zlib_header(data[off+8:off+10]):
                    return "zl"
        except struct.error:
            pass

    return None

def is_real_subcontainer(raw_data: bytes, offsets: list[int], table_end: int, probe_limit: int = 8) -> bool:
    """
    Treat as subcontainer only if a few offsets actually point to known file signatures
    """
    uniq = sorted(set(o for o in offsets if table_end <= o < len(raw_data)))
    if len(uniq) < 2:
        return False

    hits = 0
    checked = 0

    for off in uniq[:probe_limit]:
        checked += 1
        if match_known_signature(raw_data, off):
            hits += 1

    return hits >= 2

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

def is_zlib_header(b: bytes) -> bool:
    if len(b) < 2:
        return False
    cmf, flg = b[0], b[1]
    if (cmf & 0x0F) != 8 or (cmf >> 4) > 7:
        return False
    return ((cmf << 8) + flg) % 31 == 0

def decompress_zl_bytes(buf: bytes) -> bytes:
    if len(buf) < 8:
        raise ValueError("ZL too small")

    total_out, csize = struct.unpack_from("<II", buf, 0)
    off = 8
    out = bytearray()
    chunk_idx = 0

    # u32 total_out/raw zlib stream, no csize field
    if csize > len(buf) - off and is_zlib_header(buf[4:6]):
        return zlib.decompress(buf[4:])

    while len(out) < total_out:
        if csize <= 0:
            raise ValueError(f"ZL chunk {chunk_idx}: invalid comp_size={csize}")
        if off + csize > len(buf):
            raise ValueError(f"ZL chunk {chunk_idx}: comp_size overruns file")

        comp = buf[off:off + csize]
        if not is_zlib_header(comp[:2]):
            break  # likely padding section

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

def parse_taildata(file_data: bytes):
    if len(file_data) < TAILDATA_SIZE:
        return None

    cont_id, meta_offset, orig_base, orig_main, orig_decomp, is_comp, f_idx = TAILDATA_STRUCT.unpack(
        file_data[-TAILDATA_SIZE:]
    )
    return {
        "container_id": cont_id,
        "meta_offset": meta_offset,
        "orig_base": orig_base,
        "orig_main": orig_main,
        "orig_decomp": orig_decomp,
        "is_comp": is_comp,
        "file_id": f_idx,
        "key": (cont_id, f_idx),
    }

def has_plausible_taildata(tail_info) -> bool:
    if not tail_info:
        return False
    if not (0 <= tail_info["container_id"] <= 16):
        return False
    if tail_info["meta_offset"] < 0x10:
        return False
    return ((tail_info["meta_offset"] - 0x10) % 16) == 0

def split_payload_and_taildata(file_data: bytes):
    tail_info = parse_taildata(file_data)
    if not has_plausible_taildata(tail_info):
        return file_data, b"", None
    return file_data[:-TAILDATA_SIZE], file_data[-TAILDATA_SIZE:], tail_info

def subcontainer_file_sort_key(path: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return (0, int(parts[1]), stem.lower())
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

def rebuild_subcontainer_from_folder(folder_path, original_subcontainer_path, output_path=None):
    if not os.path.isdir(folder_path):
        raise ValueError("Selected subcontainer folder does not exist.")
    if not os.path.isfile(original_subcontainer_path):
        raise ValueError("Selected original subcontainer file does not exist.")

    with open(original_subcontainer_path, "rb") as f:
        original_blob = f.read()

    original_raw, taildata_bytes, _tail_info = split_payload_and_taildata(original_blob)
    if not taildata_bytes:
        raise ValueError("Original subcontainer must be an unpacked Katsuki file with taildata appended.")

    toc_info = read_subcontainer_toc(original_raw)
    if not toc_info:
        raise ValueError("Original file does not contain a readable subcontainer TOC.")

    count, offsets, table_end = toc_info
    if not is_real_subcontainer(original_raw, offsets, table_end):
        raise ValueError("Original file does not look like a valid subcontainer.")

    unique_offsets = sorted(set(off for off in offsets if table_end <= off < len(original_raw)))
    folder_files = [
        os.path.join(folder_path, name)
        for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
    ]
    folder_files.sort(key=subcontainer_file_sort_key)

    if not folder_files:
        raise ValueError("Selected subcontainer folder does not contain any files to rebuild.")
    if len(folder_files) != len(unique_offsets):
        raise ValueError(
            f"Subcontainer file count mismatch. Folder has {len(folder_files)} file(s), "
            f"but the original TOC maps to {len(unique_offsets)} unique payload slot(s)."
        )

    prefix_end = unique_offsets[0] if unique_offsets else table_end
    rebuilt_prefix = bytearray(original_raw[:prefix_end])
    rebuilt_payload = bytearray()
    new_unique_offsets = []

    cursor = prefix_end
    for file_path in folder_files:
        with open(file_path, "rb") as f:
            blob = f.read()
        new_unique_offsets.append(cursor)
        rebuilt_payload.extend(blob)
        cursor += len(blob)

    offset_map = {
        old_offset: new_offset
        for old_offset, new_offset in zip(unique_offsets, new_unique_offsets)
    }

    struct.pack_into("<I", rebuilt_prefix, 0, count)
    for idx, old_offset in enumerate(offsets):
        struct.pack_into("<I", rebuilt_prefix, 4 + idx * 4, offset_map.get(old_offset, old_offset))

    rebuilt_blob = bytes(rebuilt_prefix) + bytes(rebuilt_payload) + taildata_bytes

    if output_path is None:
        src_dir = os.path.dirname(original_subcontainer_path)
        src_name = os.path.basename(original_subcontainer_path)
        base, ext = os.path.splitext(src_name)
        output_path = os.path.join(src_dir, f"{base}_rebuilt{ext}")
    output_path = next_available_output_path(output_path)

    with open(output_path, "wb") as f:
        f.write(rebuilt_blob)

    return output_path, f"Rebuilt subcontainer with {len(folder_files)} payload(s)."

class BackgroundUnpacker:
    """
    Handles the unpacking logic in a background thread:
     Unpacks/Decompresses files
     Auto detects file extensions based on magic bytes
     Appends 22 byte taildata for Mod Manager tracking
    """
    def __init__(self, progress_callback, ui_notify=None):
        self.progress_callback = progress_callback
        self.ui_notify = ui_notify

    def detect_ext(self, data: bytes) -> str:
        if not data:
            return ".bin"

        head = data[:64]
        n = len(data)
        head4 = head[:4]
        head3 = head[:3]
        head2 = head[:2]

        ext = EXT4.get(head4)
        if ext:
            if head4 == b'RIFF':
                return ".wav" if b"WAVEfmt" in head else ".riff"
            return ext

        ext = EXT3.get(head3)
        if ext:
            return ext

        ext = EXT2.get(head2)
        if ext:
            return ext

        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"

        # ZL wrapper
        if n >= 12:
            try:
                total_out, csize = struct.unpack_from("<II", data, 0)
                if 0 < total_out <= 0x40000000 and 0 < csize <= (n - 8) and is_zlib_header(data[8:10]):
                    return ".zl"
            except struct.error:
                pass

        if b"JFIF" in head:
            return ".jpg"

        if head.startswith(b"TIM2") or b"TIM2" in head:
            return ".tm2"
        if data.startswith(b"SShd"):
            return ".ss2"
        if data.startswith(b"SSbd"):
            return ".ss2bd"
        if data.startswith(b"IECSsreV"):
            return ".vagbank"
        if head4 == b"\x00\x20\xAF\x30":
            return ".tm2"
        if head4 == b"\x45\x4D\x06\x00":
            return ".EM"

        return ".bin"

    def unpack_resource(self, bin_path, folder_name, container_id):
        """Unpacks main files"""
        if not os.path.exists(bin_path):
            raise FileNotFoundError(f"Could not find {bin_path}.")
        os.makedirs(folder_name, exist_ok=True)
        
        with open(bin_path, "rb") as f:
            # Read Header
            sig = f.read(4)
            file_count = int.from_bytes(f.read(4), "little")
            f.read(8)
            
            # Map the TOC
            toc = []
            for i in range(file_count):
                entry_data = f.read(16)
                base_val, _, main_size, decomp_size = struct.unpack("<IIII", entry_data)
                
                # Store original index
                toc.append({
                    'idx': i,
                    'off': base_val << 8,
                    'ms': main_size,
                    'ds': decomp_size,
                    'meta_offset': 0x10 + (i * 16),
                    'base': base_val
                })

            f.seek(0, 2)
            total_size = f.tell()

            # Sort by offset since some bins do not have files packed in sequential order
            valid_toc = [e for e in toc if e['off'] > 0]
            valid_toc.sort(key=lambda x: x['off'])

            # Extraction Loop
            for i, entry in enumerate(valid_toc):
                
                # Calculate size based on the next physical file, skipping duplicate offsets
                j = i + 1
                while j < len(valid_toc) and valid_toc[j]['off'] == entry['off']:
                    j += 1

                if j < len(valid_toc):
                    read_size = valid_toc[j]['off'] - entry['off']
                else:
                    read_size = total_size - entry['off']

                if read_size <= 0: read_size = entry['ms']
                if read_size <= 0: continue 

                f.seek(entry['off'])
                raw_data = f.read(read_size)
                
                if not raw_data: continue

                ext = self.detect_ext(raw_data)
                orig_ext = ext

                if ext == ".zl":
                    try:
                        raw_data = decompress_zl_bytes(raw_data)
                        new_ext = self.detect_ext(raw_data)
                        ext = new_ext if new_ext else ".bin"
                    except Exception as e:
                        log.warning("ZL decompression failed for entry %06d: %s", entry['idx'], e)

                # Append Taildata
                # Essential for the Mod Manager to map this file back to the TOC later
                is_comp = 1 if entry['ds'] > 0 else 0
                taildata = TAILDATA_STRUCT.pack(
                    container_id, 
                    entry['meta_offset'], 
                    entry['base'], 
                    entry['ms'], 
                    entry['ds'], 
                    is_comp, 
                    entry['idx']
                )

                filename = f"file_{entry['idx']:06d}{ext}"
                output_path = os.path.join(folder_name, filename)

                with open(output_path, "wb") as out:
                    out.write(raw_data)
                    out.write(taildata)

                toc_info = None
                if ext != ".zl":
                    toc_info = read_subcontainer_toc(raw_data)
                    if toc_info:
                        _count, offsets, table_end = toc_info

                        if is_real_subcontainer(raw_data, offsets, table_end):
                            sub_dir = ensure_dir(os.path.join(folder_name, f"file_{entry['idx']:06d}"))

                            uniq = sorted(set(o for o in offsets if o >= table_end))
                            n2 = len(raw_data)

                            for j, off2 in enumerate(uniq):
                                if off2 >= n2:
                                    break

                                next_off2 = uniq[j + 1] if j + 1 < len(uniq) else n2
                                if next_off2 > n2:
                                    next_off2 = n2

                                size2 = next_off2 - off2
                                if size2 <= 0:
                                    continue

                                blob = raw_data[off2:off2 + size2]
                                blob_ext = self.detect_ext(blob) if blob else ".bin"
                                blob_name = f"file_{entry['idx']:06d}_{j:04d}{blob_ext}"
                                blob_path = os.path.join(sub_dir, blob_name)

                                with open(blob_path, "wb") as bout:
                                    bout.write(blob)

                if self.progress_callback and i % 100 == 0:
                    self.progress_callback(i + 1, len(valid_toc), f"Unpacking: {filename}")

            if self.progress_callback:
                self.progress_callback(file_count, file_count, f"Completed: {folder_name}")

class ModManagerLogic:
    def __init__(self):
        self.containers = {
            0: "LINKDATA_A.BIN", 
            1: "LINKDATA_B.BIN", 
            2: "LINKDATA_C.BIN", 
            3: "LINKDATA_D.BIN",
            4: "LINKDATA_DEBUG.BIN", 
            5: "LINKDATA_DLC.BIN",
            6: "LINKDATA_PLATFORM_DX11.BIN", 
            7: "LINKDATA_PLATFORM_EDEN_DX11.BIN",
            8: "REGION/LINKDATA_REGION_JP.BIN",
            9: "REGION/LINKDATA_REGION_AS.BIN", 
            10: "REGION/LINKDATA_REGION_EDEN_AS.BIN", 
            11: "REGION/LINKDATA_REGION_EDEN_EU.BIN", 
            12: "REGION/LINKDATA_REGION_EDEN_JP.BIN",
            13: "REGION/LINKDATA_REGION_EU.BIN", 
            14: "EX/LINKDATA_EX_MASTER.BIN",
            15: "PATCH/LINKDATA_PATCH_000.BIN", 
            16: "PATCH/LINKDATA_PATCH_EDEN_000.BIN",
        }
        self.ledger_path = "applied_mods.txt"
        self.installer_state_path = "installer_state.json"

    def load_installer_state(self):
        if not os.path.exists(self.installer_state_path):
            return {}

        try:
            with open(self.installer_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            log.warning("Installer state could not be read; resetting sidecar.", exc_info=True)
            return {}

        return data if isinstance(data, dict) else {}

    def save_installer_state_map(self, state):
        with open(self.installer_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def prune_installer_state(self, active_mods=None):
        state = self.load_installer_state()
        if active_mods is None:
            active_mods = set(self.get_applied_mod_order())
        else:
            active_mods = set(active_mods)

        pruned = {
            mod_name: entries
            for mod_name, entries in state.items()
            if mod_name in active_mods and os.path.exists(os.path.join("Mods", mod_name))
        }

        if pruned != state:
            if pruned:
                self.save_installer_state_map(pruned)
            elif os.path.exists(self.installer_state_path):
                os.remove(self.installer_state_path)

        return pruned

    def get_applied_mod_order(self):
        """Returns active mods in apply order"""
        if not os.path.exists(self.ledger_path):
            return []

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            raw_mods = [line.strip() for line in f if line.strip()]

        ordered_mods = []
        seen = set()
        for mod_name in raw_mods:
            if mod_name in seen:
                continue
            if os.path.exists(os.path.join("Mods", mod_name)):
                ordered_mods.append(mod_name)
                seen.add(mod_name)

        if ordered_mods != raw_mods:
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                for mod_name in ordered_mods:
                    f.write(f"{mod_name}\n")

        self.prune_installer_state(ordered_mods)

        return ordered_mods

    def get_applied_mods(self):
        """Returns a set of active mod filenames"""
        return set(self.get_applied_mod_order())

    def update_ledger(self, mod_name, add=True):
        mods = self.get_applied_mod_order()
        if add:
            mods = [m for m in mods if m != mod_name]
            mods.append(mod_name)
        else:
            mods = [m for m in mods if m != mod_name]
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            for m in mods:
                f.write(f"{m}\n")

    def iter_standard_mod_records(self, mod_path, include_data=True):
        header = self.get_mod_header(mod_path)
        if not header or header.get("type") != "standard":
            return []

        records = []
        with open(mod_path, "rb") as mod_f:
            mod_f.seek(header["payload_offset"])

            for _ in range(header["file_count"]):
                file_size = int.from_bytes(mod_f.read(4), "little")
                file_data = mod_f.read(file_size)

                tail_info = parse_taildata(file_data)
                if not tail_info:
                    continue

                record = dict(tail_info)
                if include_data:
                    record["file_data"] = file_data
                records.append(record)

        return records

    def iter_installer_payload_records(self, mod_path, include_data=True):
        header = self.get_mod_header(mod_path)
        if not header or header.get("type") != "installer":
            return []

        records = []
        with open(mod_path, "rb") as mod_f:
            mod_f.seek(header["payload_offset"])

            group_count = int.from_bytes(mod_f.read(4), "little")
            for g_idx in range(group_count):
                g_name_len = int.from_bytes(mod_f.read(1), "little")
                mod_f.seek(g_name_len, 1)

                mod_f.read(1)  # selection logic byte
                opt_count = int.from_bytes(mod_f.read(4), "little")

                for o_idx in range(opt_count):
                    o_name_len = int.from_bytes(mod_f.read(1), "little")
                    mod_f.seek(o_name_len, 1)

                    self.read_krle_description(mod_f)

                    img_size = int.from_bytes(mod_f.read(4), "little")
                    if img_size:
                        mod_f.seek(img_size, 1)

                    file_payload_count = int.from_bytes(mod_f.read(4), "little")
                    for p_idx in range(file_payload_count):
                        file_size = int.from_bytes(mod_f.read(4), "little")
                        file_data = mod_f.read(file_size)

                        tail_info = parse_taildata(file_data)
                        if not tail_info:
                            continue

                        record = dict(tail_info)
                        record.update({
                            "group_index": g_idx,
                            "option_index": o_idx,
                            "payload_index": p_idx,
                        })
                        if include_data:
                            record["file_data"] = file_data
                        records.append(record)

        return records

    def save_installer_selection(self, mod_name, selected_payloads):
        state = self.load_installer_state()
        manifest = []
        invalid_count = 0

        for payload in selected_payloads:
            file_data = payload["file_data"]
            tail_info = parse_taildata(file_data)
            if not tail_info:
                invalid_count += 1
                continue

            manifest.append({
                "group_index": int(payload["group_index"]),
                "option_index": int(payload["option_index"]),
                "payload_index": int(payload["payload_index"]),
                "container_id": int(tail_info["container_id"]),
                "meta_offset": int(tail_info["meta_offset"]),
                "orig_base": int(tail_info["orig_base"]),
                "orig_main": int(tail_info["orig_main"]),
                "orig_decomp": int(tail_info["orig_decomp"]),
                "is_comp": int(tail_info["is_comp"]),
                "file_id": int(tail_info["file_id"]),
            })

        state[mod_name] = manifest
        self.save_installer_state_map(state)
        return len(manifest), invalid_count

    def clear_installer_selection(self, mod_name):
        state = self.load_installer_state()
        if mod_name in state:
            state.pop(mod_name, None)
            if state:
                self.save_installer_state_map(state)
            elif os.path.exists(self.installer_state_path):
                os.remove(self.installer_state_path)

    def get_installed_installer_records(self, mod_name, mod_path, include_data=False):
        state = self.load_installer_state()
        if mod_name not in state:
            return None

        saved_entries = state.get(mod_name, [])
        if not include_data:
            return [
                {
                    **entry,
                    "key": (entry["container_id"], entry["file_id"]),
                }
                for entry in saved_entries
            ]

        all_records = self.iter_installer_payload_records(mod_path, include_data=True)
        records_by_coord = {
            (record["group_index"], record["option_index"], record["payload_index"]): record
            for record in all_records
        }

        results = []
        for entry in saved_entries:
            coord = (entry["group_index"], entry["option_index"], entry["payload_index"])
            source = records_by_coord.get(coord)
            if not source:
                continue

            results.append({
                **entry,
                "key": (entry["container_id"], entry["file_id"]),
                "file_data": source["file_data"],
            })

        return results

    def get_collision_keys_from_blobs(self, payload_blobs):
        keys = set()
        invalid_count = 0

        for file_data in payload_blobs:
            tail_info = parse_taildata(file_data)
            if not tail_info:
                invalid_count += 1
                continue
            keys.add(tail_info["key"])

        return keys, invalid_count

    def get_active_collision_report(self, keys, exclude_mod_name=None):
        collisions = []
        skipped_mods = []

        if not keys:
            return collisions, skipped_mods

        for mod_name in self.get_applied_mod_order():
            if mod_name == exclude_mod_name:
                continue

            mod_path = os.path.join("Mods", mod_name)
            header = self.get_mod_header(mod_path)
            if not header:
                continue

            if header.get("type") == "standard":
                records = self.iter_standard_mod_records(mod_path, include_data=False)
            else:
                records = self.get_installed_installer_records(mod_name, mod_path, include_data=False)
                if records is None:
                    skipped_mods.append(mod_name)
                    continue

            mod_keys = {record["key"] for record in records}
            overlap = keys & mod_keys
            if overlap:
                collisions.append({
                    "mod_name": mod_name,
                    "count": len(overlap),
                    "keys": sorted(overlap),
                })

        return collisions, skipped_mods

    def build_collision_message(self, target_name, collisions, skipped_mods, key_count):
        lines = [f"{target_name} touches {key_count} tracked file(s)."]

        if collisions:
            total_overlaps = sum(item["count"] for item in collisions)
            lines.append(f"It overlaps {total_overlaps} file(s) across these active mods:")
            for item in collisions:
                lines.append(f"- {item['mod_name']} ({item['count']} file(s))")

        if skipped_mods:
            lines.append("")
            lines.append("These active installer packages could not be checked precisely:")
            for mod_name in skipped_mods:
                lines.append(f"- {mod_name}")

        lines.append("")
        lines.append("Continue and let the new install take priority on overlapping files?")
        return "\n".join(lines)

    def reapply_overlapping_mods(self, keys, exclude_mod_name=None):
        reapplied = []

        if not keys:
            return reapplied

        for mod_name in self.get_applied_mod_order():
            if mod_name == exclude_mod_name:
                continue

            mod_path = os.path.join("Mods", mod_name)
            header = self.get_mod_header(mod_path)
            if not header:
                continue

            if header.get("type") == "standard":
                records = self.iter_standard_mod_records(mod_path)
            else:
                records = self.get_installed_installer_records(mod_name, mod_path, include_data=True)
                if records is None:
                    continue

            overlapping_records = [record for record in records if record["key"] in keys]
            if not overlapping_records:
                continue

            for record in overlapping_records:
                self.inject_raw_payload(record["file_data"])

            reapplied.append({
                "mod_name": mod_name,
                "count": len(overlapping_records),
            })

        return reapplied

    def get_mod_header(self, mod_path):
        """Detects signature and parses standard/installer formats"""
        if not os.path.exists(mod_path): return None
        
        with open(mod_path, "rb") as f:
            sig_len = int.from_bytes(f.read(1), "little")
            sig = f.read(sig_len)
            
            def read_str(size_bytes=1):
                length = int.from_bytes(f.read(size_bytes), "little")
                return f.read(length).decode('utf-8', errors='ignore')

            if sig == b'AOT2MF':
                is_release = int.from_bytes(f.read(1), "little") # Catch global flag
                genre_byte = int.from_bytes(f.read(1), "little")
                file_count = int.from_bytes(f.read(4), "little")
                author = read_str(1)
                version = read_str(1)
                description = self.read_krle_description(f)
                
                img_count = int.from_bytes(f.read(1), "little")
                images = []
                for _ in range(img_count):
                    size = int.from_bytes(f.read(4), "little")
                    images.append(f.read(size))
                
                audio_data = None
                has_audio = int.from_bytes(f.read(1), "little")
                if has_audio:
                    a_size = int.from_bytes(f.read(4), "little")
                    audio_data = f.read(a_size)
                
                return {
                    "type": "standard",
                    "is_release": is_release,
                    "meta": {"author": author, "version": version, "description": description, "genre": REV_GENRE_MAP.get(genre_byte, "Unknown")},
                    "images": images,
                    "audio": audio_data,
                    "file_count": file_count,
                    "payload_offset": f.tell()
                }

            elif sig == b'AOT2MI':
                is_release = int.from_bytes(f.read(1), "little") # Catch global flag
                genre_byte = int.from_bytes(f.read(1), "little")
                name = read_str(1)
                author = read_str(1)
                version = read_str(1)
                description = self.read_krle_description(f)
                
                audio_data = None
                has_audio = int.from_bytes(f.read(1), "little")
                if has_audio:
                    a_size = int.from_bytes(f.read(4), "little")
                    audio_data = f.read(a_size)
                
                return {
                    "type": "installer",
                    "is_release": is_release,
                    "meta": {"name": name, "author": author, "version": version, "description": description, "genre": REV_GENRE_MAP.get(genre_byte, "Unknown")},
                    "images": [], 
                    "audio": audio_data,
                    "payload_offset": f.tell()
                }
                
        return None

    def read_krle_description(self, f):
        """Reads the hybrid Zlib/KRLE 5K text block"""
        flag = int.from_bytes(f.read(1), "little")
        payload_len = int.from_bytes(f.read(2), "little")
        payload = f.read(payload_len)
        
        if flag == 0:
            pad_count = 5000 - payload_len
            f.read(pad_count)
            return payload.decode('utf-8', errors='ignore')
        elif flag == 1:
            f.read(2)
            return payload.decode('utf-8', errors='ignore')
        elif flag == 2:
            f.read(2)
            try:
                b_text = zlib.decompress(payload)
            except zlib.error:
                b_text = b""
            return b_text.decode('utf-8', errors='ignore')
        
        return ""

    def inject_raw_payload(self, file_data):
        """Injects a single file blob into the BINs"""
        tail_info = parse_taildata(file_data)
        if not tail_info:
            return False

        cont_id = tail_info["container_id"]
        meta_offset = tail_info["meta_offset"]
        
        target_bin = self.containers.get(cont_id)
        if not target_bin or not os.path.exists(target_bin):
            return False
        actual_payload = file_data[:-TAILDATA_SIZE]

        with open(target_bin, "r+b") as bin_f:
            bin_f.seek(0, 2)
            pos = bin_f.tell()
            padding = (256 - (pos % 256)) % 256
            if padding: bin_f.write(b'\x00' * padding)
            
            new_start = bin_f.tell()
            new_base = new_start >> 8
            bin_f.write(actual_payload)
            
            bin_f.seek(meta_offset)
            bin_f.write(struct.pack("<I", new_base))
            bin_f.seek(meta_offset + 8)
            bin_f.write(struct.pack("<II", len(actual_payload), 0))
        return True

    def apply_mod(self, mod_path):
        """
        Appends files to the BIN and updates the TOC
        Also ensures 256 byte alignment for the new data
        """
        mod_name = os.path.basename(mod_path)
        header = self.get_mod_header(mod_path)
        if not header:
            return False, "Invalid Mod Package"
        if header.get("type") != "standard":
            return False, "Installer packages must be launched through the installer wizard."

        with open(mod_path, "rb") as mod_f:
            mod_f.seek(header["payload_offset"])

            current_bin_handle = None
            current_bin_path = None

            try:
                for _ in range(header['file_count']):
                    file_size = int.from_bytes(mod_f.read(4), "little")
                    file_data = mod_f.read(file_size)
                    
                    tail_info = parse_taildata(file_data)
                    if not tail_info:
                        continue

                    cont_id = tail_info["container_id"]
                    meta_offset = tail_info["meta_offset"]
                    
                    target_bin = self.containers.get(cont_id)
                    if not target_bin:
                        return False, f"Unknown Container ID: {cont_id}"

                    if current_bin_path != target_bin:
                        if current_bin_handle:
                            current_bin_handle.close()
                        if not os.path.exists(target_bin):
                            return False, f"Missing {target_bin}"
                        current_bin_handle = open(target_bin, "r+b")
                        current_bin_path = target_bin

                    current_bin_handle.seek(0, 2)
                    current_pos = current_bin_handle.tell()
                    
                    padding_needed = (256 - (current_pos % 256)) % 256
                    if padding_needed > 0:
                        current_bin_handle.write(b'\x00' * padding_needed)
                    
                    new_start_pos = current_bin_handle.tell()
                    
                    new_base_val = new_start_pos >> 8 
                    
                    actual_payload = file_data[:-TAILDATA_SIZE]
                    current_bin_handle.write(actual_payload)
                    
                    new_main_size = len(actual_payload)
                    new_decomp_size = 0 
                    
                    current_bin_handle.seek(meta_offset)
                    
                    current_bin_handle.write(struct.pack("<I", new_base_val))
                    
                    current_bin_handle.seek(meta_offset + 8)
                    current_bin_handle.write(struct.pack("<II", new_main_size, new_decomp_size))

            finally:
                if current_bin_handle: current_bin_handle.close()

        self.update_ledger(mod_name, add=True)
        return True, "Mod Applied Successfully"

    def disable_mod(self, mod_path):
        """
        Restores the original offsets/sizes using the taildata
        Doesn't delete the appended data
        """
        mod_name = os.path.basename(mod_path)
        header = self.get_mod_header(mod_path)
        if not header:
            return False, "Invalid Mod Package"
        if mod_name not in self.get_applied_mods():
            return False, "Mod is not currently active."

        if header.get("type") == "standard":
            records = self.iter_standard_mod_records(mod_path, include_data=False)
        else:
            records = self.get_installed_installer_records(mod_name, mod_path, include_data=False)
            if records is None:
                return False, "No installer selection record was found for this package."

        disabled_keys = {record["key"] for record in records}

        for record in records:
            target_bin = self.containers.get(record["container_id"])
            if not target_bin or not os.path.exists(target_bin):
                continue

            with open(target_bin, "r+b") as bin:
                bin.seek(record["meta_offset"])
                bin.write(struct.pack("<I", record["orig_base"]))

                bin.seek(record["meta_offset"] + 8)
                bin.write(struct.pack("<II", record["orig_main"], record["orig_decomp"]))

        self.update_ledger(mod_name, add=False)
        if header.get("type") == "installer":
            self.clear_installer_selection(mod_name)
        reapplied = self.reapply_overlapping_mods(disabled_keys, exclude_mod_name=mod_name)

        if reapplied:
            summary = ", ".join(f"{item['mod_name']} ({item['count']})" for item in reapplied)
            return True, f"Mod Disabled. Reapplied overlapping files from: {summary}"
        return True, "Mod Disabled"
    
    def disable_all(self):
        """ Restores metadata blocks from original backups/truncates containers to remove all appended mod data"""
        meta_size_map = {
            0: BIN1_METADATA_SIZE, 1: BIN2_METADATA_SIZE, 2: BIN3_METADATA_SIZE, 3: BIN4_METADATA_SIZE,
            4: BIN5_METADATA_SIZE, 5: BIN6_METADATA_SIZE, 6: BIN7_METADATA_SIZE, 7: BIN8_METADATA_SIZE,
            8: BIN9_METADATA_SIZE, 9: BIN10_METADATA_SIZE, 10: BIN11_METADATA_SIZE, 11: BIN12_METADATA_SIZE,
            12: BIN13_METADATA_SIZE, 13: BIN14_METADATA_SIZE, 14: BIN15_METADATA_SIZE, 15: BIN16_METADATA_SIZE,
            16: BIN17_METADATA_SIZE
        }

        file_size_map = {
            0: BIN1_SIZE, 1: BIN2_SIZE, 2: BIN3_SIZE, 3: BIN4_SIZE,
            4: BIN5_SIZE, 5: BIN6_SIZE, 6: BIN7_SIZE, 7: BIN8_SIZE,
            8: BIN9_SIZE, 9: BIN10_SIZE, 10: BIN11_SIZE, 11: BIN12_SIZE,
            12: BIN13_SIZE, 13: BIN14_SIZE, 14: BIN15_SIZE, 15: BIN16_SIZE,
            16: BIN17_SIZE
        }

        missing_backups = []
        restore_errors = []

        for cid, name in self.containers.items():
            backup_path = os.path.join(BACKUP_FOLDER, name)
            
            if not os.path.exists(name):
                continue

            if not os.path.exists(backup_path):
                missing_backups.append(name)
                continue

            try:
                size_to_read = meta_size_map.get(cid)
                target_truncate_size = file_size_map.get(cid)

                if size_to_read is None or target_truncate_size is None:
                    continue

                with open(backup_path, "rb") as bf:
                    original_meta = bf.read(size_to_read)

                with open(name, "r+b") as f:
                    f.seek(0)
                    f.write(original_meta)
                    f.truncate(target_truncate_size)
                        
            except Exception as e:
                restore_errors.append(f"{name}: {str(e)}")

        if restore_errors:
            msg = "Critical errors occurred during reset:\n\n" + "\n".join(restore_errors)
            if missing_backups:
                msg += "\n\nBackups were also missing for:\n\n" + "\n".join(missing_backups)
            log.error("disable_all failed: %s", msg.replace("\n", " | "))
            return False, "error", msg

        if missing_backups:
            msg = "Could not restore the following files because backups were missing:\n\n" + "\n".join(missing_backups)
            log.warning("disable_all partial reset: %s", msg.replace("\n", " | "))
            return True, "warning", msg

        if os.path.exists(self.ledger_path):
            try:
                os.remove(self.ledger_path)
            except Exception:
                pass

        if os.path.exists(self.installer_state_path):
            try:
                os.remove(self.installer_state_path)
            except Exception:
                pass

        msg = "All mods cleared. Metadata and file sizes restored to vanilla."
        log.info(msg)
        return True, "info", msg

class ModPacker:
    def __init__(self):
        pass

    def validate_taildata(self, file_path):
        if os.path.getsize(file_path) < TAILDATA_SIZE:
            return False
        return True

    def write_string(self, f, text, size_bytes=1):
        b_text = text.encode('utf-8')
        f.write(len(b_text).to_bytes(size_bytes, "little"))
        f.write(b_text)

    def write_krle_description(self, f, text, is_release):
        """
        Hybrid Zlib/KRLE compression for fixed 5K text blocks
        """
        b_text = text.encode('utf-8')
        if len(b_text) > 5000:
            b_text = b_text[:5000]

        if is_release:
            comp_text = zlib.compress(b_text, 9)
            if len(comp_text) < len(b_text):
                flag = 2  # Release mode, Zlib/KRLE
                payload = comp_text
            else:
                flag = 1  # Release mode, Raw/KRLE
                payload = b_text
            
            pad_count = 5000 - len(payload)
            f.write(flag.to_bytes(1, "little"))
            f.write(len(payload).to_bytes(2, "little"))
            f.write(payload)
            f.write(pad_count.to_bytes(2, "little"))
        else:
            flag = 0
            payload = b_text
            pad_count = 5000 - len(payload)
            
            f.write(flag.to_bytes(1, "little"))
            f.write(len(payload).to_bytes(2, "little"))
            f.write(payload)
            f.write(b'\x00' * pad_count)

    def process_image(self, img_path):
        if not img_path or not os.path.exists(img_path): return None
        try:
            with Image.open(img_path) as img:
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img = ImageOps.pad(img, (500, 500), color=LILAC_RGB)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                return buf.getvalue()
        except: return None

    def create_package(self, save_path, name, version, author, description, files, image_paths=[], audio_path=None, is_release=False, genre="Texture"):
        """Standard .aot2m logic"""
        try:
            with open(save_path, "wb") as f:
                f.write(len(MOD_SIGNATURE).to_bytes(1, "little"))
                f.write(MOD_SIGNATURE)
                f.write((1 if is_release else 0).to_bytes(1, "little")) # Global flag
                f.write(GENRE_MAP.get(genre, 1).to_bytes(1, "little"))
                f.write(len(files).to_bytes(4, "little"))
                
                self.write_string(f, author, 1)
                self.write_string(f, version, 1)
                self.write_krle_description(f, description, is_release)

                valid_imgs = image_paths[:5]
                f.write(len(valid_imgs).to_bytes(1, "little"))
                for img_p in valid_imgs:
                    dat = self.process_image(img_p)
                    if dat:
                        f.write(len(dat).to_bytes(4, "little"))
                        f.write(dat)

                if audio_path and os.path.exists(audio_path):
                    with open(audio_path, "rb") as af:
                        audio_dat = af.read()
                        f.write((1).to_bytes(1, "little"))
                        f.write(len(audio_dat).to_bytes(4, "little"))
                        f.write(audio_dat)
                else: f.write((0).to_bytes(1, "little"))

                for file_path in files:
                    if not self.validate_taildata(file_path):
                        return False, f"File missing taildata ({TAILDATA_SIZE} bytes): {os.path.basename(file_path)}"
                    size = os.path.getsize(file_path)
                    f.write(size.to_bytes(4, "little"))
                    with open(file_path, "rb") as src: f.write(src.read())
            return True, "Created"
        except Exception as e: return False, str(e)

    def create_installer_package(self, save_path, name, version, author, description, audio_path, arch_data, tree_obj, is_release=False, genre="Texture"):
        """Creates an .aot2mi installer with separated per-option resources"""
        try:
            with open(save_path, "wb") as f:
                f.write(len(INSTALLER_SIGNATURE).to_bytes(1, "little"))
                f.write(INSTALLER_SIGNATURE)
                f.write((1 if is_release else 0).to_bytes(1, "little")) # Globall flag
                f.write(GENRE_MAP.get(genre, 1).to_bytes(1, "little"))
                self.write_string(f, name, 1)
                self.write_string(f, author, 1)
                self.write_string(f, version, 1)
                self.write_krle_description(f, description, is_release)

                if audio_path and os.path.exists(audio_path):
                    with open(audio_path, "rb") as af:
                        audio_dat = af.read()
                        f.write((1).to_bytes(1, "little"))
                        f.write(len(audio_dat).to_bytes(4, "little"))
                        f.write(audio_dat)
                else: f.write((0).to_bytes(1, "little"))

                groups = tree_obj.get_children("")
                f.write(len(groups).to_bytes(4, "little"))

                for g_id in groups:
                    g_data = arch_data[g_id]
                    self.write_string(f, g_data['name'], 1)
                    sel_byte = 1 if g_data['sel_type'] == "Single Select" else 2
                    f.write(sel_byte.to_bytes(1, "little"))

                    options = tree_obj.get_children(g_id)
                    f.write(len(options).to_bytes(4, "little"))

                    for o_id in options:
                        o_data = arch_data[o_id]
                        self.write_string(f, o_data['name'], 1)
                        self.write_krle_description(f, o_data.get('desc', ''), is_release)

                        img_dat = self.process_image(o_data['image'])
                        if img_dat:
                            f.write(len(img_dat).to_bytes(4, "little"))
                            f.write(img_dat)
                        else: f.write((0).to_bytes(4, "little"))

                        f.write(len(o_data['files']).to_bytes(4, "little"))
                        for file_path in o_data['files']:
                            if not self.validate_taildata(file_path):
                                return False, f"File missing taildata ({TAILDATA_SIZE} bytes): {os.path.basename(file_path)}"
                            size = os.path.getsize(file_path)
                            f.write(size.to_bytes(4, "little"))
                            with open(file_path, "rb") as src: f.write(src.read())
            return True, "Installer Created"
        except Exception as e: return False, str(e)

class WinMMAudioPlayer:
    """
    Async looping WAV playback from bytes without temp files
    Keeps an internal buffer alive so Windows can read it
    """
    def __init__(self, log=None):
        self._buf = None
        self.log = log

    def play_loop_bytes(self, wav_bytes: bytes):
        if not wav_bytes:
            return

        if not (len(wav_bytes) >= 12 and wav_bytes[:4] == b"RIFF" and wav_bytes[8:12] == b"WAVE"):
            if self.log:
                self.log.warning("Audio data is not RIFF/WAVE; first 16 bytes=%r", wav_bytes[:16])
            return

        self.stop()

        self._buf = ctypes.create_string_buffer(wav_bytes)
        ptr = ctypes.cast(self._buf, ctypes.c_void_p)

        ok = PlaySoundW(ptr, None, SND_MEMORY | SND_ASYNC | SND_LOOP | SND_NODEFAULT)
        if not ok and self.log:
            err = ctypes.get_last_error()
            self.log.error("winmm.PlaySoundW failed (err=%s)", err)

    def stop(self):
        PlaySoundW(None, None, SND_PURGE)
        self._buf = None
