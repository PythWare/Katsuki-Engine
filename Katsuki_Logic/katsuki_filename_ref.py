import os, re, struct
from pathlib import Path

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


def scan_exe_pointer_runs(exe_path: Path, *, min_run: int = 8):
    try:
        import pefile
    except ImportError as exc:
        raise RuntimeError(
            "pefile is only required when regenerating filename.ref from AOT2 executables. "
            "Normal Katsuki unpack/repack use with an existing filename.ref only needs Pillow."
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
        if text and (text.startswith("File/") or text.startswith("Linkdata/")):
            return offset, string_offset, text
        return None

    runs = []
    for section in pe.sections:
        section_name = section.Name.rstrip(b"\0").decode("ascii", errors="ignore")
        if section_name not in (".rdata", ".data"):
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


def dummy_filename_for_container(container_path: str) -> str | None:
    if container_path == "LINKDATA_D.BIN":
        return "File/Debug/Dummy/dummy_d.bin"
    if container_path == "EX/LINKDATA_EX_MASTER.BIN":
        return "File/Debug/Dummy/dummy_ex.bin"
    return None


def extract_filename_refs_from_exes(root: str | os.PathLike = "."):
    root_path = Path(root)
    logic_dir = root_path / "Katsuki_Logic"
    exe_paths = [
        logic_dir / "AOT2_EU.exe",
        logic_dir / "AOT2_AS.exe",
        logic_dir / "AOT2_JP.exe",
    ]

    counts_by_path = {
        path.casefold(): read_container_toc_count(root_path / path)
        for path in CONTAINER_PATHS.values()
    }
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
            used_runs.add(run_index)
            for file_id, (_ptr_off, _str_off, filename) in enumerate(run):
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

        patch_eden = "PATCH/LINKDATA_PATCH_EDEN_000.BIN"
        patch_eden_count = counts_by_path.get(patch_eden.casefold())
        if patch_eden_count:
            composite_runs = [
                run for run in file_runs
                if len(run) > patch_eden_count
                and run[0][2].startswith("File/Stage/ST24_00/")
            ]
            if composite_runs:
                run = composite_runs[0]
                for file_id, (_ptr_off, _str_off, filename) in enumerate(run[:patch_eden_count]):
                    add_ref(patch_eden, file_id, filename, exe_path.name)
                stats.append(
                    f"{exe_path.name}: {patch_eden} <- first {patch_eden_count} names from composite run"
                )

    return refs, stats, conflicts


def write_filename_ref(
    refs: dict[tuple[int, int], tuple[str, str]],
    out_path: str | os.PathLike = DEFAULT_REF_NAME,
    *,
    stats: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> None:
    lines = [
        f"# {REF_VERSION}",
        "# columns: container_id<TAB>container_path<TAB>toc_index<TAB>filename<TAB>source_exe",
        "# generated from Katsuki_Logic/AOT2_EU.exe, AOT2_AS.exe, and AOT2_JP.exe when present",
    ]
    if stats:
        for item in stats:
            lines.append(f"# mapped: {item}")
    if conflicts:
        for item in conflicts:
            lines.append(f"# conflict: {item}")
    for cid, path in CONTAINER_PATHS.items():
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


def generate_filename_ref(root: str | os.PathLike = ".", out_path: str | os.PathLike = DEFAULT_REF_NAME):
    refs, stats, conflicts = extract_filename_refs_from_exes(root)
    write_filename_ref(refs, out_path, stats=stats, conflicts=conflicts)
    return refs, stats, conflicts


if __name__ == "__main__":
    refs, stats, conflicts = generate_filename_ref()
    print(f"Wrote {DEFAULT_REF_NAME} with {len(refs)} filename entries.")
    print(f"Mapped tables: {len(stats)}")
    print(f"Conflicts: {len(conflicts)}")
