#!/usr/bin/env python3
"""E11 iButton protocol-level TIM1 BUSY-safe start, pin and STOP pairing.

Applies only after the exact pinned native timer-lease patch; keeps the
historical HAL void APIs ABI-compatible. NO device, release or flash.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
B = "targets/f7/furi_hal/furi_hal_ibutton.c"
H = "targets/f7/furi_hal/furi_hal_ibutton.h"
P = "lib/ibutton/protocols/misc/protocol_group_misc.c"
A = "targets/f7/api_symbols.csv"
EXPECTED_DIRTY = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    "targets/f7/api_symbols.csv",
    "applications/system/js_app/modules/js_gpio.c",
    "lib/pulse_reader/pulse_reader.c",
    "lib/digital_signal/digital_sequence.c",
    "targets/f7/furi_hal/furi_hal_ibutton.c",
}
MARKER = "furi_hal_ibutton_emulate_try_start_with_pin"

def once(s: str, a: str, b: str) -> str:
    if s.count(a) != 1:
        raise ValueError("Missing/ambiguous exact pinned iButton anchor " + repr(a[:100]))
    return s.replace(a, b, 1)

def patch(h: str, b: str, p: str, api: str) -> tuple[str, str, str, str]:
    if MARKER in h or MARKER in b or MARKER in p:
        raise ValueError("iButton protocol integration already applied")
    if "/* E11 native iButton TIM1 cooperative lease (timer only)." not in b:
        raise ValueError("Prior native iButton timer lease not applied")

    h = once(h, "/**\n * Start emulation timer\n",
        """/* E11 internal protocol-aware API: never configure pin if TIM1 is BUSY.
 * Existing void HAL symbols are preserved for historical callers.
 * configure_pin is only for the native Misc protocol's internal iButton pin.
 */
bool furi_hal_ibutton_emulate_try_start_with_pin(
    uint32_t period,
    FuriHalIbuttonEmulateCallback callback,
    void* context,
    bool configure_pin);

/* Returns true only after the native timer/IRQ are safely stopped.
 * Unexpectedly lost TIM1 prevents unrelated pin teardown.
 */
bool furi_hal_ibutton_emulate_try_stop(void);

/**
 * Start emulation timer
""")

    start_head = """void furi_hal_ibutton_emulate_start(
    uint32_t period,
    FuriHalIbuttonEmulateCallback callback,
    void* context) {"""
    start_new = """bool furi_hal_ibutton_emulate_try_start_with_pin(
    uint32_t period,
    FuriHalIbuttonEmulateCallback callback,
    void* context,
    bool configure_pin) {"""
    b = once(b, start_head, start_new)
    a = b.index(start_new)
    z = b.index("\nvoid furi_hal_ibutton_emulate_set_next(", a)
    part = b[a:z]
    # The void start previously has early returns only on failed ownership.
    if part.count("return;") != 2:
        raise ValueError(f"Unexpected native iButton START early-return count {part.count('return;')}")
    part = part.replace("return;", "return false;")
    part = once(part,
        "    furi_hal_ibutton->e11_lease_handle = lease;\n"
        "    furi_hal_ibutton->state = FuriHalIbuttonStateRunning;",
        """    furi_hal_ibutton->e11_lease_handle = lease;
    /* Only touch the internal iButton pin AFTER owning TIM1 and
     * BEFORE unmasking timer IRQ/callback. No pin changes on denial.
     */
    if(configure_pin) furi_hal_ibutton_pin_configure();
    furi_hal_ibutton->state = FuriHalIbuttonStateRunning;""")
    part = once(part, """    LL_TIM_EnableCounter(FURI_HAL_IBUTTON_TIMER);
}
""", """    LL_TIM_EnableCounter(FURI_HAL_IBUTTON_TIMER);
    return true;
}

