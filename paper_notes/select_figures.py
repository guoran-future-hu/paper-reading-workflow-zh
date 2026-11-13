"""List manifest visuals, then record which ones the note embeds.

Bare run prints the candidates. `--id` replaces the selection; `--skip` excludes a selected item.
"""
from __future__ import annotations

import argparse
import json

from paper_notes.config import load_config
from paper_notes.paper_dir import embedded_items, load_manifest, resolve_paper_dir, save_manifest


def apply_selection(manifest: dict, ids: list[int], skips: list[int], unskips: list[int]) -> dict:
    known = {item.get("id") for item in manifest.get("items", [])}
    unknown = sorted(set(ids + skips + unskips) - known)
    if unknown:
        raise SystemExit(f"error: no manifest item with id {unknown}")
    for item in manifest.get("items", []):
        if ids:
            item["selected"] = item.get("id") in ids
        if item.get("id") in skips:
            item["skip"] = True
        if item.get("id") in unskips:
            item.pop("skip", None)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose the visuals a paper note embeds.")
    parser.add_argument("--paper-dir", required=True, help="raw/<paper-id>/ folder or bare paper id")
    parser.add_argument("--id", action="append", type=int, default=[], help="Select this item; repeatable, replaces")
    parser.add_argument("--skip", action="append", type=int, default=[], help="Mark item skip: true; repeatable")
    parser.add_argument("--unskip", action="append", type=int, default=[], help="Clear an item's skip; repeatable")
    parser.add_argument("--config", help="JSON config; defaults to ./paper-notes.config.json")
    args = parser.parse_args()

    paper_dir = resolve_paper_dir(args.paper_dir, load_config(args.config))
    manifest = load_manifest(paper_dir)
    if args.id or args.skip or args.unskip:
        save_manifest(paper_dir, apply_selection(manifest, args.id, args.skip, args.unskip))
    print("id  S=selected x=skip  page  caption")
    for item in manifest.get("items", []):
        flags = ("S" if item.get("selected") else "-") + ("x" if item.get("skip") else " ")
        page = f"p{item['page']}" if item.get("page") else ""
        print(f"{item.get('id'):>3} {flags} {page:>4}  {(item.get('caption') or item.get('path', ''))[:110]}")
    print(json.dumps({"items": len(manifest.get("items", [])), "embedded": len(embedded_items(manifest))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
