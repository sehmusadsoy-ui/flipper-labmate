#!/usr/bin/env python3
"""E11: compile actual patched native iButton and protocol Misc START/STOP C.

Tests zero GPIO mutation under timer BUSY, cleanup ownership, and
the retained public void API. No firmware install or device writes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile
from test_v18_native_ibutton_tim1_lease import STUB, HARNESS

PREFIX = HARNESS.split("static void callback(void* p)")[0]
MOCK = r"""
#include <stdio.h>
typedef struct ProtocolDict { int x; } ProtocolDict;
typedef int ProtocolId;
typedef int iButtonProtocolLocalId;
typedef int iButtonProtocolData;
#define PROTOCOL_NO (-1)
static int dictionary_mutations;
size_t protocol_dict_get_data_size(ProtocolDict* dict,int id) {
    (void)dict;(void)id;return 4U;
}
void protocol_dict_set_data(ProtocolDict* dict,int id, const void* data,size_t size) {
    (void)dict;(void)id;(void)data;assert(size==4U);dictionary_mutations++;
}
void protocol_dict_encoder_start(ProtocolDict* dict,int id) {
    (void)dict;(void)id;dictionary_mutations++;
}
/* Native HAL compiled above is exact patched firmware C; callbacks use
 * the same context pointer that the real application passes.
 */
static void ibutton_protocol_group_misc_emulate_callback(void* context) {
    assert(context!=NULL);
    callback_calls++;
}
"""
RUN = r"""
int main(void) {
    furi_hal_ibutton_init();
    ProtocolDict dict={0};
    iButtonProtocolData data=0;
    iButtonProtocolGroupMisc group={
        .dict=&dict,.emulate_id=PROTOCOL_NO,.emulate_active=false};
    int w=hardware_writes;
    /* Denied lease: no internal GPIO config, no timer/IRQ, no STOP reset */
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(!group.emulate_active && !bus_enabled);
    assert(hardware_writes==w && claims==1 && !active_irq);
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(hardware_writes==w && releases==0);
    /* Legacy direct HAL TIMER is enabled: claim temporary, no pin writes */
    lease_available=true;bus_enabled=true;
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(!group.emulate_active && claims==2 && releases==1);
    assert(hardware_writes==w && !active_irq);
    bus_enabled=false;
    /* True acquired TIM1 configures pin only inside successful claim. */
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(group.emulate_active && bus_enabled && active_irq);
    assert(furi_hal_ibutton->e11_lease_handle==99U);
    int dm=dictionary_mutations;
    w=hardware_writes;
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(hardware_writes==w && dictionary_mutations==dm);
    active_irq(NULL);
    assert(callback_calls==1);
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(!group.emulate_active && !active_irq && !bus_enabled);
    assert(!furi_hal_ibutton->e11_lease_handle && releases==2);
    w=hardware_writes;
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(hardware_writes==w && releases==2);
#ifdef TEST_RELEASE_FAULT
    /* Timer STOP succeeds but opaque lease release fails; internal-pin
     * cleanup remains safe while ALL subsequent starts must deny.
     */
    release_ok=false;
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(group.emulate_active && bus_enabled);
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(!group.emulate_active && !bus_enabled && !active_irq);
    assert(furi_hal_ibutton->e11_lease_fault);
    assert(furi_hal_ibutton->e11_lease_handle==99U);
    w=hardware_writes;
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(hardware_writes==w);
#else
    /* If the clock is unexpectedly removed, STOP must NEVER perform
     * pin_reset or foreign TIM1 IRQ/peripheral cleanup.
     */
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(group.emulate_active && bus_enabled);
    bus_enabled=false;
    w=hardware_writes;
    ibutton_protocol_group_misc_emulate_stop(&group,&data,3);
    assert(group.emulate_active && hardware_writes==w);
    assert(furi_hal_ibutton->e11_lease_fault && releases==2);
    w=hardware_writes;
    ibutton_protocol_group_misc_emulate_start(&group,&data,3);
    assert(hardware_writes==w);
#endif
    puts("E11 ACTUAL NATIVE IBUTTON PROTOCOL C PASS: BUSY no GPIO, acquired pin/STOP, sticky fault");
    return 0;
}
"""

def extract(s: str, start: str, end: str) -> str:
    a=s.index(start)
    b=s.index(end,a)
    return s[a:b]

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    a=ap.parse_args()
    root=a.momentum_root.resolve()
    hal=(root/"targets/f7/furi_hal/furi_hal_ibutton.c").read_text()
    hdr=(root/"targets/f7/furi_hal/furi_hal_ibutton.h").read_text()
    protocol=(root/"lib/ibutton/protocols/misc/protocol_group_misc.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "bool furi_hal_ibutton_emulate_try_start_with_pin(" in hal
    assert "bool furi_hal_ibutton_emulate_try_stop(void)" in hal
    assert "bool furi_hal_ibutton_emulate_try_start_with_pin(" in hdr
    assert "group->emulate_active = furi_hal_ibutton_emulate_try_start_with_pin(" in protocol
    assert "if(furi_hal_ibutton_emulate_try_stop()) {" in protocol
    assert "Function,+,furi_hal_ibutton_emulate_try_stop,_Bool," in api
    assert hal.index("if(configure_pin) furi_hal_ibutton_pin_configure();") > hal.index(
        "furi_hal_resource_lease_try_acquire(")
    struct=extract(protocol,
        "typedef struct {\n    ProtocolDict* dict;\n",
        "} iButtonProtocolGroupMisc;")+"} iButtonProtocolGroupMisc;\n"
    start=extract(protocol,
        "static void ibutton_protocol_group_misc_emulate_start(",
        "static bool ibutton_protocol_group_misc_save(")
    actual = PREFIX+MOCK+struct+start+RUN
    with tempfile.TemporaryDirectory(prefix="labmate_e11_ibutton_proto_") as td:
        tmp=Path(td)
        (tmp/"stub.h").write_text(STUB)
        (tmp/"furi_hal_ibutton.c").write_text(hal)
        for inc in ("furi_hal_ibutton.h","furi_hal_interrupt.h","furi_hal_resources.h",
                    "furi_hal_bus.h","stm32wbxx_ll_tim.h","furi.h"):
            (tmp/inc).write_text("")
        (tmp/"test.c").write_text(actual)
        exe=tmp/"test"
        for faults in (False,True):
            flags=["-DTEST_RELEASE_FAULT=1"] if faults else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-pedantic","-O0",*flags,"-I",str(tmp),
                            str(tmp/"test.c"),"-o",str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
    print("E11 NATIVE IBUTTON PROTOCOL ACTUAL C 2/2 PASS (host only, NO FLASH)")

if __name__=="__main__":
    main()