/* Preserve the published void HAL API for independent native callers. */
void furi_hal_ibutton_emulate_start(
    uint32_t period,
    FuriHalIbuttonEmulateCallback callback,
    void* context) {
    (void)furi_hal_ibutton_emulate_try_start_with_pin(period, callback, context, false);
}
""")
    b = b[:a] + part + b[z:]

    stop_head = "void furi_hal_ibutton_emulate_stop(void) {"
    b = once(b, stop_head, "bool furi_hal_ibutton_emulate_try_stop(void) {")
    a = b.index("bool furi_hal_ibutton_emulate_try_stop(void)")
    z = b.index("\nvoid furi_hal_ibutton_pin_configure(", a)
    part = b[a:z]
    if part.count("return;") != 2:
        raise ValueError(f"Unexpected native iButton STOP early-return count {part.count('return;')}")
    part = part.replace("return;", "return false;")
    part = once(part, """            furi_hal_ibutton->e11_lease_fault = true;
        }
    }
}
""", """            furi_hal_ibutton->e11_lease_fault = true;
        }
        /* Timer and IRQ were torn down before releasing the lease.
         * Its failure is sticky, but internal-pin cleanup is now safe.
         */
        return true;
    }
    return false;
}

void furi_hal_ibutton_emulate_stop(void) {
    (void)furi_hal_ibutton_emulate_try_stop();
}
""")
    b = b[:a] + part + b[z:]

    p = once(p, """    ProtocolDict* dict;
    ProtocolId emulate_id;
} iButtonProtocolGroupMisc;""", """    ProtocolDict* dict;
    ProtocolId emulate_id;
    bool emulate_active; /* E11: true only after TIM1 and internal pin acquired */
} iButtonProtocolGroupMisc;""")
    p = once(p, "    group->emulate_id = PROTOCOL_NO;\n",
             "    group->emulate_id = PROTOCOL_NO;\n    group->emulate_active = false;\n")
    p = once(p, """    group->emulate_id = id;
    protocol_dict_set_data(group->dict, id, data, protocol_dict_get_data_size(group->dict, id));
    protocol_dict_encoder_start(group->dict, group->emulate_id);

    furi_hal_ibutton_pin_configure();
    furi_hal_ibutton_emulate_start(0, ibutton_protocol_group_misc_emulate_callback, group);
}""", """    /* Repeat starts cannot rewrite a running protocol dictionary. */
    if(group->emulate_active) return;
    group->emulate_id = id;
    protocol_dict_set_data(group->dict, id, data, protocol_dict_get_data_size(group->dict, id));
    protocol_dict_encoder_start(group->dict, group->emulate_id);

    group->emulate_active = furi_hal_ibutton_emulate_try_start_with_pin(
        0, ibutton_protocol_group_misc_emulate_callback, group, true);
}""")
    p = once(p, """    UNUSED(group);
    UNUSED(data);
    UNUSED(id);
    furi_hal_ibutton_emulate_stop();
    furi_hal_ibutton_pin_reset();
}""", """    UNUSED(data);
    UNUSED(id);
    if(!group->emulate_active) return;
    if(furi_hal_ibutton_emulate_try_stop()) {
        /* Never reset someone else's iButton pin after clock/owner loss. */
        furi_hal_ibutton_pin_reset();
        group->emulate_active = false;
    }
}""")
    api = once(api, "Function,+,furi_hal_ibutton_emulate_stop,void,\n",
               "Function,+,furi_hal_ibutton_emulate_stop,void,\n"
               'Function,+,furi_hal_ibutton_emulate_try_start_with_pin,_Bool,"uint32_t, FuriHalIbuttonEmulateCallback, void*, _Bool"\n'
               "Function,+,furi_hal_ibutton_emulate_try_stop,_Bool,\n")
    return h, b, p, api

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("firmware_root", type=Path)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PINNED: raise ValueError("Unexpected pinned Momentum HEAD")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked or renamed firmware file refused")
            dirty.add(line[3:])
        if dirty!=EXPECTED_DIRTY:
            raise ValueError("Unreviewed native HAL modifications: "+repr(sorted(dirty)))
        before=[(root/path).read_text(encoding="utf-8") for path in (H,B,P,A)]
        updated=patch(*before)
        print("E11 IBUTTON NATIVE PROTOCOL PIN/TIM1 START+STOP SOURCE CHECK PASS")
        if args.apply:
            for path, content in zip((H,B,P,A),updated):
                (root/path).write_text(content,encoding="utf-8")
                print("PATCHED SOURCE ONLY: "+path)
            print("NO DEVICE/FLASH/SD/USB, no Stable/main changes")
        else:
            print("SOURCE DRY-RUN ONLY")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 iButton protocol refused: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
