#!/usr/bin/env python3
"""Execute actual pinned SubGHz firmware device bridge & ext plugin RX wrapper.

Old SubGhzDeviceInterconnect void ABI stays untouched. Host C tests genuine
post-patch production code, including matching official plugin BUSY, stale
or wrong-device reports, old third-party compatibility and recursion guard.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

HEADER=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#define furi_check(x) assert(x)
#define FURI_LOG_W(...) ((void)0)
typedef void (*SubGhzDeviceCC1101ExtCaptureCallback)(bool,uint32_t,void*);
typedef struct SubGhzDevice SubGhzDevice;
typedef struct {
 void (*start_async_rx)(void*,void*);
} SubGhzDeviceInterconnect;
struct SubGhzDevice {
 const char* name;
 const SubGhzDeviceInterconnect* interconnect;
};
static bool internal_result,plugin_result;
static int builtin_calls,plugin_calls,old_calls,nested_denials;
static const SubGhzDevice* wrong_report_device;
static bool report_twice,nested_request;
static bool subghz_device_cc1101_int_interconnect_try_start_async_rx(
    void* cb,void* ctx) {
 (void)cb;(void)ctx;builtin_calls++;return internal_result;
}
static bool subghz_device_cc1101_ext_try_start_async_rx(
    SubGhzDeviceCC1101ExtCaptureCallback cb,void* ctx) {
 (void)cb;(void)ctx;plugin_calls++;return plugin_result;
}
static void builtin_legacy_start(void* cb,void* ctx) {(void)cb;(void)ctx;}
static const SubGhzDeviceInterconnect builtin_interconnect={builtin_legacy_start};
static const SubGhzDeviceInterconnect disabled_interconnect={NULL};
const SubGhzDevice subghz_device_cc1101_int={"cc1101_int",&builtin_interconnect};
"""
RUN=r"""
static void old_external_start(void* cb,void* ctx) {
 (void)cb;(void)ctx;old_calls++;
}
static void malicious_start(void* cb,void* ctx){
 (void)cb;(void)ctx;old_calls++;
 subghz_devices_report_async_rx_start_result(wrong_report_device,true);
}
static void nested_start(void* cb,void* ctx){
 (void)cb;(void)ctx;
 if(nested_request) {
  bool inner=subghz_devices_try_start_async_rx(&subghz_device_cc1101_ext,cb,ctx);
  assert(!inner);nested_denials++;
 }
 subghz_devices_report_async_rx_start_result(&subghz_device_cc1101_ext,plugin_result);
 if(report_twice)
  subghz_devices_report_async_rx_start_result(&subghz_device_cc1101_ext,!plugin_result);
}
static const SubGhzDeviceInterconnect old_interconnect={old_external_start};
static const SubGhzDevice old_device={"third_party_v1",&old_interconnect};
static const SubGhzDeviceInterconnect nonreport_interconnect={old_external_start};
static const SubGhzDevice copied_official={"cc1101_ext",&nonreport_interconnect};
static const SubGhzDeviceInterconnect malicious_interconnect={malicious_start};
static const SubGhzDevice forged_device={"cc1101_ext",&malicious_interconnect};
static const SubGhzDeviceInterconnect nested_interconnect={nested_start};
static const SubGhzDevice nested_device={"cc1101_ext",&nested_interconnect};
static const SubGhzDevice disabled_device={"disabled",&disabled_interconnect};
int main(void){
 internal_result=false;
 assert(!subghz_devices_try_start_async_rx(&subghz_device_cc1101_int,NULL,NULL));
 assert(builtin_calls==1 && !plugin_calls);
 internal_result=true;
 assert(subghz_devices_try_start_async_rx(&subghz_device_cc1101_int,NULL,NULL));
 assert(builtin_calls==2 && !plugin_calls);
 assert(!subghz_devices_try_start_async_rx(&disabled_device,NULL,NULL));
 plugin_result=false;
 assert(!subghz_devices_try_start_async_rx(&subghz_device_cc1101_ext,NULL,NULL));
 assert(plugin_calls==1 && !e11_rx_start_pending && !e11_rx_start_reported);
 plugin_result=true;
 assert(subghz_devices_try_start_async_rx(&subghz_device_cc1101_ext,NULL,NULL));
 assert(plugin_calls==2 && !e11_rx_start_pending);
 /* Old official-name build lacking new sidechannel is not
  * mistaken for a confirmed RX. Correct matched updater is mandatory.
  */
 assert(!subghz_devices_try_start_async_rx(&copied_official,NULL,NULL));
 assert(old_calls==1 && !e11_rx_start_pending);
 /* ABI-v1 third-party callback remains callable in compatibility mode:
  * UNKNOWN is explicitly not a confirmed source of truthful BUSY.
  */
 assert(subghz_devices_try_start_async_rx(&old_device,NULL,NULL));
 assert(old_calls==2 && !e11_rx_start_pending);
 wrong_report_device=&old_device;
 assert(!subghz_devices_try_start_async_rx(&forged_device,NULL,NULL));
 assert(old_calls==3 && !e11_rx_start_pending);
 plugin_result=true;report_twice=true;nested_request=true;
 assert(subghz_devices_try_start_async_rx(&nested_device,NULL,NULL));
 assert(nested_denials==1 && !e11_rx_start_pending);
 /* Asynchronous/spurious reports outside a call do nothing. */
 subghz_devices_report_async_rx_start_result(&subghz_device_cc1101_ext,true);
 assert(!e11_rx_start_reported && !e11_rx_start_pending);
 puts("E11 original SubGHz v1 plugin sidechannel C: external BUSY/ABI PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    dev=(root/"lib/subghz/devices/devices.c").read_text()
    plugin=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext_interconnect.c").read_text()
    dh=(root/"lib/subghz/devices/devices.h").read_text()
    types=(root/"lib/subghz/devices/types.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    ext=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    assert "/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged." in dev
    assert "void subghz_devices_report_async_rx_start_result(" in dh
    assert "Function,+,subghz_devices_report_async_rx_start_result,void," in api
    assert "bool subghz_device_cc1101_ext_try_start_async_rx(" in ext
    assert "typedef void (*SubGhzStartAsyncRx)(void* callback, void* context);" in types
    assert 'SUBGHZ_RADIO_DEVICE_PLUGIN_API_VERSION 1' in types
    assert "void subghz_devices_start_async_rx(" in dh
    assert "subghz_devices_report_async_rx_start_result(" in plugin
    source=dev[dev.index("/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged."):
               dev.index("void subghz_devices_start_async_rx(",dev.index("/* E11 matched radio plugin"))]
    wrap=plugin[plugin.index("extern const SubGhzDevice subghz_device_cc1101_ext;"):
                plugin.index("static void subghz_device_cc1101_ext_interconnect_load_preset(")]
    assert "device->interconnect->start_async_rx(callback, context);" in source
    assert source.index("e11_rx_start_pending=device;") < source.index(
        "device->interconnect->start_async_rx(callback, context);")
    with tempfile.TemporaryDirectory(prefix="e11_subghz_v1_bridge_") as d:
        src=Path(d)/"original.c";exe=Path(d)/"test"
        # Use original wrapper and firstparty SubGhz device value with
        # its exact callback, not fake function replacements.
        bootstrap="static const SubGhzDeviceInterconnect official_interconnect={subghz_device_cc1101_ext_interconnect_start_async_rx};\n"
        definition='const SubGhzDevice subghz_device_cc1101_ext={"cc1101_ext",&official_interconnect};\n'
        # Official device symbol gets declaration from copied wrapper.
        src.write_text(HEADER+"\n"+source+"\n"+wrap+"\n"+bootstrap+definition+RUN)
        subprocess.run(["cc","-std=c11","-O0","-Wall","-Wextra","-Werror",
                        str(src),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 actual matched subghz_devices C + original external plugin wrapper HOST PASS")
    print("Legacy v1 third-party receiver remains UNVERIFIED, NOT universally BUSY-safe.")

if __name__=="__main__":
    main()
