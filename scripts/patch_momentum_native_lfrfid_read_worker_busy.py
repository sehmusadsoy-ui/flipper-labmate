#!/usr/bin/env python3
"""E11 pinned LF RFID normal READ worker BUSY-aware lifecycle (NO FLASH).

Requires reviewed native RFID carrier TIM1 + capture TIM2 owner stages.
Intentionally does not touch raw file recording, DMA emulation or field mode.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
WORKER="lib/lfrfid/lfrfid_worker_modes.c"
MARK="/* E11 native LFRFID read worker BUSY-safe lifecycle. */"
EXPECTED={
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
    "lib/infrared/worker/infrared_worker.h",
    "targets/f7/furi_hal/furi_hal_rfid.c",
    "targets/f7/furi_hal/furi_hal_rfid.h",
}

def once(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("Unexpected pinned LFRFID worker anchor "+repr(old[:110]))
    return s.replace(old,new,1)

def patch(source:str)->str:
    if MARK in source:
        raise ValueError("LFRFID read worker already patched")
    source=once(source,
        """typedef enum {
    LFRFIDWorkerReadOK,
    LFRFIDWorkerReadExit,
    LFRFIDWorkerReadTimeout,
} LFRFIDWorkerReadState;

static LFRFIDWorkerReadState lfrfid_worker_read_internal(""",
        """typedef enum {
    LFRFIDWorkerReadOK,
    LFRFIDWorkerReadExit,
    LFRFIDWorkerReadTimeout,
    LFRFIDWorkerReadBusy, /* E11: never confuse unavailable timers with timeout. */
} LFRFIDWorkerReadState;

/* E11 native LFRFID read worker BUSY-safe lifecycle. */
static bool lfrfid_worker_e11_try_carrier(LFRFIDFeature feature) {
    if(feature & LFRFIDFeatureASK) {
        return furi_hal_rfid_tim_read_try_start(125000, 0.5);
    }
    return furi_hal_rfid_tim_read_try_start(62500, 0.25);
}

static bool lfrfid_worker_e11_try_capture(LFRFIDWorkerReadContext* ctx) {
    if(furi_hal_rfid_tim_read_capture_try_start(lfrfid_worker_read_capture, ctx)) {
        return true;
    }
    /* Only our successful carrier START may be unwound here.
       A foreign TIM2/IRQ/capture callback must remain untouched. */
    furi_hal_rfid_tim_read_stop();
    furi_hal_rfid_pins_reset();
    return false;
}

static LFRFIDWorkerReadState lfrfid_worker_read_internal(""")
    source=once(source,
        """    if(feature & LFRFIDFeatureASK) {
        furi_hal_rfid_tim_read_start(125000, 0.5);
        FURI_LOG_D(TAG, "Start ASK");
        if(worker->read_cb) {
            worker->read_cb(LFRFIDWorkerReadStartASK, PROTOCOL_NO, worker->cb_ctx);
        }
    } else {
        furi_hal_rfid_tim_read_start(62500, 0.25);
        FURI_LOG_D(TAG, "Start PSK");
        if(worker->read_cb) {
            worker->read_cb(LFRFIDWorkerReadStartPSK, PROTOCOL_NO, worker->cb_ctx);
        }
    }

    // stabilize detector
    lfrfid_worker_delay(worker, LFRFID_WORKER_READ_STABILIZE_TIME_MS);

    protocol_dict_decoders_start(worker->protocols);""",
        """    if(!lfrfid_worker_e11_try_carrier(feature)) {
        FURI_LOG_W(TAG, "RFID carrier TIM1 BUSY");
        return LFRFIDWorkerReadBusy;
    }

    // Original stabilization remains before capture, but STOP must not
    // start a new capture after cancellation while stabilizing.
    lfrfid_worker_delay(worker, LFRFID_WORKER_READ_STABILIZE_TIME_MS);
    if(lfrfid_worker_check_for_stop(worker)) {
        furi_hal_rfid_tim_read_stop();
        furi_hal_rfid_pins_reset();
        return LFRFIDWorkerReadExit;
    }

    protocol_dict_decoders_start(worker->protocols);""")
    source=once(source,
        """    furi_hal_rfid_tim_read_capture_start(lfrfid_worker_read_capture, &ctx);

    *result_protocol = PROTOCOL_NO;""",
        """    if(!lfrfid_worker_e11_try_capture(&ctx)) {
        FURI_LOG_W(TAG, "RFID capture TIM2 BUSY");
        varint_pair_free(ctx.pair);
        buffer_stream_free(ctx.stream);
#ifdef LFRFID_WORKER_READ_DEBUG_GPIO
        furi_hal_gpio_write(LFRFID_WORKER_READ_DEBUG_GPIO_VALUE, false);
        furi_hal_gpio_write(LFRFID_WORKER_READ_DEBUG_GPIO_LOAD, false);
        furi_hal_gpio_init_simple(LFRFID_WORKER_READ_DEBUG_GPIO_VALUE, GpioModeAnalog);
        furi_hal_gpio_init_simple(LFRFID_WORKER_READ_DEBUG_GPIO_LOAD, GpioModeAnalog);
#endif
        return LFRFIDWorkerReadBusy;
    }

    /* Report a read START only after BOTH native timers actually started. */
    if(feature & LFRFIDFeatureASK) {
        FURI_LOG_D(TAG, "Start ASK");
        if(worker->read_cb) {
            worker->read_cb(LFRFIDWorkerReadStartASK, PROTOCOL_NO, worker->cb_ctx);
        }
    } else {
        FURI_LOG_D(TAG, "Start PSK");
        if(worker->read_cb) {
            worker->read_cb(LFRFIDWorkerReadStartPSK, PROTOCOL_NO, worker->cb_ctx);
        }
    }

    *result_protocol = PROTOCOL_NO;""")
    x="if(state == LFRFIDWorkerReadOK || state == LFRFIDWorkerReadExit) {"
    if source.count(x)!=2:
        raise ValueError("Unexpected number of ASK/PSK retry loops")
    source=source.replace(x,
        "if(state == LFRFIDWorkerReadOK || state == LFRFIDWorkerReadExit ||\n"
        "               state == LFRFIDWorkerReadBusy) {")
    return source

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                    text=True).strip()
        if sha!=PIN:
            raise ValueError("Unpinned Momentum checkout")
        changed=set()
        for ln in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],
                                           text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed native source")
            changed.add(ln[3:])
        if changed!=EXPECTED:
            raise ValueError("Unexpected native source edits "+repr(sorted(changed^EXPECTED)))
        rfid=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text(encoding="utf-8")
        if "/* E11 native RFID read TIM1 owner. */" not in rfid or (
            "/* E11 native RFID capture TIM2 owner. */" not in rfid):
            raise ValueError("Native READ+CAPTURE owners not installed")
        before=(root/WORKER).read_text(encoding="utf-8")
        after=patch(before)
        print("E11 NATIVE RFID NORMAL READ WORKER SOURCE PREFLIGHT PASS")
        if a.apply:
            (root/WORKER).write_text(after,encoding="utf-8")
            print("WORKER SOURCE ONLY — NO FLASH, RAW/EMULATE/FIELD UNCHANGED")
        else:
            print("READ-ONLY SOURCE PREFLIGHT")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 NATIVE RFID WORKER REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
