import os, re
from pathlib import Path

DEFAULT_REF_NAME = "filename.ref"
INVALID_FILENAME_CHARS = '<>:"|?*'

REF_DIR = Path(__file__).resolve().parent


def ref_path(profile) -> Path:
    """Where this game's filename ref lives, shipped or regenerated"""
    return REF_DIR / profile.ref_filename


def load_profile_filename_ref(profile, root: str | os.PathLike = ".") -> dict[tuple[int, int], str]:
    candidate = ref_path(profile)
    if candidate.exists():
        return load_filename_ref(candidate)
    return {}


def load_filename_ref(ref_path: str | os.PathLike = DEFAULT_REF_NAME) -> dict[tuple[int, int], str]:
    refs: dict[tuple[int, int], str] = {}
    path = Path(ref_path)
    if not path.exists():
        return refs

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return refs

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        try:
            container_id = int(parts[0])
            file_id = int(parts[2])
        except ValueError:
            continue
        filename = parts[3].strip()
        if filename:
            refs[(container_id, file_id)] = filename
    return refs


def normalize_ref_filename(filename: str, ext: str) -> str | None:
    name = (filename or "").replace("\\", "/").strip()
    if not name:
        return None
    if re.match(r"^[A-Za-z]:", name):
        name = name[2:]
    name = name.lstrip("/")

    parts = []
    for part in name.split("/"):
        part = part.strip()
        if not part or part in (".", ".."):
            continue
        safe = "".join("_" if ch in INVALID_FILENAME_CHARS or ord(ch) < 32 else ch for ch in part)
        safe = safe.rstrip(" .")
        if safe:
            parts.append(safe)
    if not parts:
        return None

    if ext.lower() != ".zl" and parts[-1].upper().endswith(".ZL_"):
        parts[-1] = parts[-1][:-4]
    return os.path.join(*parts)


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


def resolve_output_path(
    folder_name: str,
    refs: dict[tuple[int, int], str],
    container_id: int,
    file_id: int,
    ext: str,
) -> tuple[str, str]:
    fallback = f"file_{file_id:06d}{ext}"
    ref_name = refs.get((container_id, file_id))
    rel_name = normalize_ref_filename(ref_name, ext) if ref_name else None
    if not rel_name:
        rel_name = fallback

    output_path = os.path.join(folder_name, rel_name)
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return next_available_output_path(output_path), rel_name
