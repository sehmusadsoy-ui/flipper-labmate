#!/usr/bin/env python3
"""E11 native infrared RX: propagate TIM2 BUSY to worker without dead thread.

Pinned Momentum, after all prior E11 patches through IR TX. Legacy void
symbols stay ABI compatible; new try-starts return bool for native callers.
No device flashing or Stable modifications.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
IR = "targets/f7/furi_hal/furi_hal_infrared.c"
HEADER = "targets/furi_hal_include/furi_hal_infrared.h"
WORKER = "lib/infrared/worker/infrared_worker.c"
WORKER_H = "lib/infrared/worker/infrared_worker.h"
API = "targets/f7/api_symbols.csv"
DIRTY = {
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
    "targets/f7/furi_hal/furi_hal_ibutton.h",
    "lib/ibutton/protocols/misc/protocol_group_misc.c",
    "targets/f7/furi_hal/furi_hal_nfc_timer.c",
    "targets/f7/furi_hal/furi_hal_nfc_i.h",
    "targets/f7/furi_hal/furi_hal_nfc.c",
    "targets/f7/furi_hal/furi_hal_infrared.c",
    "targets/furi_hal_include/furi_hal_infrared.h",
    "lib/infrared/worker/infrared_worker.c",
}
MARKER = "E11 IR RX BUSY-aware worker rollback"

def once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError("Unknown/ambiguous native RX signature " + repr(before[:90]))
    return text.replace(before, after, 1)

def patch(ir: str, h: str, worker: str, wh: str, api: str):
    if MARKER in worker or "furi_hal_infrared_async_rx_try_start" in h:
        raise ValueError("Infrared RX worker stage already applied")
    if "/* LabMate E11 native infrared TIM2 RX owner. */" not in ir:
        raise ValueError("Prior infrared RX lease missing")
    if "/* E11 native infrared TX timer/DMA/PA7 cooperative owner. */" not in ir:
        raise ValueError("Prior infrared TX worker lease missing")

    start = "void furi_hal_infrared_async_rx_start(void) {"
    stop = "\nvoid furi_hal_infrared_async_rx_stop(void) {"
    p = ir.index(start)
    end = ir.index(stop, p)
    block = ir[p:end]
    if block.count("return;") != 3:
        raise ValueError("Unreviewed native RX TIM2 start return count")
    block = block.replace(start, "bool furi_hal_infrared_async_rx_try_start(void) {", 1)
    block = block.replace("return;", "return false;")
    if not block.endswith("    LL_TIM_EnableCounter(INFRARED_RX_TIMER);\n}"):
        raise ValueError("Unrecognized RX START end")
    block = block[:-1] + """    return true;
}

/* Keep original public void symbol. Native worker uses bool status. */
void furi_hal_infrared_async_rx_start(void) {
    (void)furi_hal_infrared_async_rx_try_start();
}"""
    ir = ir[:p] + block + ir[end:]

    h = once(h, "void furi_hal_infrared_async_rx_start(void);",
             "void furi_hal_infrared_async_rx_start(void);\n"
             "/* Returns false without starting TIM2 when native/lease BUSY. */\n"
             "bool furi_hal_infrared_async_rx_try_start(void);")
    wh = once(wh, "void infrared_worker_rx_start(InfraredWorker* instance);",
              "void infrared_worker_rx_start(InfraredWorker* instance);\n"
              "/* New native status-bearing start. On BUSY, worker stays Idle. */\n"
              "bool infrared_worker_rx_try_start(InfraredWorker* instance);")

    old = """void infrared_worker_rx_start(InfraredWorker* instance) {
    furi_check(instance);
    furi_check(instance->state == InfraredWorkerStateIdle);

    furi_stream_set_trigger_level(instance->stream, sizeof(LevelDuration));

    furi_thread_set_callback(instance->thread, infrared_worker_rx_thread);
    furi_thread_start(instance->thread);

    furi_hal_infrared_async_rx_set_capture_isr_callback(infrared_worker_rx_callback, instance);
    furi_hal_infrared_async_rx_set_timeout_isr_callback(
        infrared_worker_rx_timeout_callback, instance);
    furi_hal_infrared_async_rx_start();
    furi_hal_infrared_async_rx_set_timeout(INFRARED_WORKER_RX_TIMEOUT);

    instance->rx.overrun = false;
    instance->state = InfraredWorkerStateRunRx;
}"""
    new = """/* E11 IR RX BUSY-aware worker rollback.
 * Start the receiver thread FIRST, because the native HAL ISR may
 * post flags immediately after successful TIM2 START.
 * On BUSY, no hardware or IRQ was changed; unwind only our worker
 * thread and callback pointers, leaving foreign TIM2 untouched.
 */
