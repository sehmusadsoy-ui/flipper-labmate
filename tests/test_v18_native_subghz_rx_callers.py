#!/usr/bin/env python3
"""Execute pinned native SubGHz HAL -> device -> app RX BUSY C call chain.

No external plugin layout change or radio/physical verdict. Real C bodies
for the new device bool layer, built-in CC1101 wrapper and app RX method.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#define furi_check(x) assert(x)
#define furi_assert(x) assert(x)
#define FURI_LOG_W(...) ((void)0)
typedef void (*FuriHalSubGhzCaptureCallback)(bool,uint32_t,void*);
typedef struct {void (*start_async_rx)(void*,void*);} SubGhzDeviceInterconnect;
typedef struct {
 const char* name;
 const SubGhzDeviceInterconnect* interconnect;
} SubGhzDevice;
static bool hal_ok;
static int hal_starts,plugin_starts,worker_starts,speaker_ons,flushes,frequency_sets,radio_idles;
static bool furi_hal_subghz_async_rx_try_start(
 FuriHalSubGhzCaptureCallback callback,void* context) {
 (void)callback;assert(context);hal_starts++;return hal_ok;
}
static void builtin_legacy_start(void* c,void* x) {(void)c;(void)x;}
static void plugin_start(void* c,void* x) {
 (void)c;(void)x;plugin_starts++;
}
static const SubGhzDeviceInterconnect internal_iface={builtin_legacy_start};
static const SubGhzDeviceInterconnect plugin_iface={plugin_start};
static const SubGhzDevice subghz_device_cc1101_int={"cc1101_int",&internal_iface};
static const SubGhzDevice external={"external",&plugin_iface};
static void subghz_worker_rx_callback(bool level,uint32_t us,void* ctx) {
 (void)level;(void)us;(void)ctx;
}
static uint32_t subghz_devices_set_frequency(const SubGhzDevice* device,uint32_t f) {
 assert(device);frequency_sets++;return f;
}
static void subghz_devices_idle(const SubGhzDevice* dev) {
 assert(dev);radio_idles++;
}
static void subghz_devices_flush_rx(const SubGhzDevice* dev) {
 assert(dev);flushes++;
}
typedef enum { SubGhzTxRxStateIDLE,SubGhzTxRxStateRx,SubGhzTxRxStateSleep } SubGhzTxRxState;
typedef struct {
 const SubGhzDevice* radio_device;
 void* worker;
 SubGhzTxRxState txrx_state;
} SubGhzTxRx;
static void subghz_worker_start(void* worker) {
 assert(worker==(void*)&worker_starts);worker_starts++;
}
static void subghz_txrx_speaker_on(SubGhzTxRx* instance) {
 assert(instance);speaker_ons++;
}
"""
RUN=r"""
static void reset(void) {
 hal_ok=false;hal_starts=plugin_starts=worker_starts=speaker_ons=0;
 flushes=frequency_sets=radio_idles=0;
}
int main(void) {
 SubGhzTxRx app={&subghz_device_cc1101_int,&worker_starts,SubGhzTxRxStateIDLE};
 reset();
 assert(subghz_txrx_rx(&app,433920000U)==0U);
 assert(app.txrx_state==SubGhzTxRxStateIDLE);
 assert(hal_starts==1 && !worker_starts && !speaker_ons &&
        radio_idles==1 && frequency_sets==1 && flushes==1);
 reset();hal_ok=true;
 assert(subghz_txrx_rx(&app,433920000U)==433920000U);
 assert(app.txrx_state==SubGhzTxRxStateRx);
 assert(hal_starts==1 && worker_starts==1 && speaker_ons==1);
 reset();
 assert(subghz_devices_try_start_async_rx(&external,(void*)1,&app));
 assert(plugin_starts==1 && !hal_starts);
 puts("E11 actual native SubGHz device/app C BUSY and legacy plugin ABI PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    cc=(root/"lib/subghz/devices/cc1101_int/cc1101_int_interconnect.c").read_text()
    ch=(root/"lib/subghz/devices/cc1101_int/cc1101_int_interconnect.h").read_text()
    devices=(root/"lib/subghz/devices/devices.c").read_text()
    header=(root/"lib/subghz/devices/devices.h").read_text()
    app=(root/"applications/main/subghz/helpers/subghz_txrx.c").read_text()
    types=(root/"lib/subghz/devices/types.h").read_text()
    assert "/* E11 cooperative SubGHz RX BUSY path; plugin interconnect ABI unchanged. */" in devices
    assert "bool subghz_devices_try_start_async_rx(" in header
    assert "bool subghz_device_cc1101_int_interconnect_try_start_async_rx(" in ch
    assert "typedef void (*SubGhzStartAsyncRx)(void* callback, void* context);" in types
    ccfunc=cc[cc.index("bool subghz_device_cc1101_int_interconnect_try_start_async_rx("):
              cc.index("static void subghz_device_cc1101_int_interconnect_start_async_rx(")]
    # After the E11 status bridge, the genuine device helper preceding
    # this function owns the synchronous report state. Compile that exact
    # original production C too; earlier RX-only stages still work.
    start=("/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged."
           if "/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged."
           in devices else "/* E11 cooperative SubGHz RX BUSY path;")
    devfunc=devices[devices.index(start):
                    devices.index("void subghz_devices_start_async_rx(")]
    appfunc=app[app.index("static uint32_t subghz_txrx_rx("):
                app.index("static void subghz_txrx_idle(")]
    assert appfunc.index("if(!subghz_devices_try_start_async_rx(") < appfunc.index(
        "subghz_worker_start(instance->worker);")
    assert appfunc.index("if(!subghz_devices_try_start_async_rx(") < appfunc.index(
        "subghz_txrx_speaker_on(instance);")
    assert "instance->txrx_state=SubGhzTxRxStateIDLE;" in appfunc
    assert "return 0U;" in appfunc
    assert "if(device == &subghz_device_cc1101_int)" in devfunc
    assert "device->interconnect->start_async_rx(callback, context);" in devfunc
    with tempfile.TemporaryDirectory(prefix="e11_subghz_rx_callers_") as tmp:
        d=Path(tmp);src=d/"chain.c";exe=d/"chain"
        src.write_text(STUB+"\n"+ccfunc+"\n"+devfunc+"\n"+appfunc+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 actual native SubGHz device and app RX BUSY C host PASS")
    print("External plugin void callback remains ABI-compatible, cannot signal BUSY.")

if __name__=="__main__":
    main()
