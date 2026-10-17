#!/usr/bin/env python3
"""Actual pinned Accessor Wiegand C++ START/STOP/IRQ + firmware allocator.

No real user pins/device, and no claim of hardware Wiegand protocol PASS.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <cassert>
#include <cstdbool>
#include <cstdint>
#include <cstddef>
#include <cstdio>
#define FURI_LOG_W(...) ((void)0)
#define FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7 ((1U<<11)|(1U<<10)|(1U<<1)|(1U<<21))
enum { GpioModeInterruptFall=1,GpioModeAnalog=2 };
struct GpioPin {int port;int pin;};
static const GpioPin gpio_ext_pa4={1,4},gpio_ext_pa7={1,7};
static const GpioPin* const pinD0=&gpio_ext_pa4;
static const GpioPin* const pinD1=&gpio_ext_pa7;
using GpioExtiCallback=void(*)(void*);
static GpioExtiCallback callbacks[16];
static void* contexts[16];
static bool lease_ok,release_ok=true,add_ok_d0=true,add_ok_d1=true,remove_ok_d0=true,remove_ok_d1=true;
static int claims,releases,irq_adds,irq_removes,pin_writes,read_d0,read_d1;
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask){
 assert(mask==FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7);
 claims++;return lease_ok?191U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask){
 assert(owner==191U && mask==FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7);
 releases++;return release_ok;
}
static bool furi_hal_gpio_try_add_int_callback(const GpioPin* pin,GpioExtiCallback cb,void* ctx){
 assert(pin && cb);irq_adds++;
 if((pin==pinD0&&!add_ok_d0)||(pin==pinD1&&!add_ok_d1)||callbacks[pin->pin])return false;
 callbacks[pin->pin]=cb;contexts[pin->pin]=ctx;return true;
}
static bool furi_hal_gpio_try_remove_int_callback(const GpioPin* pin,GpioExtiCallback cb,void* ctx){
 assert(pin && cb);irq_removes++;
 if((pin==pinD0&&!remove_ok_d0)||(pin==pinD1&&!remove_ok_d1)||
    callbacks[pin->pin]!=cb||contexts[pin->pin]!=ctx)return false;
 callbacks[pin->pin]=nullptr;contexts[pin->pin]=nullptr;return true;
}
static void furi_hal_gpio_init_simple(const GpioPin* pin,int mode){
 assert((pin==pinD0||pin==pinD1) && (mode==GpioModeInterruptFall||mode==GpioModeAnalog));
 pin_writes++;
}
"""
RUN=r"""
WIEGAND::WIEGAND() {}
unsigned long WIEGAND::_cardTempHigh=0;
unsigned long WIEGAND::_cardTemp=0;
unsigned long WIEGAND::_lastWiegand=0;
unsigned long WIEGAND::_code=0;
unsigned long WIEGAND::_codeHigh=0;
int WIEGAND::_bitCount=0;
int WIEGAND::_wiegandType=0;
void WIEGAND::ReadD0() {read_d0++;}
void WIEGAND::ReadD1() {read_d1++;}
static void foreign(void* ctx){(void)ctx;}
static void reset_case(){
 lease_ok=false;release_ok=true;add_ok_d0=add_ok_d1=remove_ok_d0=remove_ok_d1=true;
 claims=releases=irq_adds=irq_removes=pin_writes=read_d0=read_d1=0;
 for(int i=0;i<16;i++){callbacks[i]=nullptr;contexts[i]=nullptr;}
}
int main(){
 reset_case();
 WIEGAND denied;
 denied.begin();
 denied.end();
 assert(claims==1 && !pin_writes && !irq_adds && !irq_removes);
 reset_case();lease_ok=true;
 callbacks[4]=foreign;contexts[4]=reinterpret_cast<void*>(15);
 WIEGAND busy_d0;
 assert(!busy_d0.tryBegin());
 assert(callbacks[4]==foreign && contexts[4]==reinterpret_cast<void*>(15));
 assert(!pin_writes && irq_adds==1 && irq_removes==0 && releases==1);
 busy_d0.end();assert(!pin_writes);
 reset_case();lease_ok=true;callbacks[7]=foreign;contexts[7]=reinterpret_cast<void*>(19);
 WIEGAND busy_d1;
 assert(!busy_d1.tryBegin());
 assert(callbacks[7]==foreign && callbacks[4]==nullptr &&
        irq_adds==2 && irq_removes==1 && releases==1 && !pin_writes);
 busy_d1.end();
 reset_case();lease_ok=true;
 WIEGAND active;
 assert(active.tryBegin());
 assert(claims==1 && callbacks[4] && callbacks[7] && pin_writes==2);
 int tries=claims;
 assert(!active.tryBegin() && claims==tries);
 callbacks[4](contexts[4]);callbacks[7](contexts[7]);
 assert(read_d0==1 && read_d1==1);
 active.end();
 assert(releases==1 && callbacks[4]==nullptr && callbacks[7]==nullptr &&
        irq_removes==2 && pin_writes==4);
 int old=pin_writes;active.end();assert(old==pin_writes);
 assert(active.tryBegin());active.end();
 reset_case();lease_ok=true;
 WIEGAND changed;
 assert(changed.tryBegin());
 callbacks[4]=foreign;old=pin_writes;
 changed.end();assert(callbacks[4]==foreign && pin_writes==old &&
                      irq_removes==1 && releases==0);
 assert(!changed.tryBegin() && claims==1);
 reset_case();lease_ok=true;remove_ok_d1=false;
 WIEGAND changed_d1;
 assert(changed_d1.tryBegin());old=pin_writes;
 changed_d1.end();assert(pin_writes==old && releases==0);
 reset_case();lease_ok=true;release_ok=false;
 WIEGAND sticky;
 assert(sticky.tryBegin());sticky.end();
 assert(releases==1 && !sticky.tryBegin());
 old=pin_writes;sticky.end();assert(old==pin_writes);
 reset_case();lease_ok=true;release_ok=false;add_ok_d1=false;
 WIEGAND partial_sticky;
 assert(!partial_sticky.tryBegin() && releases==1 && !pin_writes);
 assert(!partial_sticky.tryBegin() && claims==1);
 puts("E11 actual native Wiegand C++ PA4/PA7 callback BUSY/STOP/fault PASS");
 return 0;
}
"""
MASK=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"Wiegand allocator fail %d\n",__LINE__);exit(1);}}while(0)
int main(void){
 uint32_t owner=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7);
 CHECK(owner);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PA4));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI4));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI7));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7));
 CHECK(!furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_PWM_PA7));
 CHECK(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7));
 CHECK(!furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7));
 puts("E11 genuine firmware allocator Wiegand PA4/PA7/EXTI conflicts PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    wh=(root/"applications/debug/accessor/helpers/wiegand.h").read_text()
    wc=(root/"applications/debug/accessor/helpers/wiegand.cpp").read_text()
    app=(root/"applications/debug/accessor/accessor_app.cpp").read_text()
    assert "FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7" in r
    assert "bool tryBegin(void);" in wh
    assert "/* E11 Accessor Wiegand PA4+PA7 EXTI4/EXTI7 owner. */" in wc
    assert "const bool wiegand_ready=wiegand.tryBegin();" in app
    assert "furi_hal_gpio_remove_int_callback(" not in wc
    assert "furi_hal_gpio_add_int_callback(" not in wc
    assert "if(!e11_owner || e11_fault) return;" in wc
    native=wc[wc.index("static void input_isr_d0(void* _ctx) {"):wc.index("void WIEGAND::ReadD0() {")]
    assert native.index("furi_hal_resource_lease_try_acquire(")<native.index("furi_hal_gpio_try_add_int_callback(")
    assert native.index("furi_hal_gpio_try_add_int_callback(")<native.index("furi_hal_gpio_init_simple(pinD0,")
    assert native.index("furi_hal_gpio_try_remove_int_callback(")<native.index("furi_hal_gpio_init_simple(pinD0,GpioModeAnalog)")
    with tempfile.TemporaryDirectory(prefix="e11_wiegand_") as temp:
        d=Path(temp);exe=d/"test"
        header=d/"wiegand.h";header.write_text(wh)
        (d/"native.cpp").write_text(STUB+'\n#include "wiegand.h"\n'+native+"\n"+RUN)
        subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror","-pedantic",
                        str(d/"native.cpp"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        pre=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do{if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do{if(pthread_mutex_unlock(&critical))abort();}while(0)
"""
        masks=h[h.index("enum {\n    FuriHalLeaseTim1"):h.index("/* Returns unique nonzero")]
        allocator=r[r.index("/* Firmware-owned E11 lease primitive"):r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (d/"lease.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 actual native Wiegand C++/firmware allocator strict host PASS")
    print("Physical Wiegand button/UI, native input and GPIO failure recovery OPEN")

if __name__=="__main__": main()
