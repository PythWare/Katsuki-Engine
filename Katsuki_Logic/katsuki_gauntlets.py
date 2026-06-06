import os, sys, struct, io, zlib, logging, ctypes, threading, json
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk
from PIL import Image, ImageOps
from .katsuki_sub_logic import (
    decompress_zl_bytes,
    is_zlib_header,
    rebuild_subcontainer_from_folder,
    unpack_nested_resource,
)
from .katsuki_ref_runtime import load_filename_ref, resolve_output_path

"""
This script handles the utility logic such as unpacking, mod creation, etc
"""

LILAC = "#12100F"
MOD_SIGNATURE = b'AOT2MF'
INSTALLER_SIGNATURE = b'AOT2MI'
BACKUP_FOLDER = "Backups"
LILAC_RGB = (18, 16, 15)
BLAST_THEME = {
    "bg": "#12100F",
    "bg_alt": "#191411",
    "panel": "#231914",
    "panel_alt": "#2F221B",
    "panel_soft": "#3A2A20",
    "field": "#F3E2C4",
    "field_alt": "#D4C0A2",
    "text": "#F8F1E6",
    "text_muted": "#C7B69C",
    "text_dark": "#1B140F",
    "accent": "#FF6A13",
    "accent_bright": "#FFA12E",
    "accent_deep": "#D94715",
    "accent_green": "#5F7934",
    "accent_green_bright": "#89A247",
    "danger": "#B42A16",
    "warning": "#F08A22",
    "metal": "#9A9BA2",
    "border": "#6F4A25",
    "preview_bg": "#0A0908",
}

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

