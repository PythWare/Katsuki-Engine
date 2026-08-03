"""
Game profiles for the Katsuki Engine
"""
from __future__ import annotations

import json, os, struct
from dataclasses import dataclass
from pathlib import Path

LINKDATA_MAGIC = 0x00077DF9
HEADER_STRUCT = struct.Struct("<IIII")
TOC_ENTRY_STRUCT = struct.Struct("<IIII")
HEADER_SIZE = HEADER_STRUCT.size
TOC_ENTRY_SIZE = TOC_ENTRY_STRUCT.size

SETTINGS_FILENAME = "katsuki_settings.json"
DEFAULT_GAME = "aot2"

AOT1_REGIONS = ("EU", "JP", "AS", "US", "CH", "KR")


@dataclass(frozen=True)
class GameProfile:
    game_id: str
    label: str
    short_label: str
    containers: dict[int, tuple[str, tuple[str, ...]]]
    align_shift: int
    mod_signature: bytes
    installer_signature: bytes
    mod_ext: str
    installer_ext: str
    unpack_root: str
    exe_names: tuple[str, ...]
    extract_size: str = "gap"

    @property
    def taildata_filename(self) -> str:
        return f"katsuki_taildata_{self.game_id}.json"

    @property
    def ledger_filename(self) -> str:
        return f"applied_mods_{self.game_id}.txt"

    @property
    def installer_state_filename(self) -> str:
        return f"installer_state_{self.game_id}.json"

    @property
    def ref_filename(self) -> str:
        return f"filename_{self.game_id}.ref"

    @property
    def backup_manifest_filename(self) -> str:
        return f"backup_manifest_{self.game_id}.json"

    @property
    def mod_extensions(self) -> tuple[str, str]:
        return (self.mod_ext, self.installer_ext)

    @property
    def alignment(self) -> int:
        return 1 << self.align_shift

    def folder_name(self, container_id: int) -> str | None:
        entry = self.containers.get(container_id)
        return entry[0] if entry else None

    def unpack_dir(self, container_id: int, root: str | os.PathLike = ".") -> str | None:
        folder = self.folder_name(container_id)
        if folder is None:
            return None
        return os.path.join(str(root), self.unpack_root, folder)

    def candidates(self, container_id: int) -> tuple[str, ...]:
        entry = self.containers.get(container_id)
        return entry[1] if entry else ()


def aot2_containers() -> dict[int, tuple[str, tuple[str, ...]]]:
    paths = {
        0: ("LINK_A", "LINKDATA_A.BIN"),
        1: ("LINK_B", "LINKDATA_B.BIN"),
        2: ("LINK_C", "LINKDATA_C.BIN"),
        3: ("LINK_D", "LINKDATA_D.BIN"),
        4: ("LINK_DEBUG", "LINKDATA_DEBUG.BIN"),
        5: ("LINK_DLC", "LINKDATA_DLC.BIN"),
        6: ("LINK_PLATFORM_DX11", "LINKDATA_PLATFORM_DX11.BIN"),
        7: ("LINK_PLATFORM_EDEN", "LINKDATA_PLATFORM_EDEN_DX11.BIN"),
        8: ("REGION_JP", "REGION/LINKDATA_REGION_JP.BIN"),
        9: ("REGION_AS", "REGION/LINKDATA_REGION_AS.BIN"),
        10: ("REGION_EDEN_AS", "REGION/LINKDATA_REGION_EDEN_AS.BIN"),
        11: ("REGION_EDEN_EU", "REGION/LINKDATA_REGION_EDEN_EU.BIN"),
        12: ("REGION_EDEN_JP", "REGION/LINKDATA_REGION_EDEN_JP.BIN"),
        13: ("REGION_EU", "REGION/LINKDATA_REGION_EU.BIN"),
        14: ("LINK_EX", "EX/LINKDATA_EX_MASTER.BIN"),
        15: ("LINK_PATCH", "PATCH/LINKDATA_PATCH_000.BIN"),
        16: ("LINK_PATCH_EDEN", "PATCH/LINKDATA_PATCH_EDEN_000.BIN"),
    }
    return {cid: (folder, (path,)) for cid, (folder, path) in paths.items()}


def aot1_containers() -> dict[int, tuple[str, tuple[str, ...]]]:
    letters = {
        0: ("LINK_A", "A"),
        1: ("LINK_B", "B"),
        2: ("LINK_C", "C"),
        3: ("LINK_D", "D"),
        4: ("LINK_PLATFORM", "PLATFORM"),
    }
    containers: dict[int, tuple[str, tuple[str, ...]]] = {}
    for cid, (folder, letter) in letters.items():
        names: list[str] = []
        for region in AOT1_REGIONS:
            names.append(f"LINKDATA_{region}_{letter}.BIN")
        names.append(f"LINKDATA_{letter}.BIN")
        containers[cid] = (folder, tuple(names))
    return containers


