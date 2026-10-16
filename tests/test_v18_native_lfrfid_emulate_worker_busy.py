#!/usr/bin/env python3
"""Genuine pinned LF RFID normal/RAW emulation worker C helpers and scene audit.

No physical RF, emulator DMA or Flipper SD is used.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#define LFRFID_WORKER_EMULATE_BUFFER_SIZE 1024
#define EMULATE_BUFFER_SIZE 1024
typedef void (*FuriHalRfidDMACallback)(bool,void*);
typedef struct {int marker;} FuriStreamBuffer;
typedef struct {
 uint32_t duration[LFRFID_WORKER_EMULATE_BUFFER_SIZE];
 uint32_t pulse[LFRFID_WORKER_EMULATE_BUFFER_SIZE];
} LFRFIDWorkerEmulateBuffer;
typedef struct {size_t overrun_count;FuriStreamBuffer* stream;} RfidEmulateCtx;
typedef struct {
 uint32_t emulate_buffer_arr[EMULATE_BUFFER_SIZE];
 uint32_t emulate_buffer_ccr[EMULATE_BUFFER_SIZE];
 RfidEmulateCtx ctx;
} LFRFIDRawWorkerEmulateData;
static bool allow_start;
static int tries,writes,callbacks;
static FuriHalRfidDMACallback registered;
static void* registered_ctx;
static bool furi_hal_rfid_tim_emulate_dma_try_start(
 uint32_t* duration,uint32_t* pulse,size_t count,
 FuriHalRfidDMACallback cb,void* context) {
 assert(duration && pulse && count==1024 && cb && context);
 tries++;if(!allow_start)return false;
 writes++;registered=cb;registered_ctx=context;
 return true;
}
static void lfrfid_worker_emulate_dma_isr(bool half,void* context){
 (void)half;(void)context;callbacks++;
}
static void rfid_emulate_dma_isr(bool half,void* context){
 (void)half;(void)context;callbacks++;
}
"""
RUN=r"""
int main(void) {
 LFRFIDWorkerEmulateBuffer normal={0};
 FuriStreamBuffer stream={0};
 LFRFIDRawWorkerEmulateData raw={0};
 raw.ctx.stream=&stream;
 allow_start=false;
 assert(!lfrfid_worker_e11_try_emulate(&normal,&stream));
 assert(!lfrfid_raw_e11_try_emulate(&raw));
 assert(tries==2 && !writes && !registered);
 allow_start=true;
 assert(lfrfid_worker_e11_try_emulate(&normal,&stream));
 assert(registered==lfrfid_worker_emulate_dma_isr && registered_ctx==&stream);
 assert(lfrfid_raw_e11_try_emulate(&raw));
 assert(registered==rfid_emulate_dma_isr && registered_ctx==&raw.ctx);
 assert(tries==4 && writes==2);
 puts("E11 real LF RFID normal/RAW emulation helper C BUSY/START PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    modes=(root/"lib/lfrfid/lfrfid_worker_modes.c").read_text()
    raw=(root/"lib/lfrfid/lfrfid_raw_worker.c").read_text()
    header=(root/"lib/lfrfid/lfrfid_worker.h").read_text()
    scene=(root/"applications/main/lfrfid/scenes/lfrfid_scene_raw_emulate.c").read_text()
    original_rfid=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text()
    assert "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" in original_rfid
    mark="/* E11 native LFRFID EMULATE bool BUSY worker. */"
    n=modes[modes.index(mark):
            modes.index("static void lfrfid_worker_mode_emulate_process(")]
    r=raw[raw.index("/* E11 native RAW emulator:"):
          raw.index("static int32_t lfrfid_raw_emulate_worker_thread(void* thread_context) {",
                    raw.index("/* E11 native RAW emulator:"))]
    normal=modes[modes.index("static void lfrfid_worker_mode_emulate_process("):
                 modes.index("/********************************",modes.index("static void lfrfid_worker_mode_emulate_process("))]
    recorder=raw[raw.index("static int32_t lfrfid_raw_emulate_worker_thread(void* thread_context) {"):
                 raw.rindex("return 0;")+len("return 0;")]
    assert "furi_hal_rfid_tim_emulate_dma_start(" not in normal
    assert "furi_hal_rfid_tim_emulate_dma_start(" not in recorder
    assert normal.index("if(!lfrfid_worker_e11_try_emulate(buffer, stream))") < normal.index("while(true)")
    assert normal.index("if(!lfrfid_worker_e11_try_emulate(buffer, stream))") < normal.index(
        "furi_hal_gpio_init_simple(LFRFID_WORKER_READ_DEBUG_GPIO_LOAD, GpioModeOutputPushPull)")
    assert "free(buffer);" in normal and "pulse_glue_free(pulse_glue);" in normal
    assert recorder.index("if(file_valid &&") < recorder.index("lfrfid_raw_e11_try_emulate(data)")
    assert "if(file_valid && e11_started)" in recorder
    assert "if(e11_started) furi_hal_rfid_tim_emulate_dma_stop();" in recorder
    assert "LFRFIDWorkerEmulateRawBusy" in header
    assert "LFRFIDWorkerEmulateRawBusy" in scene
    assert "LfRfidEventReadBusy" in scene
    assert 'popup_set_header(popup, "RFID BUSY"' in scene
    with tempfile.TemporaryDirectory(prefix="e11_lfrfid_emulate_") as d:
        td=Path(d);src=td/"worker.c";exe=td/"worker"
        src.write_text(STUB+"\n"+n+"\n"+r+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 REAL NORMAL/RAW EMULATION C helpers + BUSY worker/scene audit PASS")
    print("Exact native complete firmware CI and device RF still separate.")

if __name__=="__main__":
    main()
