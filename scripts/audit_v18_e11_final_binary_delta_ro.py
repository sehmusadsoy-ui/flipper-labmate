#!/usr/bin/env python3
"""Compare two PINNED E11 Actions review bundles: read-only, never deploy.

Reports binary *difference*, never binary/runtime equivalence. This tool
does not access any hardware, SD card, release asset or installed firmware.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

FILES = ("labmate.fap", "firmware.dfu", "js_gpio.module", "firmware-full-update.tgz")
OTHER = ("PROVENANCE.txt", "SHA256SUMS.txt", "READ_ME_FIRST.txt")
MOMENTUM = "d3f89dfe2ef6b01839201598e9be1590cba80322"
PATCH_SHA = "1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80"
TRIAL = {
    "source": "ba379f20fb29369501e1057f570a911f71ac83f8",
    "run": "38966248325",
    "labmate.fap": "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0",
    "firmware.dfu": "88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
    "firmware-full-update.tgz": "11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553",
}
FINAL = {
    "source": "99cb65d0194dc59d423cfa439c90618ac6b9f114",
    "run": "39035056937",
    "labmate.fap": "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61",
    "firmware.dfu": "e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
    "firmware-full-update.tgz": "cd12be2a85512dcd360e6b93e027fa2ad9136a76602ba01036dc235b7a804dee",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def metadata(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ": " not in line:
            continue
        k, v = line.split(": ", 1)
        if not k or k in out:
            raise ValueError("duplicate or invalid provenance field")
        out[k] = v
    return out


def validate(root: Path, expected: dict[str, str]) -> None:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("artifact directory not regular")
    entries = list(root.iterdir())
    allowed = set(FILES + OTHER)
    if {f.name for f in entries} != allowed:
        raise ValueError("review artifact file inventory differs from exact seven files")
    for file in entries:
        if not file.is_file() or file.is_symlink():
            raise ValueError("special file or symbolic link forbidden")
        if file.stat().st_size > 85*1024*1024 or file.stat().st_size <= 0:
            raise ValueError("oversized or empty review file: " + file.name)
    sums: dict[str, str] = {}
    for row in (root/"SHA256SUMS.txt").read_text("utf-8").splitlines():
        fields = row.split()
        if len(fields) != 2 or fields[1] not in FILES or fields[1] in sums:
            raise ValueError("invalid SHA256SUMS line")
        sums[fields[1]] = fields[0].lower()
    if set(sums) != set(FILES):
        raise ValueError("missing SHA record")
    for name in FILES:
        actual = digest(root/name)
        if actual != expected[name] or sums[name] != actual:
            raise ValueError("independent pinned SHA mismatch: " + name)
    p = metadata((root/"PROVENANCE.txt").read_text("utf-8"))
    for field,value in {
        "LabMate commit": expected["source"],
        "Actions run": expected["run"],
        "Momentum base": MOMENTUM,
        "E11 firmware diff SHA256": PATCH_SHA,
    }.items():
        if p.get(field) != value:
            raise ValueError("pinned provenance mismatch: " + field)
    note = (root/"READ_ME_FIRST.txt").read_text("utf-8")
    for token in ("NOT A RELEASE", "DO NOT FLASH", "Never mix this matched FAP"):
        if token not in note:
            raise ValueError("review-only warning missing: " + token)


def difference_count(left: Path, right: Path) -> tuple[int,int,int]:
    """Count changed bytes by position; no claim about semantics."""
    n = 0
    length_left = length_right = 0
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            x,y=a.read(1024*1024),b.read(1024*1024)
            if not x and not y:
                break
            n += sum(z!=w for z,w in zip(x,y))
            n += abs(len(x)-len(y))
            length_left += len(x)
            length_right += len(y)
    return n,length_left,length_right


def bounded_changed_offsets(left: Path, right: Path, limit: int = 16) -> list[int]:
    """Actual changed byte offsets for small identical-length DFUs, never interpret semantics."""
    a,b=left.read_bytes(),right.read_bytes()
    if len(a)!=len(b) or len(a)>2_000_000:
        raise ValueError("DFU lengths differ or exceed small review bound")
    offsets=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    if len(offsets)>limit:
        raise ValueError("too many DFU changed bytes to report bounded offsets")
    return offsets


def audit(trial: Path, final: Path, first: dict[str,str] = TRIAL,
          second: dict[str,str] = FINAL) -> dict[str,tuple[int,int,int]]:
    if trial.resolve() == final.resolve():
        raise ValueError("two independent artifact directories required")
    validate(trial,first)
    validate(final,second)
    if first["js_gpio.module"] != second["js_gpio.module"]:
        raise ValueError("native JS module drift from operator-tested pair")
    if first["labmate.fap"] == second["labmate.fap"]:
        raise ValueError("final-label FAP unexpectedly unchanged")
    if first["firmware.dfu"] == second["firmware.dfu"]:
        raise ValueError("firmware unexpectedly identical to pinned distinct hashes")
    return {name:difference_count(trial/name,final/name)
            for name in ("labmate.fap","firmware.dfu","js_gpio.module")}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial",type=Path,required=True)
    parser.add_argument("--final",type=Path,required=True)
    options=parser.parse_args()
    result=audit(options.trial,options.final)
    for name,(changed,old,new) in result.items():
        print(f"E11 BYTE DELTA {name}: changed-by-position={changed} trial-bytes={old} candidate-bytes={new}")
    offsets=bounded_changed_offsets(options.trial/"firmware.dfu", options.final/"firmware.dfu")
    print("E11 DFU byte offsets of changes: " + ", ".join(map(str, offsets)))
    print("E11 DFU last-16-byte suffix start: " + str(result["firmware.dfu"][1]-16))
    # Context is informational: even a printable byte is not proof of
    # firmware ABI or behavior equivalence. Review only changed payload bytes.
    firmware_payload_end=result["firmware.dfu"][1]-16
    left=(options.trial/"firmware.dfu").read_bytes()
    right=(options.final/"firmware.dfu").read_bytes()
    for pos in offsets:
        if pos>=firmware_payload_end:
            continue
        start=max(0,pos-14)
        end=min(firmware_payload_end,pos+15)
        print(f"E11 DFU payload delta at {pos} trial-context-hex={left[start:end].hex()}")
        print(f"E11 DFU payload delta at {pos} final-context-hex={right[start:end].hex()}")
    print("Unchanged source and small byte delta do NOT by themselves prove unchanged firmware behavior.")
    print("E11 PINNED PAIR IDENTITIES PASS; BINARY DIFFERENCE REPORT ONLY")
    print("DO NOT INFER DFU RUNTIME EQUIVALENCE, DEVICE PASS, SAFE FAP-ONLY MIX, OR RELEASE APPROVAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
