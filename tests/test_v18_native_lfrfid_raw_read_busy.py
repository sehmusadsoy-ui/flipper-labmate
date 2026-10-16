#!/usr/bin/env python3
"""Actual native LFRFID RAW START C fault injection and no-file-before-claim audit."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#define LFRFIDRawWorkerEventStop 0
#define FURI_BIT(flags,idx) ((flags)&(1U<<(idx)))
typedef struct {
 void* stream;
 void* pair;
} LFRFIDRawWorkerReadData;
typedef struct {
 void* events;
 float frequency,duty_cycle;
} LFRFIDRawWorker;
static int claims,captures,stops,resets,delays,writes;
static bool carrier_ok,capture_ok,clock_running,run_cancel;
static uint32_t stop_flag;
static uint32_t furi_event_flag_get(void* events) {
 assert(events==(void*)19);
 return stop_flag;
}
static void furi_delay_ms(unsigned ms) {
 assert(ms==100);
 delays++;
 if(run_cancel && delays==3) stop_flag=1;
}
static bool furi_hal_rfid_tim_read_try_start(float f,float duty) {
 assert(f==125000.0f && duty==0.5f);
 claims++;
 if(!carrier_ok) return false;
 clock_running=true;writes++;
 return true;
}
static void lfrfid_raw_worker_capture(bool lev,uint32_t dur,void* ctx) {
 (void)lev;(void)dur;(void)ctx;
}
static bool furi_hal_rfid_tim_read_capture_try_start(
 void(*cb)(bool,uint32_t,void*),void* ctx) {
 assert(cb==lfrfid_raw_worker_capture && ctx);
 captures++;
 if(!capture_ok) return false;
 assert(clock_running);
 writes++;return true;
}
static void furi_hal_rfid_tim_read_stop(void) {
 assert(clock_running);clock_running=false;stops++;writes++;
}
static void furi_hal_rfid_pins_reset(void) {
 assert(!clock_running);resets++;writes++;
}
static void reset(void) {
 claims=captures=stops=resets=delays=writes=0;
 carrier_ok=capture_ok=clock_running=run_cancel=false;
 stop_flag=0;
}
"""
RUN=r"""
int main(void) {
 LFRFIDRawWorker w={.events=(void*)19,.frequency=125000.0f,.duty_cycle=0.5f};
 LFRFIDRawWorkerReadData data={0};
 reset();stop_flag=1;
 assert(lfrfid_raw_e11_try_start(&w,&data)==LFRFIDRawE11Cancelled);
 assert(!claims&&!writes&&!delays&&!captures);
 reset();
 assert(lfrfid_raw_e11_try_start(&w,&data)==LFRFIDRawE11Busy);
 assert(claims==1&&!writes&&!delays&&!captures&&!stops&&!resets);
 reset();carrier_ok=true;run_cancel=true;
 assert(lfrfid_raw_e11_try_start(&w,&data)==LFRFIDRawE11Cancelled);
 assert(claims==1 && captures==0 && delays==3 && stops==1 && resets==1 &&
        !clock_running);
 reset();carrier_ok=true;
 assert(lfrfid_raw_e11_try_start(&w,&data)==LFRFIDRawE11Busy);
 assert(delays==15 && captures==1 && stops==1 && resets==1 && !clock_running);
 reset();carrier_ok=capture_ok=true;
 assert(lfrfid_raw_e11_try_start(&w,&data)==LFRFIDRawE11Started);
 assert(delays==15 && captures==1 && stops==0 && resets==0 && clock_running);
 puts("E11 native RAW RFID worker real C PASS: STOP/BUSY/no-unowned-STOP");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    a=p.parse_args();root=a.root.resolve()
    raw=(root/"lib/lfrfid/lfrfid_raw_worker.c").read_text()
    hdr=(root/"lib/lfrfid/lfrfid_worker.h").read_text()
    assert "LFRFIDWorkerReadRawBusy" in hdr
    assert "/* E11 native LFRFID RAW read BUSY-safe START. */" in raw
    start=raw.index("/* E11 native LFRFID RAW read BUSY-safe START. */")
    end=raw.index("static int32_t lfrfid_raw_read_worker_thread(void* thread_context) {",start)
    helper=raw[start:end]
    body=raw[end:raw.index("static void rfid_emulate_dma_isr(",end)]
    assert body.index("lfrfid_raw_e11_try_start(worker, data)") < body.index(
        "lfrfid_raw_file_open_write(file, filename)")
    assert body.index("if(start != LFRFIDRawE11Started)") < body.index(
        "furi_record_open(RECORD_STORAGE)")
    assert "worker->read_callback(LFRFIDWorkerReadRawBusy" in body
    assert "furi_hal_rfid_tim_read_start(" not in body
    assert "furi_hal_rfid_tim_read_capture_start(" not in body
    assert body.count("furi_hal_rfid_tim_read_capture_stop();")==1
    assert body.count("furi_hal_rfid_tim_read_stop();")==1
    assert "if(start == LFRFIDRawE11Busy)" in body
    with tempfile.TemporaryDirectory(prefix="e11_rfid_raw_busy_") as t:
        tmp=Path(t);src=tmp/"raw.c";exe=tmp/"raw"
        src.write_text(STUB+"\n"+helper+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 RAW RFID native START C host PASS. Other RFID modes/physical gate OPEN.")

if __name__=="__main__":
    main()