GAME_PROFILES: dict[str, GameProfile] = {
    "aot2": GameProfile(
        game_id="aot2",
        label="Attack on Titan 2",
        short_label="AOT2",
        containers=aot2_containers(),
        align_shift=8,
        mod_signature=b"AOT2MF",
        installer_signature=b"AOT2MI",
        mod_ext=".aot2m",
        installer_ext=".aot2mi",
        unpack_root=".",
        exe_names=("AOT2_EU.exe", "AOT2_AS.exe", "AOT2_JP.exe"),
        extract_size="gap",
    ),
    "aot1": GameProfile(
        game_id="aot1",
        label="A.O.T. Wings of Freedom",
        short_label="AOT1",
        containers=aot1_containers(),
        align_shift=11,
        mod_signature=b"AOT1MF",
        installer_signature=b"AOT1MI",
        mod_ext=".aot1m",
        installer_ext=".aot1mi",
        unpack_root="AOT1",
        exe_names=("AoT.exe", "AOT.exe"),
        extract_size="toc",
    ),
}


def get_profile(game_id: str) -> GameProfile:
    try:
        return GAME_PROFILES[game_id]
    except KeyError as exc:
        known = ", ".join(sorted(GAME_PROFILES))
        raise ValueError(f"Unknown game id {game_id!r}. Expected one of: {known}") from exc

def read_container_header(path: str | os.PathLike) -> tuple[int, int, int] | None:
    """Return (magic, file_count, alignment) or None when unreadable"""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(HEADER_SIZE)
    except OSError:
        return None
    if len(raw) != HEADER_SIZE:
        return None
    magic, count, alignment, _reserved = HEADER_STRUCT.unpack(raw)
    return magic, count, alignment

def is_real_container(path: str | os.PathLike) -> bool:
    header = read_container_header(path)
    return bool(header and header[0] == LINKDATA_MAGIC)


def read_toc(path: str | os.PathLike, alignment: int | None = None) -> list[dict]:
    """Parse a LINKDATA table of contents"""
    with open(path, "rb") as handle:
        raw_header = handle.read(HEADER_SIZE)
        if len(raw_header) != HEADER_SIZE:
            raise IOError(f"{path} is too small to hold a LINKDATA header")
        magic, count, header_alignment, _reserved = HEADER_STRUCT.unpack(raw_header)
        if magic != LINKDATA_MAGIC:
            raise IOError(f"{path} is not a LINKDATA container (magic 0x{magic:08X})")
        raw_toc = handle.read(count * TOC_ENTRY_SIZE)

    if len(raw_toc) != count * TOC_ENTRY_SIZE:
        raise IOError(f"{path} ended inside its table of contents")

    step = alignment or header_alignment
    entries = []
    for index in range(count):
        base, _reserved, stored, decompressed = TOC_ENTRY_STRUCT.unpack_from(
            raw_toc, index * TOC_ENTRY_SIZE
        )
        entries.append({
            "idx": index,
            "base": base,
            "off": base * step,
            "ms": stored,
            "ds": decompressed,
            "meta_offset": HEADER_SIZE + index * TOC_ENTRY_SIZE,
        })
    return entries

def metadata_size(path: str | os.PathLike) -> int | None:
    """Bytes of header/TOC, everything a backup needs to undo appends"""
    header = read_container_header(path)
    if not header or header[0] != LINKDATA_MAGIC:
        return None
    return HEADER_SIZE + header[1] * TOC_ENTRY_SIZE


def resolve_container_path(
    profile: GameProfile, container_id: int, root: str | os.PathLike = "."
) -> str | None:
    root = str(root)
    fallback = None
    for name in profile.candidates(container_id):
        full = os.path.join(root, name)
        if not os.path.exists(full):
            continue
        if is_real_container(full):
            return name
        if fallback is None:
            fallback = name
    return fallback


def resolve_containers(profile: GameProfile, root: str | os.PathLike = ".") -> dict[int, str]:
    resolved = {}
    for container_id in profile.containers:
        path = resolve_container_path(profile, container_id, root)
        if path:
            resolved[container_id] = path
    return resolved


def default_container_paths(profile: GameProfile) -> dict[int, str]:
    return {
        cid: candidates[0]
        for cid, candidates in ((c, profile.candidates(c)) for c in profile.containers)
        if candidates
    }


def detect_installed_game(root: str | os.PathLike = ".") -> str | None:
    """Guess which game the working directory holds by looking for containers"""
    best = None
    best_score = 0
    for game_id, profile in GAME_PROFILES.items():
        score = sum(
            1
            for cid in profile.containers
            if (path := resolve_container_path(profile, cid, root))
            and is_real_container(os.path.join(str(root), path))
        )
        if score > best_score:
            best, best_score = game_id, score
    return best

def load_settings(root: str | os.PathLike = ".") -> dict:
    path = Path(root) / SETTINGS_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(settings: dict, root: str | os.PathLike = ".") -> None:
    path = Path(root) / SETTINGS_FILENAME
    try:
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def load_active_game(root: str | os.PathLike = ".") -> str:
    stored = load_settings(root).get("active_game")
    if stored in GAME_PROFILES:
        return stored
    return detect_installed_game(root) or DEFAULT_GAME


def save_active_game(game_id: str, root: str | os.PathLike = ".") -> None:
    settings = load_settings(root)
    settings["active_game"] = game_id
    save_settings(settings, root)

active_profile: GameProfile | None = None


def get_active_profile() -> GameProfile:
    global active_profile
    if active_profile is None:
        active_profile = get_profile(load_active_game())
    return active_profile


def set_active_profile(game_id: str, persist: bool = True) -> GameProfile:
    global active_profile
    active_profile = get_profile(game_id)
    if persist:
        save_active_game(game_id)
    return active_profile
