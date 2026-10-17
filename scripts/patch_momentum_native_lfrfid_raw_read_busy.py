#!/usr/bin/env python3
"""E11 pinned LF RFID RAW RECORD worker BUSY-safe START / no bogus file (NO FLASH).

This does not touch RFID DMA emulation or field detection.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
RAW="lib/lfrfid/lfrfid_raw_worker.c"
HEADER="lib/lfrfid/lfrfid_worker.h"
MARK="/* E11 native LFRFID RAW read BUSY-safe START. */"
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
    "lib/lfrfid/lfrfid_worker_modes.c",
}

def once(text:str,old:str,new:str)->str:
    if text.count(old)!=1:
        raise ValueError("Pinned RAW worker anchor missing/ambiguous "+repr(old[:115]))
    return text.replace(old,new,1)

def patch(raw:str,header:str):
    if MARK in raw or "LFRFIDWorkerReadRawBusy" in header:
        raise ValueError("RAW read worker already patched")
    header=once(header,
        """typedef enum {
    LFRFIDWorkerReadRawFileError,
    LFRFIDWorkerReadRawOverrun,
} LFRFIDWorkerReadRawResult;""",
        """typedef enum {
    LFRFIDWorkerReadRawFileError,
    LFRFIDWorkerReadRawOverrun,
    LFRFIDWorkerReadRawBusy, /* E11: timer is owned; not a storage failure. */
} LFRFIDWorkerReadRawResult;""")
    needle="""static int32_t lfrfid_raw_read_worker_thread(void* thread_context) {
    LFRFIDRawWorker* worker = (LFRFIDRawWorker*)thread_context;"""
    insert="""/* E11 native LFRFID RAW read BUSY-safe START. */
typedef enum {
    LFRFIDRawE11Started,
    LFRFIDRawE11Busy,
    LFRFIDRawE11Cancelled,
} LFRFIDRawE11Start;

static LFRFIDRawE11Start lfrfid_raw_e11_try_start(
    LFRFIDRawWorker* worker, LFRFIDRawWorkerReadData* data) {
    if(FURI_BIT(furi_event_flag_get(worker->events), LFRFIDRawWorkerEventStop)) {
        return LFRFIDRawE11Cancelled;
    }
    if(!furi_hal_rfid_tim_read_try_start(worker->frequency, worker->duty_cycle)) {
        return LFRFIDRawE11Busy;
    }
    /* Keep the original 1500 ms stabilization but honor STOP every 100ms. */
    for(uint8_t i = 0; i < 15; ++i) {
        if(FURI_BIT(furi_event_flag_get(worker->events), LFRFIDRawWorkerEventStop)) {
            furi_hal_rfid_tim_read_stop();
            furi_hal_rfid_pins_reset();
            return LFRFIDRawE11Cancelled;
        }
        furi_delay_ms(100);
    }
    if(!furi_hal_rfid_tim_read_capture_try_start(lfrfid_raw_worker_capture, data)) {
        furi_hal_rfid_tim_read_stop();
        furi_hal_rfid_pins_reset();
        return LFRFIDRawE11Busy;
    }
    return LFRFIDRawE11Started;
}

static int32_t lfrfid_raw_read_worker_thread(void* thread_context) {
    LFRFIDRawWorker* worker = (LFRFIDRawWorker*)thread_context;"""
    raw=once(raw,needle,insert)
    raw=once(raw,
        """    Storage* storage = furi_record_open(RECORD_STORAGE);
    LFRFIDRawFile* file = lfrfid_raw_file_alloc(storage);
    const char* filename = furi_string_get_cstr(worker->file_path);
    bool file_valid = lfrfid_raw_file_open_write(file, filename);

    LFRFIDRawWorkerReadData* data = malloc(sizeof(LFRFIDRawWorkerReadData));

    data->stream = buffer_stream_alloc(RFID_DATA_BUFFER_SIZE, READ_DATA_BUFFER_COUNT);
    data->pair = varint_pair_alloc();

    if(file_valid) {""",
        """    LFRFIDRawWorkerReadData* data = malloc(sizeof(LFRFIDRawWorkerReadData));
    data->stream = buffer_stream_alloc(RFID_DATA_BUFFER_SIZE, READ_DATA_BUFFER_COUNT);
    data->pair = varint_pair_alloc();

    /* Never create or truncate a raw recording before BOTH timers start. */
    const LFRFIDRawE11Start start = lfrfid_raw_e11_try_start(worker, data);
    if(start != LFRFIDRawE11Started) {
        if(start == LFRFIDRawE11Busy) {
            FURI_LOG_W(TAG_EMULATE, "RFID RAW carrier/capture BUSY");
            if(worker->read_callback) {
                worker->read_callback(LFRFIDWorkerReadRawBusy, worker->context);
            }
        }
        varint_pair_free(data->pair);
        buffer_stream_free(data->stream);
        free(data);
        return 0;
    }

    Storage* storage = furi_record_open(RECORD_STORAGE);
    LFRFIDRawFile* file = lfrfid_raw_file_alloc(storage);
    const char* filename = furi_string_get_cstr(worker->file_path);
    bool file_valid = lfrfid_raw_file_open_write(file, filename);

    if(file_valid) {""")
    raw=once(raw,
        """    if(file_valid) {
        // setup carrier
        furi_hal_rfid_tim_read_start(worker->frequency, worker->duty_cycle);

        // stabilize detector
        furi_delay_ms(1500);

        // start capture
        furi_hal_rfid_tim_read_capture_start(lfrfid_raw_worker_capture, data);

        while(1) {""",
        """    if(file_valid) {
        /* Carrier and capture are already owned; process original stream. */
        while(1) {""")
    raw=once(raw,
        """        furi_hal_rfid_tim_read_capture_stop();
        furi_hal_rfid_tim_read_stop();
    } else {
        if(worker->read_callback != NULL) {
            // message file_error to worker
            worker->read_callback(LFRFIDWorkerReadRawFileError, worker->context);
        }
    }

    if(!file_valid) {""",
        """    } else {
        if(worker->read_callback != NULL) {
            // Genuine storage error, not native resource BUSY.
            worker->read_callback(LFRFIDWorkerReadRawFileError, worker->context);
        }
    }

    /* Release exactly the two resources acquired before opening the file.
       No late cleanup can run after a denied hardware START. */
    furi_hal_rfid_tim_read_capture_stop();
    furi_hal_rfid_tim_read_stop();

    if(!file_valid) {""")
    return raw,header

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args();root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                     text=True).strip()
        if head!=PIN:
            raise ValueError("Unpinned Momentum revision")
        changed=set()
        for ln in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],
                                           text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed native source")
            changed.add(ln[3:])
        if changed!=EXPECTED:
            raise ValueError("Unexpected native changes "+repr(sorted(changed^EXPECTED)))
        rfid=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text(encoding="utf-8")
        modes=(root/"lib/lfrfid/lfrfid_worker_modes.c").read_text(encoding="utf-8")
        if "/* E11 native RFID capture TIM2 owner. */" not in rfid or (
            "/* E11 native LFRFID read worker BUSY-safe lifecycle. */" not in modes):
            raise ValueError("Required native owners and READ worker missing")
        old=((root/RAW).read_text(encoding="utf-8"),
             (root/HEADER).read_text(encoding="utf-8"))
        result=patch(*old)
        print("E11 NATIVE LFRFID RAW START SOURCE PREFLIGHT PASS")
        if args.apply:
            for name,value in zip((RAW,HEADER),result):
                (root/name).write_text(value,encoding="utf-8")
            print("RAW START SOURCE ONLY; NO SD/DEVICE/FLASH; DMA/FIELD OPEN")
        else:
            print("READ-ONLY RAW WORKER SOURCE PREFLIGHT")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as ex:
        print("E11 NATIVE RFID RAW START REFUSED: "+str(ex),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
