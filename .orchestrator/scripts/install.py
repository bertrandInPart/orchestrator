#!/usr/bin/env python3
"""
install.py — Package installer for adopting `.orchestrator` into an existing project.

This is the entry point for bringing the agentic feature-production chain into a project that
already exists ("already industrialized": its own CI, its own `.github/copilot-instructions.md`,
its own issue templates, etc.) without clobbering any of that. It is deliberately non-destructive:
it never overwrites a file that's already there and differs from the incoming version — it writes
the incoming version alongside as `<name>.orchestrator-suggested<ext>` and lists it for you to
merge by hand, instead of guessing.

Typical usage, from the root of the project you're adopting the chain into:

    python -c "$(curl -fsSL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/.orchestrator/scripts/install.py)"

or, if you already have a local clone of the orchestrator repo to install from:

    python /path/to/orchestrator/.orchestrator/scripts/install.py --source /path/to/orchestrator

Then, once installed:

    python .orchestrator/scripts/init-wizard.py

which adapts the freshly-installed files to your project's actual language/framework/paths and
ticket system (see that script's own docstring).

Updating later (after this project has already installed a version): re-run with `--update`. Any
file you have not modified since the last install is refreshed to the new version; anything you
have modified is left alone and the incoming version is written as a `.orchestrator-suggested`
sibling instead, exactly like a fresh-install conflict.

Flags:
    --source PATH_OR_URL   Where to fetch the package from. A local directory is copied directly;
                            anything else is treated as a `git clone --depth 1` URL. Defaults to
                            this project's own GitHub repo.
    --ref REF               Git branch/tag to install from when --source is a URL. Defaults to the
                            latest tag if any exist, else the remote's default branch.
    --target PATH           Project directory to install into. Defaults to the current directory
                            (resolved to its git root if inside one).
    --update                Treat this as an update to a previously-installed copy: refresh any
                            file unmodified since last install, leave modified files as conflicts.
    --dry-run               Show what would happen without writing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SOURCE = "https://github.com/<OWNER>/<REPO>"
INSTALL_RECORD_NAME = "INSTALLED.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def find_git_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except Exception:
        return start


def load_manifest(payload_dir: Path) -> list[dict]:
    manifest_path = payload_dir / ".orchestrator" / "manifest.yml"
    if not manifest_path.exists():
        print(f"ERROR: no manifest.yml found in payload at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required (pip install pyyaml).", file=sys.stderr)
        sys.exit(1)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return data["files"]


def resolve_ref(source: str, explicit_ref: str | None) -> str:
    if explicit_ref:
        return explicit_ref
    try:
        out = subprocess.run(
            ["git", "ls-remote", "--tags", "--sort=-v:refname", source],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            first_line = out.splitlines()[0]
            ref = first_line.split("refs/tags/")[-1]
            if ref and not ref.endswith("^{}"):
                return ref
    except Exception:
        pass
    return "main"


def fetch_payload(source: str, ref: str | None, tmp_dir: Path) -> tuple[Path, str]:
    """Returns (payload_dir, resolved_ref)."""
    source_path = Path(source)
    if source_path.exists() and source_path.is_dir():
        return source_path, "local"

    resolved_ref = resolve_ref(source, ref)
    print(f"==> Cloning {source} @ {resolved_ref} ...")
    clone_dir = tmp_dir / "payload"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", resolved_ref, source, str(clone_dir)],
        check=True,
    )
    return clone_dir, resolved_ref


def load_install_record(target: Path) -> dict:
    record_path = target / ".orchestrator" / INSTALL_RECORD_NAME
    if record_path.exists():
        return json.loads(record_path.read_text(encoding="utf-8"))
    return {"version": None, "ref": None, "installed_at": None, "files": {}}


def save_install_record(target: Path, record: dict, dry_run: bool) -> None:
    if dry_run:
        return
    record_path = target / ".orchestrator" / INSTALL_RECORD_NAME
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def suggested_path(target_file: Path) -> Path:
    if target_file.suffix:
        return target_file.with_name(
            target_file.stem + ".orchestrator-suggested" + target_file.suffix
        )
    return target_file.with_name(target_file.name + ".orchestrator-suggested")


def install(payload_dir: Path, target: Path, is_update: bool, dry_run: bool) -> dict:
    manifest = load_manifest(payload_dir)
    prior_record = load_install_record(target) if is_update else {"files": {}}
    prior_hashes: dict = prior_record.get("files", {})

    created, refreshed, unchanged, conflicts, seeded = [], [], [], [], []
    new_hashes: dict = {}

    for entry in manifest:
        rel_path = entry["path"]
        category = entry.get("category", "core")
        src_file = payload_dir / rel_path
        dst_file = target / rel_path

        if not src_file.exists():
            print(f"  WARNING: manifest lists {rel_path} but it's missing from the payload — skipping.")
            continue

        if not dst_file.exists():
            if category == "seed" and not is_update:
                # Seed files are still created on a fresh install (nothing to seed from yet);
                # they're just never treated as conflicts or auto-refreshed afterward.
                pass
            if not dry_run:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
            new_hashes[rel_path] = sha256_of(src_file)
            (seeded if category == "seed" else created).append(rel_path)
            continue

        # Destination already exists.
        if category == "seed":
            unchanged.append(rel_path)
            new_hashes[rel_path] = prior_hashes.get(rel_path) or (
                sha256_of(dst_file) if dst_file.exists() else ""
            )
            continue

        src_hash = sha256_of(src_file)
        dst_hash = sha256_of(dst_file)

        if src_hash == dst_hash:
            unchanged.append(rel_path)
            new_hashes[rel_path] = src_hash
            continue

        previously_installed_hash = prior_hashes.get(rel_path)
        untouched_since_install = (
            is_update and previously_installed_hash is not None
            and previously_installed_hash == dst_hash
        )

        if untouched_since_install:
            if not dry_run:
                shutil.copy2(src_file, dst_file)
            new_hashes[rel_path] = src_hash
            refreshed.append(rel_path)
        else:
            suggestion = suggested_path(dst_file)
            if not dry_run:
                suggestion.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, suggestion)
            # Deliberately NOT recorded in new_hashes: this file was never actually installed
            # by us (either it predates the chain, or the project has since diverged from what
            # we installed). Leaving it out of the record means the next `--update` still sees
            # no "previously installed hash" for it and re-flags it as a conflict again, instead
            # of treating the project's own content as something safe to silently overwrite.
            conflicts.append((rel_path, str(suggestion.relative_to(target)), category))

    return {
        "created": created, "refreshed": refreshed, "unchanged": unchanged,
        "conflicts": conflicts, "seeded": seeded, "new_hashes": new_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--target", default=".")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = find_git_root(Path(args.target).resolve())
    print("=" * 78)
    print("orchestrator package installer")
    print("=" * 78)
    print(f"Target project: {target}")
    print(f"Source        : {args.source}")
    print(f"Mode          : {'update' if args.update else 'fresh install'}"
          f"{' (dry run)' if args.dry_run else ''}\n")

    with tempfile.TemporaryDirectory(prefix="orchestrator-install-") as tmp:
        payload_dir, resolved_ref = fetch_payload(args.source, args.ref, Path(tmp))
        version = (payload_dir / ".orchestrator" / "VERSION")
        version_str = version.read_text(encoding="utf-8").strip() if version.exists() else "unknown"

        result = install(payload_dir, target, is_update=args.update, dry_run=args.dry_run)

        print(f"Package version: {version_str} (ref: {resolved_ref})\n")
        print(f"Created  : {len(result['created'])} file(s)")
        for f in result["created"]:
            print(f"    + {f}")
        if result["seeded"]:
            print(f"Seeded   : {len(result['seeded'])} starter file(s) (memory/telemetry/eval baselines)")
        if result["refreshed"]:
            print(f"Refreshed: {len(result['refreshed'])} file(s) (unmodified since last install)")
            for f in result["refreshed"]:
                print(f"    ~ {f}")
        print(f"Unchanged: {len(result['unchanged'])} file(s) already up to date")

        if result["conflicts"]:
            print(f"\nCONFLICTS: {len(result['conflicts'])} file(s) already exist and differ from "
                  f"the incoming version. Nothing was overwritten — the incoming version was "
                  f"written alongside for you to merge by hand:\n")
            integration_conflicts = [c for c in result["conflicts"] if c[2] == "integration"]
            core_conflicts = [c for c in result["conflicts"] if c[2] != "integration"]
            if integration_conflicts:
                print("  Needs manual merge into your existing setup (CI, repo-wide "
                      "instructions, issue intake):")
                for rel_path, suggestion, _ in integration_conflicts:
                    print(f"    {rel_path}  ->  see {suggestion}")
            if core_conflicts:
                print("  Chain-internal files that differ from a prior install (review before "
                      "adopting the new version):")
                for rel_path, suggestion, _ in core_conflicts:
                    print(f"    {rel_path}  ->  see {suggestion}")

        if not args.dry_run:
            record = {
                "version": version_str,
                "source": args.source,
                "ref": resolved_ref,
                "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "files": result["new_hashes"],
            }
            save_install_record(target, record, dry_run=args.dry_run)
            print(f"\nWrote .orchestrator/{INSTALL_RECORD_NAME}")

    print("\n" + "=" * 78)
    if args.dry_run:
        print("Dry run complete — nothing was written.")
    else:
        print("Install complete. Next: python .orchestrator/scripts/init-wizard.py")
    print("=" * 78)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: command failed: {e}", file=sys.stderr)
        sys.exit(1)
