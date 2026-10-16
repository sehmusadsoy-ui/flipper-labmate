#!/usr/bin/env python3
"""E11 native LF RFID emulation worker bool BUSY path on pinned Momentum.

Includes normal protocol, RAW file worker and RAW scene BUSY warning.
The NFC/iButton pin utility and RFID field mode remain separate E11 gates.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_rfid_emulate_dma_lease import EXPECTED as DMA_DIRTY

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
MODES="lib/lfrfid/lfrfid_worker_modes.c"
RAW="lib/lfrfid/lfrfid_raw_worker.c"
HEADER="lib/lfrfid/lfrfid_worker.h"
SCENE="applications/main/lfrfid/scenes/lfrfid_scene_raw_emulate.c"
EXPECTED=DMA_DIRTY
MARK="/* E11 native LFRFID EMULATE bool BUSY worker. */"

def once(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("Pinned emulation worker anchor missing/ambiguous "+repr(old[:110]))
    return s.replace(old,new,1)

def patch(modes:str,raw:str,header:str,scene:str):
    if MARK in modes:
        raise ValueError("Native LF RFID emulation worker already patched")
    modes=once(modes,
        """static void lfrfid_worker_mode_emulate_process(LFRFIDWorker* worker) {""",
        """/* E11 native LFRFID EMULATE bool BUSY worker. */
static bool lfrfid_worker_e11_try_emulate(
    LFRFIDWorkerEmulateBuffer* buffer, FuriStreamBuffer* stream) {
    return furi_hal_rfid_tim_emulate_dma_try_start(
        buffer->duration, buffer->pulse, LFRFID_WORKER_EMULATE_BUFFER_SIZE,
        lfrfid_worker_emulate_dma_isr, stream);
}

static void lfrfid_worker_mode_emulate_process(LFRFIDWorker* worker) {""")
    modes=once(modes,
        """#ifdef LFRFID_WORKER_READ_DEBUG_GPIO
    furi_hal_gpio_init_simple(LFRFID_WORKER_READ_DEBUG_GPIO_LOAD, GpioModeOutputPushPull);
#endif

    furi_hal_rfid_tim_emulate_dma_start(
        buffer->duration,
        buffer->pulse,
        LFRFID_WORKER_EMULATE_BUFFER_SIZE,
        lfrfid_worker_emulate_dma_isr,
        stream);

    while(true) {""",
        """    /* The old void START silently continued on TIM2 or DMA2 BUSY.
     * Do not enter the DMA event loop or STOP unless START succeeded.
     */
    if(!lfrfid_worker_e11_try_emulate(buffer, stream)) {
        FURI_LOG_W(TAG, "Native RFID emulation TIM2/DMA2 BUSY");
        free(buffer);
        furi_stream_buffer_free(stream);
        pulse_glue_free(pulse_glue);
        return;
    }
#ifdef LFRFID_WORKER_READ_DEBUG_GPIO
    furi_hal_gpio_init_simple(LFRFID_WORKER_READ_DEBUG_GPIO_LOAD, GpioModeOutputPushPull);
#endif

    while(true) {""")
    header=once(header,
        """typedef enum {
    LFRFIDWorkerEmulateRawFileError,
    LFRFIDWorkerEmulateRawOverrun,
} LFRFIDWorkerEmulateRawResult;""",
        """typedef enum {
    LFRFIDWorkerEmulateRawFileError,
    LFRFIDWorkerEmulateRawOverrun,
    LFRFIDWorkerEmulateRawBusy, /* Append; preserve existing numeric values. */
} LFRFIDWorkerEmulateRawResult;""")
    raw=once(raw,
        """static int32_t lfrfid_raw_emulate_worker_thread(void* thread_context) {""",
        """/* E11 native RAW emulator: no hardware START before file is valid. */
static bool lfrfid_raw_e11_try_emulate(LFRFIDRawWorkerEmulateData* data) {
    return furi_hal_rfid_tim_emulate_dma_try_start(
        data->emulate_buffer_arr, data->emulate_buffer_ccr, EMULATE_BUFFER_SIZE,
        rfid_emulate_dma_isr, &data->ctx);
}

static int32_t lfrfid_raw_emulate_worker_thread(void* thread_context) {""")
    raw=once(raw,
        """    furi_hal_rfid_tim_emulate_dma_start(
        data->emulate_buffer_arr,
        data->emulate_buffer_ccr,
        EMULATE_BUFFER_SIZE,
        rfid_emulate_dma_isr,
        &data->ctx);

    if(!file_valid && worker->emulate_callback != NULL) {""",
        """    bool e11_started = false;
    if(file_valid &&
       !FURI_BIT(furi_event_flag_get(worker->events), LFRFIDRawWorkerEventStop)) {
        e11_started = lfrfid_raw_e11_try_emulate(data);
        if(!e11_started && worker->emulate_callback != NULL) {
            worker->emulate_callback(LFRFIDWorkerEmulateRawBusy, worker->context);
        }
    }

    if(!file_valid && worker->emulate_callback != NULL) {""")
    raw=once(raw,
        """    if(file_valid) {
        uint32_t flag = 0;""",
        """    if(file_valid && e11_started) {
        uint32_t flag = 0;""")
    raw=once(raw,
        """    furi_hal_rfid_tim_emulate_dma_stop();

    if(!file_valid) {""",
        """    if(e11_started) furi_hal_rfid_tim_emulate_dma_stop();

    if(!file_valid) {""")
    scene=once(scene,
        """    } else if(result == LFRFIDWorkerEmulateRawOverrun) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadOverrun);
    }""",
        """    } else if(result == LFRFIDWorkerEmulateRawOverrun) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadOverrun);
    } else if(result == LFRFIDWorkerEmulateRawBusy) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadBusy);
    }""")
    scene=once(scene,
        """            notification_message(app->notifications, &sequence_blink_start_red);
        }
    }

    return consumed;""",
        """            notification_message(app->notifications, &sequence_blink_start_red);
        } else if(event.event == LfRfidEventReadBusy) {
            consumed = true;
            state->error = true;
            popup_set_header(popup, "RFID BUSY", 89, 30, AlignCenter, AlignTop);
            popup_set_text(popup, "Timer or DMA in use\\nPress Back",
                           0, 13, AlignLeft, AlignTop);
            notification_message(app->notifications, &sequence_blink_start_red);
        }
    }

    return consumed;""")
    return modes,raw,header,scene

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Unpinned Momentum source")
        dirty=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed source")
            dirty.add(ln[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native source changes "+repr(sorted(dirty^EXPECTED)))
        rfid=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text(encoding="utf-8")
        if "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" not in rfid:
            raise ValueError("Missing native emulate atomic HAL owner")
        paths=(MODES,RAW,HEADER,SCENE)
        original=[(root/p).read_text(encoding="utf-8") for p in paths]
        modified=patch(*original)
        print("E11 LF RFID EMULATION WORKER/UI EXACT SOURCE PREFLIGHT PASS")
        if a.apply:
            for p,s in zip(paths,modified):
                (root/p).write_text(s,encoding="utf-8")
            print("NATIVE WORKER/UI PATCH ONLY; NO DEVICE, SD OR FLASH")
        else:
            print("READ ONLY; no source written")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 EMULATION WORKER SOURCE REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
