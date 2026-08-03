import os, sys, struct, io, zlib, logging, ctypes, threading, json
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk
from PIL import Image, ImageOps
from .katsuki_sub_logic import (
    decompress_zl_bytes,
    is_zlib_header,
    rebuild_subcontainer_from_folder,
    unpack_nested_resource,
)
from .katsuki_ref_runtime import load_profile_filename_ref, resolve_output_path
from .katsuki_profiles import (
    GAME_PROFILES,
    LINKDATA_MAGIC,
    GameProfile,
    get_active_profile,
    metadata_size as container_metadata_size,
    read_container_header,
    read_toc,
    resolve_containers,
)
from .katsuki_taildata import (
    TAILDATA_SIZE,
    load_manifest,
    pack_record,
    pack_target_block,
    parse_valid_taildata,
    read_target_block,
)

"""
This script handles the utility logic such as unpacking, mod creation, etc
"""

LILAC = "#12100F"
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

def backup_manifest_path(profile: GameProfile) -> str:
    return os.path.join(BACKUP_FOLDER, profile.backup_manifest_filename)


def load_backup_manifest(profile: GameProfile) -> dict:
    """Pristine container sizes, recorded the first time a backup is taken"""
    try:
        with open(backup_manifest_path(profile), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_backup_manifest(profile: GameProfile, manifest: dict) -> None:
    try:
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        with open(backup_manifest_path(profile), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
    except OSError as exc:
        log.warning("Could not write backup manifest: %s", exc)


def original_container_size(profile: GameProfile, container_id: int, manifest: dict | None = None):
    """Pristine size for a container or None when it was never recorded"""
    if manifest is None:
        manifest = load_backup_manifest(profile)
    entry = manifest.get("containers", {}).get(str(container_id))
    if isinstance(entry, dict) and isinstance(entry.get("original_size"), int):
        return entry["original_size"]
    return None


def ensure_backups(profile: GameProfile | None = None):
    """
    Creates metadata only TOC backups for original game containers
    preserving subdirectory structures
    """
    profile = profile or get_active_profile()
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

    manifest = load_backup_manifest(profile)
    containers = manifest.setdefault("containers", {})
    manifest["game"] = profile.game_id

    for cid, bin_path in resolve_containers(profile).items():
        dest = os.path.join(BACKUP_FOLDER, bin_path)
        metadata_size = container_metadata_size(bin_path)

        if metadata_size is None or not os.path.exists(bin_path):
            continue

        record = containers.setdefault(str(cid), {})
        record["path"] = bin_path
        if "original_size" not in record and not os.path.exists(dest):
            try:
                record["original_size"] = os.path.getsize(bin_path)
            except OSError:
                pass

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

    save_backup_manifest(profile, manifest)

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

class BackgroundUnpacker:
    """
    Handles the unpacking logic in a background thread:
     Unpacks/Decompresses files
     Auto detects file extensions based on magic bytes
     Records container metadata in the external taildata manifest
    """
    def __init__(self, progress_callback, ui_notify=None, profile: GameProfile | None = None):
        self.progress_callback = progress_callback
        self.ui_notify = ui_notify
        self.profile = profile or get_active_profile()
        self.filename_ref = load_profile_filename_ref(self.profile)
        self.manifest = load_manifest(self.profile)

    def save_manifest(self):
        try:
            return self.manifest.save()
        except OSError as exc:
            log.error("Could not write taildata manifest: %s", exc)
            if self.ui_notify:
                self.ui_notify(
                    "error",
                    "Taildata",
                    f"Unpacked files were written but the taildata manifest could not be saved:\n{exc}",
                )
            return None

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

        alignment = self.profile.alignment
        header = read_container_header(bin_path)
        if header and header[2] and header[2] != alignment:
            log.warning(
                "%s declares alignment 0x%X but %s expects 0x%X; using the profile value",
                bin_path, header[2], self.profile.game_id, alignment,
            )

        self.manifest.drop_container(container_id)
        self.manifest.set_container(container_id, bin_path)

        toc = read_toc(bin_path, alignment=alignment)
        file_count = len(toc)

        with open(bin_path, "rb") as f:
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
                    gap_size = valid_toc[j]['off'] - entry['off']
                else:
                    gap_size = total_size - entry['off']

                if self.profile.extract_size == "toc" and 0 < entry['ms'] <= gap_size:
                    read_size = entry['ms']
                else:
                    read_size = gap_size

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

                output_path, filename = resolve_output_path(
                    folder_name,
                    self.filename_ref,
                    container_id,
                    entry['idx'],
                    ext,
                )

                with open(output_path, "wb") as out:
                    out.write(raw_data)

                self.manifest.add(
                    os.path.relpath(output_path, str(self.manifest.root)),
                    {
                        "container_id": container_id,
                        "container_path": bin_path,
                        "meta_offset": entry['meta_offset'],
                        "orig_base": entry['base'],
                        "orig_main": entry['ms'],
                        "orig_decomp": entry['ds'],
                        "is_comp": 1 if entry['ds'] > 0 else 0,
                        "file_id": entry['idx'],
                        "unpacked_size": len(raw_data),
                        "stored_ext": orig_ext,
                        "ext": ext,
                    },
                )

                try:
                    unpack_nested_resource(output_path, blob=raw_data)
                except Exception as e:
                    log.warning("Nested subcontainer unpack failed for %s: %s", filename, e)

                if self.progress_callback and i % 100 == 0:
                    self.progress_callback(i + 1, len(valid_toc), f"Unpacking: {filename}")

            if self.progress_callback:
                self.progress_callback(file_count, file_count, f"Completed: {folder_name}")

        self.save_manifest()

class ModManagerLogic:
    def __init__(self, profile: GameProfile | None = None):
        self.profile = profile or get_active_profile()
        self.containers = resolve_containers(self.profile)
        for cid in self.profile.containers:
            self.containers.setdefault(cid, self.profile.candidates(cid)[0])
        self.align_shift = self.profile.align_shift
        self.alignment = self.profile.alignment
        self.ledger_path = self.profile.ledger_filename
        self.installer_state_path = self.profile.installer_state_filename
        self.mods_dir = "Mods"

    def mod_extensions(self):
        return self.profile.mod_extensions

    def align_up(self, handle):
        """Move to the next container aligned boundary, padding as needed"""
        handle.seek(0, 2)
        pos = handle.tell()
        padding = (self.alignment - (pos % self.alignment)) % self.alignment
        if padding:
            handle.write(b"\x00" * padding)
        aligned = handle.tell()
        if aligned % self.alignment:
            raise IOError(
                f"Couldn't align to 0x{self.alignment:X} in {handle.name}, "
                f"landed on 0x{aligned:X}"
            )
        return aligned

    def base_for_offset(self, offset, target_bin):
        """Convert an aligned offset into the TOC's base value"""
        base = offset >> self.align_shift
        if base << self.align_shift != offset:
            raise IOError(
                f"{target_bin}: offset 0x{offset:X} is not a multiple of "
                f"0x{self.alignment:X}, refusing to write a lossy TOC entry"
            )
        if base > 0xFFFFFFFF:
            raise IOError(
                f"{target_bin}: container has grown past what the TOC can address "
                f"at 0x{self.alignment:X} alignment. Run Hard Reset to reclaim space."
            )
        return base

    def verify_target(self, header, mod_name="This mod"):
        """Check a package was built for the containers this install actually has"""
        target = header.get("target") or {}
        expected_shift = target.get("align_shift")

        if expected_shift is not None and expected_shift != self.profile.align_shift:
            return False, (
                f"{mod_name} was built for {1 << expected_shift} byte alignment but "
                f"{self.profile.label} uses {self.profile.alignment}.\n\n"
                "The package targets a different game and can't be applied here."
            )

        for cid, (built_name, built_count) in (target.get("containers") or {}).items():
            local_name = self.containers.get(cid)
            if not local_name:
                return False, f"{mod_name} targets unknown container id {cid}."

            if os.path.basename(built_name).casefold() != os.path.basename(local_name).casefold():
                return False, (
                    f"{mod_name} was built against {built_name} but this install "
                    f"has {local_name} for that slot.\n\n"
                    "These are different regional versions of the game. Their file "
                    "tables may not line up so applying this would corrupt the "
                    "container. Use a mod built for your region & notify PythWare so KE can be updated."
                )

            if not built_count:
                continue
            header_info = read_container_header(local_name)
            if not header_info or header_info[0] != LINKDATA_MAGIC:
                continue
            if header_info[1] != built_count:
                return False, (
                    f"{mod_name} was built against a {built_name} holding "
                    f"{built_count} files but yours holds {header_info[1]}.\n\n"
                    "The versions differ, so the stored file positions no longer "
                    "point at the right entries."
                )

        return True, ""

    def load_installer_state(self):
        if not os.path.exists(self.installer_state_path):
            return {}
        try:
            with open(self.installer_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            log.warning("Installer state could not be read, resetting sidecar.", exc_info=True)
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

                mod_f.read(1)
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

                if sig == self.profile.mod_signature:
                    target = read_target_block(read_int, read_exact)
                    is_release = read_int(1)
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
                        "target": target,
                        "payload_offset": f.tell()
                    }

                elif sig == self.profile.installer_signature:
                    target = read_target_block(read_int, read_exact)
                    is_release = read_int(1)
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
                        "target": target,
                        "payload_offset": f.tell()
                    }

                for other in GAME_PROFILES.values():
                    if sig in (other.mod_signature, other.installer_signature):
                        log.warning(
                            "%s is a %s package but %s is the active game",
                            os.path.basename(mod_path), other.short_label, self.profile.short_label,
                        )
                        break
        except Exception:
            log.warning("Couldn't parse mod package header: %s", mod_path, exc_info=True)

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
            new_start = self.align_up(bin_f)
            new_base = self.base_for_offset(new_start, target_bin)
            bin_f.write(actual_payload)

            bin_f.seek(meta_offset)
            bin_f.write(struct.pack("<I", new_base))
            bin_f.seek(meta_offset + 8)
            bin_f.write(struct.pack("<II", len(actual_payload), 0))
        return True

    def apply_mod(self, mod_path):
        """
        Appends files to the BIN and updates the TOC
        """
        mod_name = os.path.basename(mod_path)
        header = self.get_mod_header(mod_path)
        if not header:
            return False, "Invalid Mod Package"
        if header.get("type") != "standard":
            return False, "Installer packages must be launched through the installer wizard."

        ok, reason = self.verify_target(header, mod_name)
        if not ok:
            log.warning("Refused to apply %s: %s", mod_name, reason.replace("\n", " "))
            return False, reason

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

                    new_start_pos = self.align_up(current_bin_handle)
                    new_base_val = self.base_for_offset(new_start_pos, target_bin)

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
        unknown_sizes = []
        backup_manifest = load_backup_manifest(self.profile)

        for cid, name in self.containers.items():
            backup_path = os.path.join(BACKUP_FOLDER, name)

            if not os.path.exists(name):
                continue

            if not os.path.exists(backup_path):
                missing_backups.append(name)
                continue

            try:
                size_to_read = os.path.getsize(backup_path)
                target_truncate_size = original_container_size(self.profile, cid, backup_manifest)

                if not size_to_read:
                    continue
                if target_truncate_size is None:
                    unknown_sizes.append(name)

                original_meta = read_metadata_block(backup_path, size_to_read)

                with open(name, "r+b") as f:
                    f.seek(0)
                    f.write(original_meta)
                    if target_truncate_size is not None:
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
            msg = "Couldn't restore the following files because backups were missing:\n\n" + "\n".join(missing_backups)
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

        if unknown_sizes:
            msg = (
                "All mods cleared and the TOCs are back to vanilla.\n\n"
                "These containers had no recorded original size, so the appended "
                "mod bytes were left in place (harmless, just wasted disk):\n\n"
                + "\n".join(unknown_sizes)
            )
            log.warning("disable_all couldn't truncate: %s", ", ".join(unknown_sizes))
            return True, "warning", msg

        msg = "All mods cleared. Metadata and file sizes restored to vanilla."
        log.info(msg)
        return True, "info", msg

class ModPacker:
    """Builds mod packages"""

    def __init__(self, profile: GameProfile | None = None):
        self.profile = profile or get_active_profile()
        self.manifest = load_manifest(self.profile)
        self.resolved_containers = resolve_containers(self.profile)

    def reload_manifest(self):
        self.manifest = load_manifest(self.profile)
        self.resolved_containers = resolve_containers(self.profile)

    def container_signature(self, container_id):
        """filename/toc_entry_count for a container"""
        name = self.resolved_containers.get(container_id)
        if name:
            header = read_container_header(name)
            if header and header[0] == LINKDATA_MAGIC:
                return name, header[1]
        recorded = self.manifest.containers.get(str(container_id))
        if isinstance(recorded, str) and recorded:
            return recorded, 0
        return (name or ""), 0

    def build_target_block(self, records):
        """Describe the containers this package writes into"""
        containers = {}
        for record in records:
            cid = int(record["container_id"])
            if cid in containers:
                continue
            name, count = self.container_signature(cid)
            if name:
                containers[cid] = (name, count)
        return pack_target_block(self.profile.align_shift, containers)

    def resolve_payload(self, file_path):
        """Return (payload_with_record, error) for one file being packed"""
        try:
            file_data = Path(file_path).read_bytes()
        except OSError as exc:
            return None, f"Couldn't read {os.path.basename(file_path)}: {exc}"

        record, payload = self.manifest.resolve(file_path, file_data)
        if not record:
            return None, None, (
                f"No taildata for {os.path.basename(file_path)}.\n\n"
                f"It must sit inside the folder unpacked for {self.profile.short_label} "
                f"so it can be matched against {self.profile.taildata_filename}."
            )
        return payload + pack_record(record), record, None

    def validate_taildata(self, file_path):
        record, _payload = self.manifest.resolve(file_path)
        return record is not None

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
        """Standard mod package logic (.aot2m/.aot1m)"""
        try:
            self.reload_manifest()

            payloads = []
            records = []
            for file_path in files:
                payload, record, error = self.resolve_payload(file_path)
                if error:
                    return False, error
                payloads.append(payload)
                records.append(record)

            target_block = self.build_target_block(records)

            image_blobs = []
            for img_p in image_paths[:5]:
                dat = self.process_image(img_p)
                if dat:
                    image_blobs.append(dat)

            signature = self.profile.mod_signature
            with open(save_path, "wb") as f:
                f.write(len(signature).to_bytes(1, "little"))
                f.write(signature)
                f.write(target_block)
                f.write((1 if is_release else 0).to_bytes(1, "little"))
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

                for payload in payloads:
                    f.write(len(payload).to_bytes(4, "little"))
                    f.write(payload)
            return True, "Created"
        except Exception as e: return False, str(e)

    def create_installer_package(self, save_path, name, version, author, description, audio_path, arch_data, tree_obj, is_release=False, genre="Texture"):
        """Creates an installer package with per-option resources"""
        try:
            self.reload_manifest()

            groups = list(tree_obj.get_children(""))
            option_total = 0
            resolved: dict[str, list[bytes]] = {}
            all_records: list[dict] = []
            for g_id in groups:
                options = list(tree_obj.get_children(g_id))
                option_total += len(options)
                for o_id in options:
                    option_payloads = []
                    for file_path in arch_data[o_id].get('files', []):
                        payload, record, error = self.resolve_payload(file_path)
                        if error:
                            return False, error
                        option_payloads.append(payload)
                        all_records.append(record)
                    resolved[o_id] = option_payloads

            if not groups or option_total <= 0:
                return False, "Installer packages need at least one group and one option."

            target_block = self.build_target_block(all_records)

            signature = self.profile.installer_signature
            with open(save_path, "wb") as f:
                f.write(len(signature).to_bytes(1, "little"))
                f.write(signature)
                f.write(target_block)
                f.write((1 if is_release else 0).to_bytes(1, "little"))
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

                        option_payloads = resolved.get(o_id, [])
                        f.write(len(option_payloads).to_bytes(4, "little"))
                        for payload in option_payloads:
                            f.write(len(payload).to_bytes(4, "little"))
                            f.write(payload)
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