bool infrared_worker_rx_try_start(InfraredWorker* instance) {
    furi_check(instance);
    furi_check(instance->state == InfraredWorkerStateIdle);

    furi_stream_set_trigger_level(instance->stream, sizeof(LevelDuration));

    furi_thread_set_callback(instance->thread, infrared_worker_rx_thread);
    furi_thread_start(instance->thread);

    furi_hal_infrared_async_rx_set_capture_isr_callback(infrared_worker_rx_callback, instance);
    furi_hal_infrared_async_rx_set_timeout_isr_callback(
        infrared_worker_rx_timeout_callback, instance);
    if(!furi_hal_infrared_async_rx_try_start()) {
        furi_hal_infrared_async_rx_set_timeout_isr_callback(NULL, NULL);
        furi_hal_infrared_async_rx_set_capture_isr_callback(NULL, NULL);
        furi_thread_flags_set(furi_thread_get_id(instance->thread), INFRARED_WORKER_EXIT);
        furi_thread_join(instance->thread);
        furi_check(furi_stream_buffer_reset(instance->stream) == FuriStatusOk);
        return false;
    }
    furi_hal_infrared_async_rx_set_timeout(INFRARED_WORKER_RX_TIMEOUT);

    instance->rx.overrun = false;
    instance->state = InfraredWorkerStateRunRx;
    return true;
}

/* ABI compatibility for existing IR apps; internal users may check BUSY. */
void infrared_worker_rx_start(InfraredWorker* instance) {
    (void)infrared_worker_rx_try_start(instance);
}"""
    worker = once(worker, old, new)
    api = once(api, "Function,+,furi_hal_infrared_async_rx_start,void,\n",
               "Function,+,furi_hal_infrared_async_rx_start,void,\n"
               "Function,+,furi_hal_infrared_async_rx_try_start,_Bool,\n")
    api = once(api, "Function,+,infrared_worker_rx_start,void,InfraredWorker*\n",
               "Function,+,infrared_worker_rx_start,void,InfraredWorker*\n"
               "Function,+,infrared_worker_rx_try_start,_Bool,InfraredWorker*\n")
    return ir,h,worker,wh,api

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    root=args.firmware_root.resolve()
    try:
        sha=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PINNED:
            raise ValueError("Wrong pinned Momentum revision")
        names=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed native source refused")
            names.add(ln[3:])
        if names!=DIRTY:
            raise ValueError("Unexpected native source changes: "+repr(sorted(names^DIRTY)))
        paths=(IR,HEADER,WORKER,WORKER_H,API)
        bodies=[(root/p).read_text() for p in paths]
        changed=patch(*bodies)
        print("E11 RX TIM2/WORKER EXACT SOURCE STATUS/ROLLBACK CHECK PASS")
        if args.apply:
            for path,content in zip(paths,changed):
                (root/path).write_text(content)
            print("E11 RX NATIVE SOURCE PATCHED; NO DEVICE/USB/SD/FLASH")
        else:
            print("DRY RUN ONLY")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 native RX worker REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
