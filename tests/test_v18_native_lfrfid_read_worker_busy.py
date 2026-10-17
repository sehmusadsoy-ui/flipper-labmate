#!/usr/bin/env python3
"""Actual pinned native LFRFID read worker C helper fault injection (NO DEVICE).

Compiles extracted production helper bodies, not a reimplementation.
Full native worker compilation is a separate matched-firmware CI gate.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB = r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#define LFRFIDFeatureASK 1U
#define LFRFIDFeaturePSK 2U
typedef unsigned LFRFIDFeature;
typedef struct { void* stream; void* pair; bool ignore_next_pulse; } LFRFIDWorkerReadContext;
static int carrier_starts,capture_starts,carrier_stops,pin_resets,capture_stops,writes;
static bool carrier_ok,capture_ok,carrier_owned,capture_owned;
static float chosen_freq,chosen_duty;
bool furi_hal_rfid_tim_read_try_start(float freq,float duty) {
 carrier_starts++;chosen_freq=freq;chosen_duty=duty;
 if(!carrier_ok) return false;
 assert(!carrier_owned);carrier_owned=true;writes++;
 return true;
}
static void lfrfid_worker_read_capture(bool level,uint32_t duration,void* context) {
 (void)level;(void)duration;(void)context;
}
bool furi_hal_rfid_tim_read_capture_try_start(
 void(*callback)(bool,uint32_t,void*),void* context) {
 assert(callback==lfrfid_worker_read_capture && context);
 capture_starts++;
 if(!capture_ok) return false;
 assert(carrier_owned && !capture_owned);capture_owned=true;writes++;
 return true;
}
void furi_hal_rfid_tim_read_stop(void) {
 assert(carrier_owned);carrier_stops++;carrier_owned=false;writes++;
}
void furi_hal_rfid_pins_reset(void) {
 assert(!carrier_owned);pin_resets++;writes++;
}
static void reset(void) {
 carrier_starts=capture_starts=carrier_stops=pin_resets=capture_stops=writes=0;
 carrier_owned=capture_owned=false;carrier_ok=capture_ok=false;
 chosen_freq=chosen_duty=0.0f;
}
"""
RUN = r"""
int main(void) {
 LFRFIDWorkerReadContext ctx={0};
 reset();
 assert(!lfrfid_worker_e11_try_carrier(LFRFIDFeatureASK));
 assert(!writes && carrier_starts==1 && capture_starts==0 && !pin_resets);
 reset();
 assert(!lfrfid_worker_e11_try_carrier(LFRFIDFeaturePSK));
 assert(chosen_freq==62500.0f && chosen_duty==0.25f && !writes);
 reset();carrier_ok=true;
 assert(lfrfid_worker_e11_try_carrier(LFRFIDFeatureASK));
 assert(chosen_freq==125000.0f && chosen_duty==0.5f);
 assert(!lfrfid_worker_e11_try_capture(&ctx));
 assert(!carrier_owned && !capture_owned && carrier_stops==1 &&
        pin_resets==1 && capture_starts==1 && writes==3);
 reset();carrier_ok=capture_ok=true;
 assert(lfrfid_worker_e11_try_carrier(LFRFIDFeaturePSK));
 assert(lfrfid_worker_e11_try_capture(&ctx));
 assert(carrier_owned && capture_owned && carrier_stops==0 && pin_resets==0);
 puts("E11 native LFRFID read worker actual-C helpers: carrier/capture BUSY rollback PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    a=p.parse_args()
    root=a.root.resolve()
    worker=(root/"lib/lfrfid/lfrfid_worker_modes.c").read_text(encoding="utf-8")
    rfid=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text(encoding="utf-8")
    assert "/* E11 native RFID read TIM1 owner. */" in rfid
    assert "/* E11 native RFID capture TIM2 owner. */" in rfid
    assert "/* E11 native LFRFID read worker BUSY-safe lifecycle. */" in worker
    helpers=worker[worker.index("typedef enum {\n    LFRFIDWorkerReadOK,"):
                   worker.index("static LFRFIDWorkerReadState lfrfid_worker_read_internal(")]
    # Audit original worker integration as a negative safety condition.
    read=worker[worker.index("static LFRFIDWorkerReadState lfrfid_worker_read_internal("):
                worker.index("static void lfrfid_worker_mode_read_process(")]
    process=worker[worker.index("static void lfrfid_worker_mode_read_process("):
                   worker.index("/********************************",worker.index("static void lfrfid_worker_mode_read_process("))]
    assert "furi_hal_rfid_tim_read_start(" not in read
    assert "furi_hal_rfid_tim_read_capture_start(" not in read
    assert read.index("if(!lfrfid_worker_e11_try_carrier(feature))") < read.index(
        "lfrfid_worker_delay(worker, LFRFID_WORKER_READ_STABILIZE_TIME_MS)")
    assert read.index("if(!lfrfid_worker_e11_try_capture(&ctx))") < read.index(
        "worker->read_cb(LFRFIDWorkerReadStartASK,")
    assert read.index("if(!lfrfid_worker_e11_try_capture(&ctx))") < read.index(
        "worker->read_cb(LFRFIDWorkerReadStartPSK,")
    assert "varint_pair_free(ctx.pair);" in read and "buffer_stream_free(ctx.stream);" in read
    assert "if(lfrfid_worker_check_for_stop(worker))" in read
    assert process.count("state == LFRFIDWorkerReadBusy") >= 2
    if "LFRFIDWorkerReadHardwareBusy" in worker:
        assert "worker->read_cb(LFRFIDWorkerReadHardwareBusy, PROTOCOL_NO, worker->cb_ctx);" in process
    assert "LFRFIDWorkerReadBusy, /* E11:" in helpers
    with tempfile.TemporaryDirectory(prefix="e11_lfrfid_read_busy_") as t:
        tmp=Path(t);src=tmp/"read_worker.c";exe=tmp/"read_worker"
        src.write_text(STUB+"\n"+helpers+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("LFRFID genuine worker helper C host PASS; full firmware build + raw recording PENDING")

if __name__=="__main__":
    main()
