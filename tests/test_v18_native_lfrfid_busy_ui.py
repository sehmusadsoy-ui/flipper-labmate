#!/usr/bin/env python3
"""Execute real native LF RFID READ and RAW callback C BUSY-event dispatch.

Source audit also prevents RAW success timer from overriding a BUSY scene.
This is a host test, not a GUI/physical acceptance.
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
typedef int ProtocolId;
enum {
 LFRFIDWorkerReadSenseStart, LFRFIDWorkerReadSenseEnd,
 LFRFIDWorkerReadSenseCardStart, LFRFIDWorkerReadSenseCardEnd,
 LFRFIDWorkerReadStartASK, LFRFIDWorkerReadStartPSK,
 LFRFIDWorkerReadDone, LFRFIDWorkerReadHardwareBusy
};
typedef int LFRFIDWorkerReadResult;
enum {
 LFRFIDWorkerReadRawFileError,LFRFIDWorkerReadRawOverrun,
 LFRFIDWorkerReadRawBusy
};
typedef int LFRFIDWorkerReadRawResult;
enum {
 LfRfidEventReadSenseStart=101, LfRfidEventReadSenseEnd,
 LfRfidEventReadSenseCardStart, LfRfidEventReadSenseCardEnd,
 LfRfidEventReadStartASK, LfRfidEventReadStartPSK,
 LfRfidEventReadDone, LfRfidEventReadOverrun, LfRfidEventReadError,
 LfRfidEventReadBusy
};
typedef struct {void* view_dispatcher; int protocol_id_next;} LfRfid;
static int event_count,last_event;
static void view_dispatcher_send_custom_event(void* dispatcher,uint32_t event) {
 assert(dispatcher==(void*)&event_count);event_count++;last_event=(int)event;
}
"""
RUN=r"""
int main(void) {
 LfRfid app={.view_dispatcher=&event_count,.protocol_id_next=0};
 event_count=last_event=0;
 lfrfid_e11_normal_cb(LFRFIDWorkerReadHardwareBusy,0,&app);
 assert(event_count==1 && last_event==LfRfidEventReadBusy);
 event_count=0;
 lfrfid_e11_raw_cb(LFRFIDWorkerReadRawBusy,&app);
 assert(event_count==1 && last_event==LfRfidEventReadBusy);
 event_count=0;
 lfrfid_e11_normal_cb(LFRFIDWorkerReadDone,17,&app);
 assert(event_count==1 && last_event==LfRfidEventReadDone && app.protocol_id_next==17);
 event_count=0;
 lfrfid_e11_raw_cb(LFRFIDWorkerReadRawFileError,&app);
 assert(event_count==1 && last_event==LfRfidEventReadError);
 puts("E11 actual LF RFID READ/RAW callback C BUSY event routing PASS");
 return 0;
}
"""
def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    apph=(root/"applications/main/lfrfid/lfrfid_i.h").read_text()
    modes=(root/"lib/lfrfid/lfrfid_worker_modes.c").read_text()
    rscene=(root/"applications/main/lfrfid/scenes/lfrfid_scene_read.c").read_text()
    rawscene=(root/"applications/main/lfrfid/scenes/lfrfid_scene_raw_read.c").read_text()
    enum=(root/"lib/lfrfid/lfrfid_worker.h").read_text()
    assert "LfRfidEventReadBusy" in apph
    assert "LFRFIDWorkerReadHardwareBusy" in enum
    assert "LFRFIDWorkerReadRawBusy" in enum
    assert "worker->read_cb(LFRFIDWorkerReadHardwareBusy, PROTOCOL_NO, worker->cb_ctx);" in modes
    normal=rscene[rscene.index("static void\n    lfrfid_read_callback("):
                  rscene.index("void lfrfid_scene_read_on_enter(")]
    raw=rawscene[rawscene.index("static void lfrfid_read_callback("):
                 rawscene.index("static void timer_callback(")]
    assert "event = LfRfidEventReadBusy;" in normal
    assert "LfRfidEventReadBusy" in raw
    assert "event.event == LfRfidEventReadBusy" in rscene
    assert 'popup_set_header(popup, "RFID BUSY"' in rscene
    assert "event.event == LfRfidEventReadBusy" in rawscene
    assert 'popup_set_header(popup, "RFID BUSY"' in rawscene
    assert "state->error = true; /* Prevent false RAW success/PSK transition. */" in rawscene
    assert "if(!state->error)" in rawscene
    assert "furi_timer_stop(state->timer);" in rawscene
    normal=normal.replace("lfrfid_read_callback(", "lfrfid_e11_normal_cb(")
    raw=raw.replace("lfrfid_read_callback(", "lfrfid_e11_raw_cb(")
    with tempfile.TemporaryDirectory(prefix="e11_lfrfid_busy_ui_") as t:
        tmp=Path(t);src=tmp/"scenes.c";exe=tmp/"scenes"
        src.write_text(STUB+"\n"+normal+"\n"+raw+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 native LF RFID callback actual C BUSY and no false RAW success route PASS")

if __name__=="__main__":
    main()
