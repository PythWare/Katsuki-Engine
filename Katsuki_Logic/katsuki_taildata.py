"""External taildata manifest"""
from __future__ import annotations

import json, os, struct
from datetime import datetime, timezone
from pathlib import Path

from .katsuki_profiles import GameProfile

TAILDATA_FORMAT = "katsuki-taildata"
TAILDATA_VERSION = 1

# container_id, meta_offset, orig_base, orig_main, orig_decomp, is_comp, file_id
TAILDATA_STRUCT = struct.Struct("<BIIIIBI")
TAILDATA_SIZE = TAILDATA_STRUCT.size

MAX_CONTAINER_ID = 16


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def parse_taildata(file_data: bytes):
    if len(file_data) < TAILDATA_SIZE:
        return None
    cont_id, meta_offset, orig_base, orig_main, orig_decomp, is_comp, f_idx = (
        TAILDATA_STRUCT.unpack(file_data[-TAILDATA_SIZE:])
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
    if not (0 <= tail_info["container_id"] <= MAX_CONTAINER_ID):
        return False
    if tail_info["meta_offset"] < 0x10:
        return False
    return ((tail_info["meta_offset"] - 0x10) % 16) == 0


def parse_valid_taildata(file_data: bytes):
    tail_info = parse_taildata(file_data)
    return tail_info if has_plausible_taildata(tail_info) else None


def pack_record(record: dict) -> bytes:
    """Serialise a manifest record into the trailer form packages carry"""
    return TAILDATA_STRUCT.pack(
        int(record["container_id"]),
        int(record["meta_offset"]),
        int(record["orig_base"]),
        int(record["orig_main"]),
        int(record["orig_decomp"]),
        1 if record.get("is_comp") else 0,
        int(record["file_id"]),
    )

TARGET_BLOCK_VERSION = 1


def pack_target_block(align_shift: int, containers: dict[int, tuple[str, int]]) -> bytes:
    out = bytearray()
    out.append(align_shift & 0xFF)
    usable = {
        cid: (name, count)
        for cid, (name, count) in containers.items()
        if 0 <= cid <= 0xFF and len(name.encode("utf-8")) <= 0xFF
    }
    out.append(len(usable) & 0xFF)
    for cid in sorted(usable):
        name, count = usable[cid]
        raw = name.encode("utf-8")
        out.append(cid)
        out.append(len(raw))
        out.extend(raw)
        out.extend(struct.pack("<I", max(0, int(count))))
    return bytes(out)


def read_target_block(read_int, read_exact) -> dict:
    """Parse a target block using the caller's byte readers"""
    align_shift = read_int(1)
    container_count = read_int(1)
    containers: dict[int, tuple[str, int]] = {}
    for _ in range(container_count):
        cid = read_int(1)
        name_len = read_int(1)
        name = read_exact(name_len).decode("utf-8", errors="ignore")
        count = read_int(4)
        containers[cid] = (name, count)
    return {"align_shift": align_shift, "containers": containers}


def normalize_key(path: str | os.PathLike) -> str:
    return str(path).replace("\\", "/").strip("/")

class TaildataManifest:
    """Records for one game, keyed by unpacked path relative to the project root"""

    def __init__(self, profile: GameProfile, root: str | os.PathLike = "."):
        self.profile = profile
        self.root = Path(root)
        self.path = self.root / profile.taildata_filename
        self.files: dict[str, dict] = {}
        self.containers: dict[str, str] = {}
        self.created_utc: str | None = None

    def load(self) -> "TaildataManifest":
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self
        if not isinstance(data, dict) or data.get("format") != TAILDATA_FORMAT:
            return self
        if data.get("game") != self.profile.game_id:
            return self
        files = data.get("files")
        if isinstance(files, dict):
            self.files = files
        containers = data.get("containers")
        if isinstance(containers, dict):
            self.containers = containers
        self.created_utc = data.get("created_utc")
        return self

    def save(self) -> Path:
        payload = {
            "format": TAILDATA_FORMAT,
            "version": TAILDATA_VERSION,
            "game": self.profile.game_id,
            "game_label": self.profile.label,
            "align_shift": self.profile.align_shift,
            "created_utc": self.created_utc or utc_now(),
            "updated_utc": utc_now(),
            "note": (
                "Taildata for the Katsuki mod manager. Keys are unpacked file "
                "paths relative to the folder holding this file."
            ),
            "containers": self.containers,
            "files": self.files,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)
        return self.path

    def add(self, rel_path: str | os.PathLike, record: dict) -> str:
        key = normalize_key(rel_path)
        self.files[key] = record
        return key

    def set_container(self, container_id: int, container_path: str) -> None:
        self.containers[str(container_id)] = container_path

    def drop_container(self, container_id: int) -> int:
        removed = [
            key for key, rec in self.files.items()
            if int(rec.get("container_id", -1)) == container_id
        ]
        for key in removed:
            del self.files[key]
        return len(removed)

    def get(self, rel_path: str | os.PathLike) -> dict | None:
        return self.files.get(normalize_key(rel_path))

    def candidate_keys(self, file_path: str | os.PathLike) -> list[str]:
        """Keys to try for a file the user picked in a dialog"""
        file_path = Path(file_path).resolve()
        keys: list[str] = []

        try:
            keys.append(normalize_key(file_path.relative_to(self.root.resolve())))
        except ValueError:
            pass

        parts = file_path.parts
        for depth in range(min(len(parts), 12), 1, -1):
            tail = normalize_key("/".join(parts[-depth:]))
            if tail not in keys:
                keys.append(tail)
        return keys

    def resolve(self, file_path: str | os.PathLike, file_data: bytes | None = None):
        """Find taildata for a file"""
        for key in self.candidate_keys(file_path):
            record = self.files.get(key)
            if record is None:
                continue
            if file_data is None:
                try:
                    file_data = Path(file_path).read_bytes()
                except OSError:
                    return None, b""
            return record, file_data
        return None, file_data if file_data is not None else b""

def load_manifest(profile: GameProfile, root: str | os.PathLike = ".") -> TaildataManifest:
    return TaildataManifest(profile, root).load()
