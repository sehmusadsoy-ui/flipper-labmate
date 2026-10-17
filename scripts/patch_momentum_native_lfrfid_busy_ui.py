#!/usr/bin/env python3
"""E11 pinned native LF RFID BUSY propagation to READ and RAW scene (NO FLASH)."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
MODES="lib/lfrfid/lfrfid_worker_modes.c"
HEADER="lib/lfrfid/lfrfid_worker.h"
APPH="applications/main/lfrfid/lfrfid_i.h"
READ="applications/main/lfrfid/scenes/lfrfid_scene_read.c"
RAW="applications/main/lfrfid/scenes/lfrfid_scene_raw_read.c"
MARK="/* E11 native LF RFID BUSY popup route. */"
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
    MODES,
    "lib/lfrfid/lfrfid_raw_worker.c",
    HEADER,
}

def once(t:str,a:str,b:str)->str:
    if t.count(a)!=1:
        raise ValueError("Pinned LF RFID BUSY scene anchor mismatch "+repr(a[:100]))
    return t.replace(a,b,1)

def patch(modes:str,header:str,apph:str,read:str,raw:str):
    if MARK in read or "LFRFIDWorkerReadHardwareBusy" in header:
        raise ValueError("BUSY scene stage already applied")
    modes=once(modes,
        """    if(state == LFRFIDWorkerReadOK && worker->read_cb) {
        worker->read_cb(LFRFIDWorkerReadDone, read_result, worker->cb_ctx);
    }
}""",
        """    if(state == LFRFIDWorkerReadOK && worker->read_cb) {
        worker->read_cb(LFRFIDWorkerReadDone, read_result, worker->cb_ctx);
    } else if(state == LFRFIDWorkerReadBusy && worker->read_cb) {
        /* Report BUSY, not success or timeout; scene can show an error. */
        worker->read_cb(LFRFIDWorkerReadHardwareBusy, PROTOCOL_NO, worker->cb_ctx);
    }
}""")
    header=once(header,
        """    LFRFIDWorkerReadStartPSK,
    LFRFIDWorkerReadDone,
} LFRFIDWorkerReadResult;""",
        """    LFRFIDWorkerReadStartPSK,
    LFRFIDWorkerReadDone,
    LFRFIDWorkerReadHardwareBusy, /* New E11 event, old values unchanged. */
} LFRFIDWorkerReadResult;""")
    apph=once(apph,
        """    LfRfidEventEmulationTimeExpired,
};""",
        """    LfRfidEventEmulationTimeExpired,
    LfRfidEventReadBusy, /* E11: append so existing event IDs do not shift. */
};""")
    read=once(read,
        """    } else if(result == LFRFIDWorkerReadStartPSK) {
        event = LfRfidEventReadStartPSK;
    } else {
        return;
    }""",
        """    } else if(result == LFRFIDWorkerReadStartPSK) {
        event = LfRfidEventReadStartPSK;
    } else if(result == LFRFIDWorkerReadHardwareBusy) {
        event = LfRfidEventReadBusy;
    } else {
        return;
    }""")
    read=once(read,
        """        } else if(event.event == LfRfidEventReadStartASK) {
            if(app->read_type == LFRFIDWorkerReadTypeAuto) {
                lfrfid_view_read_set_read_mode(app->read_view, LfRfidReadAsk);
            }
            consumed = true;
        }""",
        """        } else if(event.event == LfRfidEventReadStartASK) {
            if(app->read_type == LFRFIDWorkerReadTypeAuto) {
                lfrfid_view_read_set_read_mode(app->read_view, LfRfidReadAsk);
            }
            consumed = true;
        } else if(event.event == LfRfidEventReadBusy) {
            /* E11 native LF RFID BUSY popup route. */
            Popup* popup = app->popup;
            popup_reset(popup);
            popup_set_icon(popup, 83, 22, &I_WarningDolphinFlip_45x42);
            popup_set_header(popup, "RFID BUSY", 64, 0, AlignCenter, AlignTop);
            popup_set_text(popup, "Timer in use\\nPress Back", 0, 13, AlignLeft, AlignTop);
            notification_message(app->notifications, &sequence_blink_stop);
            view_dispatcher_switch_to_view(app->view_dispatcher, LfRfidViewPopup);
            consumed = true;
        }""")
    raw=once(raw,
        """    } else if(result == LFRFIDWorkerReadRawOverrun) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadOverrun);
    }""",
        """    } else if(result == LFRFIDWorkerReadRawOverrun) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadOverrun);
    } else if(result == LFRFIDWorkerReadRawBusy) {
        view_dispatcher_send_custom_event(app->view_dispatcher, LfRfidEventReadBusy);
    }""")
    raw=once(raw,
        """        } else if(event.event == LfRfidEventReadDone) {
            if(!state->error) {""",
        """        } else if(event.event == LfRfidEventReadBusy) {
            furi_timer_stop(state->timer);
            popup_set_icon(popup, 83, 22, &I_WarningDolphinFlip_45x42);
            popup_set_header(popup, "RFID BUSY", 64, 0, AlignCenter, AlignTop);
            popup_set_text(popup, "Timer in use\\nPress Back", 0, 13, AlignLeft, AlignTop);
            notification_message(app->notifications, &sequence_blink_start_red);
            state->error = true; /* Prevent false RAW success/PSK transition. */
        } else if(event.event == LfRfidEventReadDone) {
            if(!state->error) {""")
    return modes,header,apph,read,raw

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Pinned Momentum revision mismatch")
        dirty=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed native source")
            dirty.add(ln[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native source "+repr(sorted(dirty^EXPECTED)))
        raw_worker=(root/"lib/lfrfid/lfrfid_raw_worker.c").read_text(encoding="utf-8")
        modes=(root/MODES).read_text(encoding="utf-8")
        if "/* E11 native LFRFID RAW read BUSY-safe START. */" not in raw_worker or (
            "/* E11 native LFRFID read worker BUSY-safe lifecycle. */" not in modes):
            raise ValueError("Missing normal and raw worker predecessors")
        paths=(MODES,HEADER,APPH,READ,RAW)
        before=[(root/x).read_text(encoding="utf-8") for x in paths]
        after=patch(*before)
        print("E11 NATIVE RFID BUSY SCENE EXACT-SOURCE PREFLIGHT PASS")
        if a.apply:
            for name,data in zip(paths,after):
                (root/name).write_text(data,encoding="utf-8")
            print("SOURCE ONLY — NO FAP INSTALL, NO FLASH, NO SD MODIFICATIONS")
        else:
            print("READ ONLY; NONE WRITTEN")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 RFID BUSY UI PATCH REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