CONTAINER_PATHS = {
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

METADATA_SIZE_MAP = {
    0: BIN1_METADATA_SIZE, 1: BIN2_METADATA_SIZE, 2: BIN3_METADATA_SIZE, 3: BIN4_METADATA_SIZE,
    4: BIN5_METADATA_SIZE, 5: BIN6_METADATA_SIZE, 6: BIN7_METADATA_SIZE, 7: BIN8_METADATA_SIZE,
    8: BIN9_METADATA_SIZE, 9: BIN10_METADATA_SIZE, 10: BIN11_METADATA_SIZE, 11: BIN12_METADATA_SIZE,
    12: BIN13_METADATA_SIZE, 13: BIN14_METADATA_SIZE, 14: BIN15_METADATA_SIZE, 15: BIN16_METADATA_SIZE,
    16: BIN17_METADATA_SIZE,
}

FILE_SIZE_MAP = {
    0: BIN1_SIZE, 1: BIN2_SIZE, 2: BIN3_SIZE, 3: BIN4_SIZE,
    4: BIN5_SIZE, 5: BIN6_SIZE, 6: BIN7_SIZE, 7: BIN8_SIZE,
    8: BIN9_SIZE, 9: BIN10_SIZE, 10: BIN11_SIZE, 11: BIN12_SIZE,
    12: BIN13_SIZE, 13: BIN14_SIZE, 14: BIN15_SIZE, 15: BIN16_SIZE,
    16: BIN17_SIZE,
}

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

def read_metadata_block(path, size):
    with open(path, "rb") as f:
        data = f.read(size)
    if len(data) != size:
        raise IOError(f"{path} is only {len(data)} bytes; expected {size} bytes")
    return data

def write_toc_backup(source_path, backup_path, metadata_size):
    """
    Store only the container TOC/metadata prefix needed to undo appended mods
    Existing full container backups are shrunk using their own metadata bytes
    """
    existing_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else None
    if existing_size == metadata_size:
        return "kept"
    if existing_size is not None and existing_size < metadata_size:
        raise IOError(
            f"Existing backup is only {existing_size} bytes; expected {metadata_size} bytes"
        )

    read_path = backup_path if existing_size is not None else source_path
    toc_data = read_metadata_block(read_path, metadata_size)

    dest_dir = os.path.dirname(backup_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    tmp_path = f"{backup_path}.tmp"
    try:
        with open(tmp_path, "wb") as out:
            out.write(toc_data)
        try:
            os.utime(tmp_path, (os.path.getatime(read_path), os.path.getmtime(read_path)))
        except OSError:
            pass
        os.replace(tmp_path, backup_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return "shrunk" if read_path == backup_path else "created"

def ensure_backups():
    """
    Creates metadata only TOC backups for original game containers
    preserving subdirectory structures
    """
    backup_errors = []
    created_count = 0
    shrunk_count = 0

    if not os.path.exists(BACKUP_FOLDER):
        try:
            os.makedirs(BACKUP_FOLDER)
        except Exception as e:
            msg = f"Could not create Backup folder: {e}"
            log.error(msg)
            return False, "error", msg
        
    for cid, bin_path in CONTAINER_PATHS.items():
        dest = os.path.join(BACKUP_FOLDER, bin_path)
        metadata_size = METADATA_SIZE_MAP.get(cid)

        if metadata_size is None or not os.path.exists(bin_path):
            continue

        try:
            result = write_toc_backup(bin_path, dest, metadata_size)
            if result == "created":
                created_count += 1
            elif result == "shrunk":
                shrunk_count += 1
        except Exception as e:
            msg = f"Failed to back up TOC for {bin_path}: {e}"
            log.error(msg)
            backup_errors.append(msg)

    if backup_errors:
        return False, "warning", "Some backups could not be created:\n\n" + "\n".join(backup_errors)

    if created_count or shrunk_count:
        log.info(
            "TOC backups ready: created %d, converted from full backups %d",
            created_count,
            shrunk_count,
        )

    return True, "info", ""

def setup_lilac_styles(root: tk.Misc) -> ttk.Style:
    """
    Create/refresh Katsuki blast ttk styles for the given Tk interpreter
    """
    style = ttk.Style(master=root)

    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("Lilac.TFrame", background=BLAST_THEME["bg"])
    style.configure("Lilac.TLabel", background=BLAST_THEME["bg"], foreground=BLAST_THEME["text"], padding=0)
    style.map("Lilac.TLabel", background=[("active", LILAC)])
    style.configure(
        "TButton",
        background=BLAST_THEME["panel_soft"],
        foreground=BLAST_THEME["text"],
        borderwidth=1,
        relief="flat",
        padding=(10, 6),
        focusthickness=1,
        focuscolor=BLAST_THEME["accent"],
    )
    style.map(
        "TButton",
        background=[
            ("disabled", BLAST_THEME["panel"]),
            ("pressed", BLAST_THEME["accent_deep"]),
            ("active", BLAST_THEME["accent"]),
        ],
        foreground=[
            ("disabled", BLAST_THEME["text_muted"]),
            ("pressed", BLAST_THEME["text"]),
            ("active", BLAST_THEME["text_dark"]),
        ],
    )
    style.configure(
        "TNotebook",
        background=BLAST_THEME["bg"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=BLAST_THEME["panel_alt"],
        foreground=BLAST_THEME["text_muted"],
        padding=(16, 8),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", BLAST_THEME["accent"]), ("active", BLAST_THEME["panel_soft"])],
        foreground=[("selected", BLAST_THEME["text_dark"]), ("active", BLAST_THEME["text"])],
    )
    style.configure(
        "TProgressbar",
        troughcolor=BLAST_THEME["panel"],
        background=BLAST_THEME["accent"],
        bordercolor=BLAST_THEME["panel"],
        lightcolor=BLAST_THEME["accent_bright"],
        darkcolor=BLAST_THEME["accent_deep"],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=BLAST_THEME["panel_soft"],
        troughcolor=BLAST_THEME["bg_alt"],
        bordercolor=BLAST_THEME["panel"],
        arrowcolor=BLAST_THEME["accent_bright"],
        relief="flat",
    )
    style.configure(
        "TCombobox",
        fieldbackground=BLAST_THEME["field"],
        background=BLAST_THEME["panel_soft"],
        foreground=BLAST_THEME["text_dark"],
        arrowcolor=BLAST_THEME["accent"],
        bordercolor=BLAST_THEME["border"],
        lightcolor=BLAST_THEME["field"],
        darkcolor=BLAST_THEME["field_alt"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BLAST_THEME["field"])],
        foreground=[("readonly", BLAST_THEME["text_dark"])],
        selectbackground=[("readonly", BLAST_THEME["accent_bright"])],
        selectforeground=[("readonly", BLAST_THEME["text_dark"])],
    )
    style.configure(
        "Treeview",
        background=BLAST_THEME["panel_alt"],
        fieldbackground=BLAST_THEME["panel_alt"],
        foreground=BLAST_THEME["text"],
        bordercolor=BLAST_THEME["border"],
        rowheight=24,
    )
    style.map(
        "Treeview",
        background=[("selected", BLAST_THEME["accent"])],
        foreground=[("selected", BLAST_THEME["text_dark"])],
    )
    style.configure(
        "Treeview.Heading",
        background=BLAST_THEME["panel_soft"],
        foreground=BLAST_THEME["text"],
        bordercolor=BLAST_THEME["border"],
        relief="flat",
    )
    style.map(
        "Treeview.Heading",
        background=[("active", BLAST_THEME["accent_bright"])],
        foreground=[("active", BLAST_THEME["text_dark"])],
    )

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

def parse_valid_taildata(file_data: bytes):
    tail_info = parse_taildata(file_data)
    return tail_info if has_plausible_taildata(tail_info) else None

def split_payload_and_taildata(file_data: bytes):
    tail_info = parse_taildata(file_data)
    if not has_plausible_taildata(tail_info):
        return file_data, b"", None
    return file_data[:-TAILDATA_SIZE], file_data[-TAILDATA_SIZE:], tail_info

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
        self.filename_ref = load_filename_ref()

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

            # Sort by offset since some bins don't have files packed in sequential order
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

                # Append Taildata for the mod manager
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

                output_path, filename = resolve_output_path(
                    folder_name,
                    self.filename_ref,
                    container_id,
                    entry['idx'],
                    ext,
                )

                with open(output_path, "wb") as out:
                    out.write(raw_data)
                    out.write(taildata)

                try:
                    unpack_nested_resource(output_path, blob=raw_data)
                except Exception as e:
                    log.warning("Nested subcontainer unpack failed for %s: %s", filename, e)

                if self.progress_callback and i % 100 == 0:
                    self.progress_callback(i + 1, len(valid_toc), f"Unpacking: {filename}")

            if self.progress_callback:
                self.progress_callback(file_count, file_count, f"Completed: {folder_name}")

class ModManagerLogic:
    def __init__(self):
        self.containers = dict(CONTAINER_PATHS)
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

                tail_info = parse_valid_taildata(file_data)
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

                        tail_info = parse_valid_taildata(file_data)
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
            tail_info = parse_valid_taildata(file_data)
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
            tail_info = parse_valid_taildata(file_data)
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

        try:
            with open(mod_path, "rb") as f:
                def read_exact(size):
                    data = f.read(size)
                    if len(data) != size:
                        raise EOFError("Unexpected end of mod package header")
                    return data

                def read_int(size):
                    return int.from_bytes(read_exact(size), "little")

                sig_len = read_int(1)
                sig = read_exact(sig_len)

                def read_str(size_bytes=1):
                    length = read_int(size_bytes)
                    return read_exact(length).decode('utf-8', errors='ignore')

                if sig == b'AOT2MF':
                    is_release = read_int(1) # Catch global flag
                    genre_byte = read_int(1)
                    file_count = read_int(4)
                    author = read_str(1)
                    version = read_str(1)
                    description = self.read_krle_description(f)

                    img_count = read_int(1)
                    images = []
                    for _ in range(img_count):
                        size = read_int(4)
                        images.append(read_exact(size))

                    audio_data = None
                    has_audio = read_int(1)
                    if has_audio:
                        a_size = read_int(4)
                        audio_data = read_exact(a_size)

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
                    is_release = read_int(1) # Catch global flag
                    genre_byte = read_int(1)
                    name = read_str(1)
                    author = read_str(1)
                    version = read_str(1)
                    description = self.read_krle_description(f)

                    audio_data = None
                    has_audio = read_int(1)
                    if has_audio:
                        a_size = read_int(4)
                        audio_data = read_exact(a_size)

                    return {
                        "type": "installer",
                        "is_release": is_release,
                        "meta": {"name": name, "author": author, "version": version, "description": description, "genre": REV_GENRE_MAP.get(genre_byte, "Unknown")},
                        "images": [],
                        "audio": audio_data,
                        "payload_offset": f.tell()
                    }
        except Exception:
            log.warning("Could not parse mod package header: %s", mod_path, exc_info=True)

        return None

    def read_krle_description(self, f):
        """Reads the hybrid Zlib/KRLE 5K text block"""
        flag_raw = f.read(1)
        payload_len_raw = f.read(2)
        if len(flag_raw) != 1 or len(payload_len_raw) != 2:
            raise EOFError("Unexpected end of mod description block")

        flag = int.from_bytes(flag_raw, "little")
        payload_len = int.from_bytes(payload_len_raw, "little")
        if payload_len > 5000:
            raise ValueError("Mod description block is larger than 5000 bytes")

        payload = f.read(payload_len)
        if len(payload) != payload_len:
            raise EOFError("Unexpected end of mod description payload")

        if flag == 0:
            pad_count = 5000 - payload_len
            if len(f.read(pad_count)) != pad_count:
                raise EOFError("Unexpected end of mod description padding")
            return payload.decode('utf-8', errors='ignore')
        elif flag == 1:
            if len(f.read(2)) != 2:
                raise EOFError("Unexpected end of mod description padding")
            return payload.decode('utf-8', errors='ignore')
        elif flag == 2:
            if len(f.read(2)) != 2:
                raise EOFError("Unexpected end of mod description padding")
            try:
                b_text = zlib.decompress(payload)
            except zlib.error:
                b_text = b""
            return b_text.decode('utf-8', errors='ignore')
        
        return ""

    def inject_raw_payload(self, file_data):
        """Injects a single file blob into the BINs"""
        tail_info = parse_valid_taildata(file_data)
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
                    
                    tail_info = parse_valid_taildata(file_data)
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
                size_to_read = METADATA_SIZE_MAP.get(cid)
                target_truncate_size = FILE_SIZE_MAP.get(cid)

                if size_to_read is None or target_truncate_size is None:
                    continue

                original_meta = read_metadata_block(backup_path, size_to_read)

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
        try:
            with open(file_path, "rb") as f:
                f.seek(-TAILDATA_SIZE, 2)
                return parse_valid_taildata(f.read(TAILDATA_SIZE)) is not None
        except OSError:
            return False

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
            for file_path in files:
                if not self.validate_taildata(file_path):
                    return False, f"File missing valid Katsuki taildata ({TAILDATA_SIZE} bytes): {os.path.basename(file_path)}"

            image_blobs = []
            for img_p in image_paths[:5]:
                dat = self.process_image(img_p)
                if dat:
                    image_blobs.append(dat)

            with open(save_path, "wb") as f:
                f.write(len(MOD_SIGNATURE).to_bytes(1, "little"))
                f.write(MOD_SIGNATURE)
                f.write((1 if is_release else 0).to_bytes(1, "little")) # Global flag
                f.write(GENRE_MAP.get(genre, 1).to_bytes(1, "little"))
                f.write(len(files).to_bytes(4, "little"))
                
                self.write_string(f, author, 1)
                self.write_string(f, version, 1)
                self.write_krle_description(f, description, is_release)

                f.write(len(image_blobs).to_bytes(1, "little"))
                for dat in image_blobs:
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
                    size = os.path.getsize(file_path)
                    f.write(size.to_bytes(4, "little"))
                    with open(file_path, "rb") as src: f.write(src.read())
            return True, "Created"
        except Exception as e: return False, str(e)

    def create_installer_package(self, save_path, name, version, author, description, audio_path, arch_data, tree_obj, is_release=False, genre="Texture"):
        """Creates an .aot2mi installer with separated per-option resources"""
        try:
            groups = list(tree_obj.get_children(""))
            option_total = 0
            for g_id in groups:
                options = list(tree_obj.get_children(g_id))
                option_total += len(options)
                for o_id in options:
                    for file_path in arch_data[o_id].get('files', []):
                        if not self.validate_taildata(file_path):
                            return False, f"File missing valid Katsuki taildata ({TAILDATA_SIZE} bytes): {os.path.basename(file_path)}"

            if not groups or option_total <= 0:
                return False, "Installer packages need at least one group and one option."

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
