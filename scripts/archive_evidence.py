"""把完整证据保存为可逐字节核验的发布附件，源码树只保留摘要。"""

import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"


def retained(path):
    relative = path.relative_to(EVIDENCE)
    if len(relative.parts) == 1 and path.name in {"README.md", "archive-index.json"}:
        return True
    if relative.parts[:2] == ("p1-06", "ctest-samples"):
        return True
    if "runs" in relative.parts or "sandboxes" in relative.parts:
        return False
    return path.suffix == ".json" and (
        len(relative.parts) == 2 or path.name in {"summary.json", "source-manifest.json"}
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        parser.error("目标已存在，请先核对已有附件")
    paths = sorted(p for p in EVIDENCE.rglob("*") if p.is_file())
    records = []
    for path in paths:
        if path.is_symlink():
            parser.error("证据包含链接")
        content = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    manifest = {"schema_version": 1, "files": records}
    work = ROOT / ".repropatch/evidence-archives" / args.tag
    work.mkdir(parents=True, exist_ok=True)
    manifest_path = work / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with tarfile.open(target, "x:gz") as archive:
        for record, path in zip(records, paths, strict=True):
            archive.add(path, arcname=record["path"], recursive=False)
        archive.add(manifest_path, arcname="evidence-manifest.json", recursive=False)
    with tarfile.open(target) as archive:
        assert len(archive.getmembers()) == len(records) + 1
        for record in records:
            content = archive.extractfile(record["path"]).read()
            assert len(content) == record["size"]
            assert hashlib.sha256(content).hexdigest() == record["sha256"]
    digest = hashlib.file_digest(target.open("rb"), "sha256").hexdigest()
    target.with_name(target.name + ".sha256").write_text(f"{digest}  {target.name}\n")
    removed = [p for p in paths if not retained(p)]
    index = {
        "schema_version": 1,
        "release_tag": args.tag,
        "archive": target.name,
        "sha256": digest,
        "size_bytes": target.stat().st_size,
        "files": len(records),
        "uncompressed_bytes": sum(r["size"] for r in records),
        "manifest": "evidence-manifest.json",
        "retained_files": len(paths) - len(removed),
        "url": f"https://github.com/lilong555/ReproPatch/releases/download/{args.tag}/{target.name}",
        "verification": "逐文件原始字节 SHA-256 与大小一致",
    }
    if args.compact:
        for path in removed:
            destination = work / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(path, destination)
        for directory in sorted(EVIDENCE.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    (EVIDENCE / "archive-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
