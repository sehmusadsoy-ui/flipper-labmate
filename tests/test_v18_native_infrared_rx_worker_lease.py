#!/usr/bin/env python3
"""E11: run actual native infrared RX worker BUSY/STOP C on mocked services.

Compiles exact pinned patched production worker source (not a rewritten
algorithm). Verifies denied TIM2 START unwinds the waiting RX worker,
and successful receiver STOP touches only its owned HAL timer.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#define INFRARED_WORKER_RX_TIMEOUT 145UL
#define INFRARED_WORKER_EXIT 0x08
#define FuriStatusOk 0
#define furi_check(c) assert(c)
typedef int FuriStatus;
typedef uint32_t LevelDuration;
typedef struct {uint32_t id;} FuriThread;
typedef struct {uint32_t id;} FuriStreamBuffer;
typedef enum {InfraredWorkerStateIdle,InfraredWorkerStateRunRx} InfraredWorkerState;
typedef struct InfraredWorker {
    FuriThread* thread;
    FuriStreamBuffer* stream;
    InfraredWorkerState state;
    struct {bool overrun;} rx;
} InfraredWorker;
static FuriThread g_thread={7};
static FuriStreamBuffer g_stream={8};
static int started, joined, flags, callbacks, resets, timer_starts;
static int timeout_calls,hal_stops;
static bool lease_available;
static void infrared_worker_rx_callback(void* ctx,bool level,uint32_t duration) {
    (void)ctx;(void)level;(void)duration;
}
static void infrared_worker_rx_timeout_callback(void* ctx) {(void)ctx;}
static int32_t infrared_worker_rx_thread(void* ctx) {(void)ctx;return 0;}
void furi_stream_set_trigger_level(FuriStreamBuffer* b,size_t n) {
    assert(b==&g_stream && n==sizeof(LevelDuration));
}
void furi_thread_set_callback(FuriThread* t,int32_t (*callback)(void*)) {
    assert(t==&g_thread && callback==infrared_worker_rx_thread);
}
void furi_thread_start(FuriThread* t) {assert(t==&g_thread);started++;}
uint32_t furi_thread_get_id(FuriThread* t){assert(t==&g_thread);return t->id;}
uint32_t furi_thread_flags_set(uint32_t id,uint32_t flag) {
    assert(id==7 && flag==INFRARED_WORKER_EXIT);
    flags++;return flag;
}
void furi_thread_join(FuriThread* t) {assert(t==&g_thread);joined++;}
FuriStatus furi_stream_buffer_reset(FuriStreamBuffer* b) {
    assert(b==&g_stream);resets++;return FuriStatusOk;
}
void furi_hal_infrared_async_rx_set_capture_isr_callback(
    void (*callback)(void*,bool,uint32_t),void* context) {
    if(callback)assert(callback==infrared_worker_rx_callback && context);
    else assert(context==NULL);
    callbacks++;
}
void furi_hal_infrared_async_rx_set_timeout_isr_callback(
    void (*callback)(void*),void* context) {
    if(callback)assert(callback==infrared_worker_rx_timeout_callback && context);
    else assert(context==NULL);
    callbacks++;
}
bool furi_hal_infrared_async_rx_try_start(void) {
    timer_starts++;
    return lease_available;
}
void furi_hal_infrared_async_rx_start(void) {
    (void)furi_hal_infrared_async_rx_try_start();
}
void furi_hal_infrared_async_rx_set_timeout(uint32_t t) {
    assert(t==INFRARED_WORKER_RX_TIMEOUT && lease_available);timeout_calls++;
}
void furi_hal_infrared_async_rx_stop(void) {
    assert(lease_available);hal_stops++;
}
"""
RUN=r"""
int main(void) {
    InfraredWorker w={.thread=&g_thread,.stream=&g_stream,.state=InfraredWorkerStateIdle};
    /* Lease denial: one worker start must be paired with EXIT/join,
     * both callbacks cleared, no timeout or foreign TIM2 STOP.
     */
    assert(!infrared_worker_rx_try_start(&w));
    assert(w.state==InfraredWorkerStateIdle && started==1 && joined==1);
    assert(callbacks==4 && flags==1 && resets==1);
    assert(timeout_calls==0 && hal_stops==0 && timer_starts==1);
    /* Legacy void API must also unwind on BUSY. */
    infrared_worker_rx_start(&w);
    assert(w.state==InfraredWorkerStateIdle && started==2 && joined==2);
    assert(callbacks==8 && flags==2 && resets==2 && !hal_stops);
    /* Actual owned RX allows capture/timeout and STOP. */
    lease_available=true;
    assert(infrared_worker_rx_try_start(&w));
    assert(w.state==InfraredWorkerStateRunRx);
    assert(started==3 && joined==2 && callbacks==10);
    assert(timeout_calls==1 && timer_starts==3);
    infrared_worker_rx_stop(&w);
    assert(w.state==InfraredWorkerStateIdle);
    assert(joined==3 && flags==3 && resets==3);
    assert(callbacks==12 && hal_stops==1);
    printf("E11 real native infrared RX worker C: BUSY unwind and owned STOP PASS\n");
    return 0;
}
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    root=args.momentum_root.resolve()
    worker=(root/"lib/infrared/worker/infrared_worker.c").read_text()
    hdr=(root/"lib/infrared/worker/infrared_worker.h").read_text()
    ir=(root/"targets/f7/furi_hal/furi_hal_infrared.c").read_text()
    public=(root/"targets/furi_hal_include/furi_hal_infrared.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "E11 IR RX BUSY-aware worker rollback" in worker
    assert "bool infrared_worker_rx_try_start(InfraredWorker* instance)" in hdr
    assert "bool furi_hal_infrared_async_rx_try_start(void)" in public
    assert "bool furi_hal_infrared_async_rx_try_start(void) {" in ir
    assert "Function,+,infrared_worker_rx_try_start,_Bool,InfraredWorker*" in api
    assert "Function,+,furi_hal_infrared_async_rx_try_start,_Bool," in api
    p=worker.index("bool infrared_worker_rx_try_start(")
    e=worker.index("\nbool infrared_worker_signal_is_decoded(",p)
    actual=worker[p:e]
    assert actual.index("furi_thread_start(instance->thread);") < actual.index(
        "furi_hal_infrared_async_rx_try_start()")
    assert actual.index("furi_thread_join(instance->thread);") < actual.index(
        "return false;")
    assert actual.index("furi_hal_infrared_async_rx_try_start()") < actual.index(
        "furi_hal_infrared_async_rx_set_timeout(INFRARED_WORKER_RX_TIMEOUT)")
    assert "furi_hal_infrared_async_rx_stop();" in actual
    with tempfile.TemporaryDirectory(prefix="labmate_ir_rx_worker_") as td:
        f=Path(td)/"run.c"
        f.write_text(STUB+"\n"+actual+"\n"+RUN)
        exe=Path(td)/"run"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-O0",str(f),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 RX actual worker C + status APIs PASS; no hardware used")

if __name__=="__main__":
    main()
