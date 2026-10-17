#!/usr/bin/env python3
"""Read-only E11 publication boundary: protect original public releases.

A PASS here means historical GitHub tags/assets and frozen production paths
are unchanged. It NEVER approves a new Stable, firmware update or rollback.
All input JSON must be fetched from the GitHub API independently of this file.
"""
import argparse
import json
import sys
from pathlib import Path

FROZEN_SOURCE = "99cb65d0194dc59d423cfa439c90618ac6b9f114"
RELEASES = {
    "v1.4": {
        "commit": "84e1d8979d0631c003f9ae5f3e25596f9cb496e6",
        "assets": {
            "labmate-v1.4.fap": (18692, "sha256:b5be0a27709ea2c4fe8d63269404d50a4e7d8863c1e8e773063764f9f607cf25"),
            "SHA256SUMS.txt": (83, "sha256:d0b017405cd238f254f387493fcc6cf15e09fcf89880a6d06fecbb80a64b91e2"),
        },
    },
    "v1.8": {
        "commit": "02b05639364d6dd71f5eb70456eca379c59218cb",
        "assets": {
            "labmate.fap": (65580, "sha256:119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0"),
            "SHA256SUMS.txt": (78, "sha256:65fd45ccda9fc67b8c9032c2a7a60f3c8aba1a0d832a09e7f42bc6b842f65bb8"),
        },
    },
}


class PreservationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise PreservationError(message)


def check_release(tag, git_ref, release):
    expected = RELEASES[tag]
    require(isinstance(git_ref, dict) and isinstance(release, dict), "Malformed tag/release JSON")
    obj = git_ref.get("object")
    require(
        git_ref.get("ref") == "refs/tags/" + tag
        and isinstance(obj, dict)
        and obj.get("type") == "commit"
        and obj.get("sha") == expected["commit"],
        tag + ": tag target changed or could not be authenticated",
    )
    require(
        release.get("tag_name") == tag
        and release.get("target_commitish") == expected["commit"]
        and release.get("draft") is False
        and release.get("prerelease") is False
        and bool(release.get("published_at")),
        tag + ": public release metadata changed",
    )
    assets = release.get("assets")
    require(isinstance(assets, list), tag + ": assets missing")
    observed = {}
    for asset in assets:
        require(isinstance(asset, dict), tag + ": malformed asset")
        name = asset.get("name")
        require(isinstance(name, str) and name not in observed, tag + ": invalid/duplicate asset")
        observed[name] = (asset.get("size"), asset.get("digest"))
    require(observed == expected["assets"], tag + ": published asset inventory/hash changed")


def is_production_file(path):
    return (
        path.startswith("src/")
        or path in ("application.fam", "labmate_10px.png")
        or path.startswith("scripts/patch_momentum_")
    )


def check_source_freeze(comparison, expected_head):
    require(isinstance(comparison, dict), "Malformed compare JSON")
    base = comparison.get("base_commit")
    head = comparison.get("head_commit")
    require(isinstance(base, dict) and base.get("sha") == FROZEN_SOURCE,
            "Frozen E11 binary source base changed")
    require(isinstance(head, dict) and head.get("sha") == expected_head,
            "Compared branch head differs from checked-out revision")
    require(comparison.get("status") in ("ahead", "identical")
            and comparison.get("behind_by") == 0,
            "Frozen base is not an ancestor of candidate")
    count = comparison.get("total_commits")
    require(type(count) is int and 0 <= count < 250,
            "Compare pagination limit; refuse incomplete commit evidence")
    files = comparison.get("files")
    require(isinstance(files, list) and len(files) < 300,
            "Compare file pagination limit; refuse incomplete diff")
    for entry in files:
        require(isinstance(entry, dict) and isinstance(entry.get("filename"), str),
                "Malformed compare file")
        current = entry["filename"]
        previous = entry.get("previous_filename")
        require(not is_production_file(current)
                and not (isinstance(previous, str) and is_production_file(previous)),
                "Frozen production/firmware-patch path changed: " + current)


def audit(tag14, release14, tag18, release18, comparison, expected_head):
    check_release("v1.4", tag14, release14)
    check_release("v1.8", tag18, release18)
    require(len(expected_head) == 40 and all(c in "0123456789abcdef" for c in expected_head),
            "Bad expected HEAD SHA")
    check_source_freeze(comparison, expected_head)
    return "E11 PUBLIC RELEASE/TAG PRESERVATION + FROZEN PRODUCTION SOURCE PASS (READ ONLY); NEW STABLE NO-GO"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("tag14", "release14", "tag18", "release18", "comparison"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    try:
        documents = [json.loads(getattr(args, name).read_text(encoding="utf-8"))
                     for name in ("tag14", "release14", "tag18", "release18", "comparison")]
        print(audit(*documents, args.expected_head))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("E11 PUBLIC RELEASE PRESERVATION REFUSED - NO PUBLISH: " + str(exc),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
