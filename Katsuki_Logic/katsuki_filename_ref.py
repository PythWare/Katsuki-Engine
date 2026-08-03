"""Recover original asset filenames from the game executables"""
import os, re, struct
from pathlib import Path

from .katsuki_profiles import (
    GameProfile,
    get_profile,
    read_toc,
    resolve_containers,
)

REF_VERSION = "KATSUKI_FILENAME_REF_V1"
DEFAULT_REF_NAME = "filename.ref"

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

CONTAINER_IDS_BY_PATH = {
    path.casefold(): cid
    for cid, path in CONTAINER_PATHS.items()
}

INVALID_FILENAME_CHARS = '<>:"|?*'


def normalize_container_path(path: str) -> str:
    norm = (path or "").replace("\\", "/").strip()
    if norm.casefold().startswith("linkdata/"):
        norm = norm[9:]
    return norm


def read_container_toc_count(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            handle.read(4)
            raw = handle.read(4)
    except OSError:
        return None
    if len(raw) != 4:
        return None
    return struct.unpack("<I", raw)[0]


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
            cid = int(parts[0])
            file_id = int(parts[2])
        except ValueError:
            continue
        filename = parts[3].strip()
        if filename:
            refs[(cid, file_id)] = filename
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


def read_c_string(data: bytes, offset: int) -> str | None:
    if offset is None or offset < 0 or offset >= len(data):
        return None
    end = data.find(b"\0", offset)
    if end < 0 or end == offset or end - offset > 400:
        return None
    raw = data[offset:end]
    if any(byte < 32 or byte > 126 for byte in raw):
        return None
    return raw.decode("ascii", errors="ignore")


def scan_exe_pointer_runs(
    exe_path: Path,
    *,
    min_run: int = 8,
    prefixes: tuple[str, ...] = ("File/", "Linkdata/"),
    sections: tuple[str, ...] = (".rdata", ".data"),
):
    """Runs of consecutive 8 byte pointers that all point at matching strings"""
    try:
        import pefile
    except ImportError as exc:
        raise RuntimeError(
            "pefile is only required when regenerating a filename ref from the game "
            "executables. Normal Katsuki unpack/repack use with an existing ref only "
            "needs Pillow."
        ) from exc

    data = exe_path.read_bytes()
    pe = pefile.PE(str(exe_path), fast_load=True)
    imagebase = pe.OPTIONAL_HEADER.ImageBase

    def off_from_va(va: int) -> int | None:
        rva = va - imagebase
        if rva < 0:
            return None
        try:
            offset = pe.get_offset_from_rva(rva)
        except Exception:
            return None
        return offset if 0 <= offset < len(data) else None

    def ptr_string_at(offset: int):
        if offset + 8 > len(data):
            return None
        va = struct.unpack_from("<Q", data, offset)[0]
        string_offset = off_from_va(va)
        text = read_c_string(data, string_offset)
        if text and text.startswith(prefixes):
            return offset, string_offset, text
        return None

    runs = []
    for section in pe.sections:
        section_name = section.Name.rstrip(b"\0").decode("ascii", errors="ignore")
        if section_name not in sections:
            continue
        start = section.PointerToRawData
        end = start + section.SizeOfRawData
        offset = start
        while offset <= end - 8:
            hit = ptr_string_at(offset)
            if not hit:
                offset += 8
                continue
            run = []
            cursor = offset
            while cursor <= end - 8:
                hit = ptr_string_at(cursor)
                if not hit:
                    break
                run.append(hit)
                cursor += 8
            if len(run) >= min_run:
                runs.append(run)
            offset = cursor + 8
    return runs

AOT1_PREFIX = ("FILE/",)
AOT1_DUMMY_PREFIX = "FILE/DEBUG/dummy/"


def compressed_flag_conflicts(names: list[str], toc: list[dict]) -> int:
    conflicts = 0
    for index, name in enumerate(names):
        if index >= len(toc):
            break
        if name.upper().endswith(".ZL_") != bool(toc[index]["ds"]):
            conflicts += 1
    return conflicts

def partition_run(length: int, counts: list[int]) -> list[list[int]]:
    results: list[list[int]] = []

    def walk(remaining: int, used: frozenset[int], chosen: list[int]):
        if remaining == 0:
            results.append(list(chosen))
            return
        for position, count in enumerate(counts):
            if position in used or count > remaining:
                continue
            chosen.append(position)
            walk(remaining - count, used | {position}, chosen)
            chosen.pop()

    walk(length, frozenset(), [])
    return results


def extract_aot1_refs(exe_path: Path, containers: dict[int, str], root: Path):
    """
    Map AOT1 filename arrays onto container ids

    Returns (refs, stats, problems) where refs is {(cid, toc_index): filename}
    """
    refs: dict[tuple[int, int], str] = {}
    stats: list[str] = []
    problems: list[str] = []

    profile = get_profile("aot1")
    tocs: dict[int, list[dict]] = {}
    for cid, rel_path in containers.items():
        try:
            tocs[cid] = read_toc(root / rel_path, alignment=profile.alignment)
        except (OSError, IOError) as exc:
            problems.append(f"{rel_path}: {exc}")

    if not tocs:
        return refs, stats, problems

    single = {cid for cid, toc in tocs.items() if len(toc) == 1}
    multi = {cid: toc for cid, toc in tocs.items() if len(toc) > 1}

    ids = sorted(multi)
    counts = [len(multi[cid]) for cid in ids]

    runs = scan_exe_pointer_runs(exe_path, min_run=4, prefixes=AOT1_PREFIX)
    claimed: set[int] = set()

    for run in sorted(runs, key=len, reverse=True):
        available = [
            (position, cid) for position, cid in enumerate(ids) if cid not in claimed
        ]
        if not available:
            break
        usable_counts = [counts[position] for position, _cid in available]

        best = None
        for split in partition_run(len(run), usable_counts):
            ordered = sorted(split, key=lambda position: available[position][1])
            if ordered != split:
                continue
            conflicts = 0
            cursor = 0
            segments = []
            for position in split:
                _pos, cid = available[position]
                width = usable_counts[position]
                names = [text for _po, _so, text in run[cursor:cursor + width]]
                conflicts += compressed_flag_conflicts(names, multi[cid])
                segments.append((cid, names))
                cursor += width
            if best is None or conflicts < best[0]:
                best = (conflicts, segments)
            if conflicts == 0:
                break

        if not best:
            continue
        conflicts, segments = best
        if conflicts:
            problems.append(
                f"{exe_path.name}: rejected a {len(run)} name run, "
                f"{conflicts} entries disagree with the container about compression"
            )
            continue

        for cid, names in segments:
            for index, name in enumerate(names):
                refs[(cid, index)] = name
            claimed.add(cid)
            stats.append(f"{exe_path.name}: {containers[cid]} <- {len(names)} names")

    dummy = find_aot1_dummy_name(exe_path) if single else None
    for cid in single:
        if dummy:
            refs[(cid, 0)] = dummy
            stats.append(f"{exe_path.name}: {containers[cid]} <- 1 dummy name")

    missing = [containers[cid] for cid in multi if cid not in claimed]
    for name in missing:
        problems.append(f"{exe_path.name}: no verified filename array found for {name}")

    return refs, stats, problems


def find_aot1_dummy_name(exe_path: Path) -> str | None:
    """The single entry containers hold one debug placeholder"""
    runs = scan_exe_pointer_runs(
        exe_path, min_run=1, prefixes=(AOT1_DUMMY_PREFIX,), sections=(".data",)
    )
    for run in runs:
        for _ptr_off, _str_off, text in run:
            return text
    return None

def extract_aot1_filename_refs(
    root: str | os.PathLike = ".", exe_root: str | os.PathLike | None = None
):
    profile = get_profile("aot1")
    root_path = Path(root)
    exe_root_path = Path(exe_root) if exe_root is not None else root_path
    containers = resolve_containers(profile, root_path)

    refs: dict[tuple[int, int], tuple[str, str]] = {}
    stats: list[str] = []
    problems: list[str] = []

    if not containers:
        problems.append(
            "No AOT1 LINKDATA containers found. Put the toolkit next to the game data."
        )
        return refs, stats, problems

    searched = []
    for exe_name in profile.exe_names:
        for candidate in (exe_root_path / exe_name, exe_root_path / "Katsuki_Logic" / exe_name):
            searched.append(str(candidate))
            if not candidate.exists():
                continue
            found, exe_stats, exe_problems = extract_aot1_refs(candidate, containers, root_path)
            stats.extend(exe_stats)
            problems.extend(exe_problems)
            for key, name in found.items():
                refs.setdefault(key, (name, candidate.name))
            if found:
                return refs, stats, problems

    if not refs:
        problems.append(
            "Could not read filenames from an AOT1 executable. Looked for: "
            + ", ".join(profile.exe_names)
        )
    return refs, stats, problems


def dummy_filename_for_container(container_path: str) -> str | None:
    if container_path == "LINKDATA_D.BIN":
        return "File/Debug/Dummy/dummy_d.bin"
    if container_path == "EX/LINKDATA_EX_MASTER.BIN":
        return "File/Debug/Dummy/dummy_ex.bin"
    return None


def extract_filename_refs_from_exes(
    root: str | os.PathLike = ".", exe_root: str | os.PathLike | None = None
):
    root_path = Path(root)
    exe_root_path = Path(exe_root) if exe_root is not None else root_path
    exe_names = ("AOT2_EU.exe", "AOT2_AS.exe", "AOT2_JP.exe")
    exe_paths = [
        candidate
        for name in exe_names
        for candidate in (exe_root_path / name, exe_root_path / "Katsuki_Logic" / name)
    ]

    counts_by_path = {
        path.casefold(): read_container_toc_count(root_path / path)
        for path in CONTAINER_PATHS.values()
    }
    tocs_by_path: dict[str, list[dict]] = {}
    for path in CONTAINER_PATHS.values():
        try:
            tocs_by_path[path.casefold()] = read_toc(root_path / path, alignment=256)
        except (OSError, IOError):
            pass

    refs: dict[tuple[int, int], tuple[str, str]] = {}
    stats: list[str] = []
    conflicts: list[str] = []

    def add_ref(container_path: str, file_id: int, filename: str, source: str):
        cid = CONTAINER_IDS_BY_PATH.get(container_path.casefold())
        if cid is None:
            return
        key = (cid, file_id)
        old = refs.get(key)
        if old:
            if old[0] != filename:
                conflicts.append(
                    f"{container_path}#{file_id}: {old[0]} ({old[1]}) != {filename} ({source})"
                )
            return
        refs[key] = (filename, source)

    for exe_path in exe_paths:
        if not exe_path.exists():
            continue
        runs = scan_exe_pointer_runs(exe_path)
        container_runs = [run for run in runs if run[0][2].startswith("Linkdata/")]
        file_runs = [run for run in runs if run[0][2].startswith("File/")]
        exe_containers = []
        if container_runs:
            for _ptr_off, _str_off, name in container_runs[0]:
                norm = normalize_container_path(name)
                if norm.casefold() in CONTAINER_IDS_BY_PATH:
                    exe_containers.append(norm)

        available_by_count: dict[int, list[str]] = {}
        for container_path in exe_containers:
            count = counts_by_path.get(container_path.casefold())
            if count is not None and count > 1:
                available_by_count.setdefault(count, []).append(container_path)

        used_runs = set()
        for run_index, run in enumerate(file_runs):
            count = len(run)
            candidates = available_by_count.get(count, [])
            if len(candidates) != 1:
                continue
            container_path = candidates[0]
            names = [name for _ptr_off, _str_off, name in run]

            toc = tocs_by_path.get(container_path.casefold())
            if toc is not None:
                bad = compressed_flag_conflicts(names, toc)
                if bad:
                    conflicts.append(
                        f"{exe_path.name}: rejected {count} names for {container_path}, "
                        f"{bad} disagree with the container about compression"
                    )
                    continue

            used_runs.add(run_index)
            for file_id, filename in enumerate(names):
                add_ref(container_path, file_id, filename, exe_path.name)
            stats.append(f"{exe_path.name}: {container_path} <- {count} names")

        for container_path in exe_containers:
            count = counts_by_path.get(container_path.casefold())
            if count != 1:
                continue
            dummy = dummy_filename_for_container(container_path)
            if dummy:
                add_ref(container_path, 0, dummy, exe_path.name)
                stats.append(f"{exe_path.name}: {container_path} <- 1 dummy name")

    return refs, stats, conflicts


def write_filename_ref(
    refs: dict[tuple[int, int], tuple[str, str]],
    out_path: str | os.PathLike = DEFAULT_REF_NAME,
    *,
    stats: list[str] | None = None,
    conflicts: list[str] | None = None,
    container_paths: dict[int, str] | None = None,
    game_id: str = "aot2",
) -> None:
    if container_paths is None:
        container_paths = CONTAINER_PATHS
    lines = [
        f"# {REF_VERSION}",
        "# columns: container_id<TAB>container_path<TAB>toc_index<TAB>filename<TAB>source_exe",
        f"# game: {game_id}",
    ]
    if stats:
        for item in stats:
            lines.append(f"# mapped: {item}")
    if conflicts:
        for item in conflicts:
            lines.append(f"# conflict: {item}")
    for cid, path in container_paths.items():
        items = [
            (file_id, filename, source)
            for (ref_cid, file_id), (filename, source) in refs.items()
            if ref_cid == cid
        ]
        if not items:
            lines.append(f"# unmapped: {cid}\t{path}")
            continue
        for file_id, filename, source in sorted(items):
            lines.append(f"{cid}\t{path}\t{file_id}\t{filename}\t{source}")
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_filename_ref(
    root: str | os.PathLike = ".",
    out_path: str | os.PathLike | None = None,
    game_id: str = "aot2",
    exe_root: str | os.PathLike | None = None,
):
    """Rebuild the filename ref for one game"""
    from .katsuki_ref_runtime import ref_path

    profile = get_profile(game_id)
    if out_path is None:
        out_path = ref_path(profile)

    if game_id == "aot1":
        refs, stats, conflicts = extract_aot1_filename_refs(root, exe_root=exe_root)
        container_paths = resolve_containers(profile, root)
        for cid in profile.containers:
            container_paths.setdefault(cid, profile.candidates(cid)[0])
    else:
        refs, stats, conflicts = extract_filename_refs_from_exes(root, exe_root=exe_root)
        container_paths = CONTAINER_PATHS

    write_filename_ref(
        refs,
        out_path,
        stats=stats,
        conflicts=conflicts,
        container_paths=container_paths,
        game_id=game_id,
    )
    return refs, stats, conflicts


def ensure_filename_ref(profile: GameProfile, root: str | os.PathLike = "."):
    """Make sure a filename ref exists before unpacking, building one if not"""
    from .katsuki_ref_runtime import ref_path

    out_path = ref_path(profile)
    if out_path.exists():
        return out_path, ""

    try:
        refs, stats, problems = generate_filename_ref(Path(root), game_id=profile.game_id)
    except RuntimeError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"Could not build a filename ref: {exc}"

    if not refs:
        detail = "\n".join(problems[:4]) if problems else "no filename tables were recognised"
        return None, (
            f"No filenames could be recovered from the {profile.short_label} executable, "
            f"so assets will be extracted with numbered names.\n\n{detail}"
        )
    return out_path, f"Recovered {len(refs)} filenames into {profile.ref_filename}."

if __name__ == "__main__":
    import sys

    # usage: python -m Katsuki_Logic.katsuki_filename_ref <game> [bin_dir] [exe_dir]
    target = sys.argv[1] if len(sys.argv) > 1 else "aot2"
    bin_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    exe_dir = sys.argv[3] if len(sys.argv) > 3 else None

    profile = get_profile(target)
    refs, stats, conflicts = generate_filename_ref(bin_dir, game_id=target, exe_root=exe_dir)
    print(f"Wrote Katsuki_Logic/{profile.ref_filename} with {len(refs)} filename entries.")
    for item in stats:
        print(f"  mapped: {item}")
    for item in conflicts:
        print(f"  problem: {item}")
