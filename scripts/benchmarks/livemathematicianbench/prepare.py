"""Materialize the downloaded LiveMathematicianBench using fixed SkillOpt IDs.

Standard library only; no network, model calls, or environment installation.
Original records are retained, with additional top-level SkillOpt loader fields.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data/livemathematicianbench"
RAW = BASE / "raw"
IDS = ROOT / "external/SkillOpt/data/livemathematicianbench_id_split"
OUTPUT = BASE / "prepared_v1"
COUNTS = {"train": 35, "val": 17, "test": 125}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()


def build():
    if git(RAW, "status", "--porcelain"):
        raise ValueError("Raw checkout has local changes; preserve a clean source snapshot")
    payloads, sources, selected_ids = {}, {}, set()
    id_hashes, output_hashes, source_counts = {}, {}, {}
    for split, expected_count in COUNTS.items():
        id_path = IDS / split / "items.json"
        manifest_rows = read(id_path)
        if len(manifest_rows) != expected_count:
            raise ValueError(f"Unexpected {split} manifest count")
        id_hashes[f"{split}/items.json"] = sha256(id_path)
        items = []
        for entry in manifest_rows:
            rel = entry["source_file"]
            source_path = (RAW / rel).resolve()
            if not source_path.is_relative_to(RAW.resolve()):
                raise ValueError("Source path escapes raw checkout")
            if rel not in sources:
                rows = read(source_path)
                sources[rel] = {f"{r['month']}:{r['no']}": r for r in rows}
                if len(rows) != len(sources[rel]):
                    raise ValueError(f"Duplicate source IDs in {rel}")
                source_counts[rel] = len(rows)
            item_id = entry["id"]
            if item_id in selected_ids:
                raise ValueError(f"Repeated or overlapping ID: {item_id}")
            selected_ids.add(item_id)
            row = sources[rel][item_id]
            for key in ("month", "no", "paper_link"):
                if row[key] != entry[key]:
                    raise ValueError(f"Source identity mismatch: {item_id}/{key}")
            mcq = row["mcq"]
            choices = deepcopy([mcq["correct_choice"], *mcq["choices"]])
            if (len(choices) != 5
                    or {c["label"] for c in choices} != set("ABCDE")
                    or not all(c["text"].strip() for c in choices)
                    or not mcq["question"].strip()):
                raise ValueError(f"Invalid MCQ: {item_id}")
            additions = {"id", "question", "choices", "correct_choice", "source_file"}
            if additions.intersection(row):
                raise ValueError(f"Unexpected source schema collision: {item_id}")
            item = deepcopy(row)
            item.update(
                id=item_id,
                question=mcq["question"],
                choices=sorted(choices, key=lambda c: c["label"]),
                correct_choice=deepcopy(mcq["correct_choice"]),
                source_file=rel,
            )
            items.append(item)
        name = f"{split}/items.json"
        payloads[name] = items
        output_hashes[name] = hashlib.sha256(encode(items)).hexdigest()

    payloads["split_manifest.json"] = {
        "benchmark": "LiveMathematicianBench",
        "content_revision": git(RAW, "rev-parse", "HEAD"),
        "source_url": git(RAW, "remote", "get-url", "origin"),
        "source_root": str(RAW.relative_to(ROOT)),
        "source_files": {
            rel: {"sha256": sha256(RAW / rel), "count": source_counts[rel]}
            for rel in sorted(sources)
        },
        "split_mode": "fixed_ids",
        "split_id_root": str(IDS.relative_to(ROOT)),
        "split_id_source_commit": git(IDS, "rev-parse", "HEAD"),
        "split_id_file_sha256": id_hashes,
        "counts": COUNTS,
        "order": "Exact order of each SkillOpt ID manifest; no resampling",
        "content_policy": "Downloaded source content; ID manifests select membership only",
        "format": "Original record retained; top-level fields added for SkillOpt split_dir loading",
        "output_sha256": output_hashes,
        "preparation_script_sha256": sha256(Path(__file__)),
    }
    return payloads


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate existing outputs without writing")
    args = parser.parse_args()
    payloads = {name: encode(value) for name, value in build().items()}
    # Check all existing files before writing; never overwrite differing material.
    for name, content in payloads.items():
        path = OUTPUT / name
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"Existing output differs: {path}")
        if args.check and not path.exists():
            raise FileNotFoundError(path)
    if OUTPUT.exists():
        unexpected = {str(p.relative_to(OUTPUT)) for p in OUTPUT.rglob("*") if p.is_file()} - payloads.keys()
        if unexpected:
            raise ValueError(f"Unexpected output files: {sorted(unexpected)}")
    if not args.check:
        for name, content in payloads.items():
            path = OUTPUT / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    handle.write(content)
    print(json.dumps({"status": "verified" if args.check else "prepared", "counts": COUNTS,
                      "unique_ids": sum(COUNTS.values()), "split_dir": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
