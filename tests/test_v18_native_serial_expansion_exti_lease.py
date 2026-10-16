#!/usr/bin/env python3
"""Compile actual pinned native serial expansion C and firmware atomic allocator.

Covers BOTH USART1/PB7/EXTI7 and LPUART1/PC0/EXTI0, queue BUSY
propagation, callback ownership and native UART direction preserving STOP.
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
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define FURI_LOG_W(...) ((void)0)
#define TAG "SerialControl"
#define FuriWaitForever 0
enum { FuriHalSerialIdUsart=0,FuriHalSerialIdLpuart=1,FuriHalSerialIdMax=2 };
enum { FuriHalSerialDirectionRx=0,GpioModeInterruptFall=1,
 GpioPullUp=1,GpioSpeedLow=0 };
#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1 ((1U<<12)|(1U<<30)|(1U<<21))
#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ((1U<<31)|(1U<<5)|(1U<<4))
typedef int FuriHalSerialId;
typedef struct {int id;bool in_use;} FuriHalSerialHandle;
typedef struct {int port,pin;} GpioPin;
static const GpioPin gpio_usart_rx={2,7},gpio_ext_pc0={3,0},alien={3,3};
typedef void (*GpioExtiCallback)(void*);
typedef void (*FuriHalSerialControlExpansionCallback)(void*);
typedef void* FuriApiLock;
typedef struct {int dummy;} FuriMessageQueue;
typedef struct {int dummy;} FuriThread;
typedef struct {struct {void (*callback)(const uint8_t*,size_t,void*);void* context;} fields;} FuriLogHandler;
typedef enum {
 FuriHalSerialControlMessageTypeStop,
 FuriHalSerialControlMessageTypeAcquire,
 FuriHalSerialControlMessageTypeRelease,
 FuriHalSerialControlMessageTypeIsBusy,
 FuriHalSerialControlMessageTypeLogging,
 FuriHalSerialControlMessageTypeExpansionSetCallback,
 FuriHalSerialControlMessageTypeExpansionIrq,
} FuriHalSerialControlMessageType;
typedef struct {
 FuriHalSerialControlMessageType type;
 FuriApiLock api_lock;
 void* input;
 void* output;
} FuriHalSerialControlMessage;
typedef struct {
 const FuriHalSerialId id;
 const FuriHalSerialControlExpansionCallback callback;
 void* context;
} FuriHalSerialControlMessageExpCallback;
typedef struct {
 FuriHalSerialHandle handles[FuriHalSerialIdMax];
 FuriMessageQueue* queue;
 FuriThread* thread;
 FuriHalSerialId log_config_serial_id;
 uint32_t log_config_serial_baud_rate;
 FuriLogHandler log_handler;
 FuriHalSerialHandle* log_serial;
 FuriHalSerialHandle* expansion_serial;
 FuriHalSerialControlExpansionCallback expansion_cb;
 void* expansion_ctx;
} FuriHalSerialControl;
static FuriHalSerialControl storage;
static FuriHalSerialControl* furi_hal_serial_control=&storage;
static GpioExtiCallback slots[16];
static void* contexts[16];
static int claims,releases,irq_adds,irq_removes,rx_disables,rx_enables,mode_writes,irq_posts;
static bool lease_allowed,release_allowed=true,slot_add_allowed=true,slot_remove_allowed=true;
static int callback_count;
static uint32_t expected_mask;
static const GpioPin* furi_hal_serial_get_gpio_pin(FuriHalSerialHandle* h,int direction) {
 assert(direction==FuriHalSerialDirectionRx);
 if(h->id==FuriHalSerialIdUsart)return &gpio_usart_rx;
 if(h->id==FuriHalSerialIdLpuart)return &gpio_ext_pc0;
 return &alien;
}
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==expected_mask);claims++;return lease_allowed?111U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
 assert(h==111U && mask==expected_mask);releases++;return release_allowed;
}
static int pin_index(const GpioPin* g) {return g->pin;}
static bool furi_hal_gpio_try_add_int_callback(const GpioPin* g,GpioExtiCallback cb,void* ctx) {
 assert(g && cb);irq_adds++;int idx=pin_index(g);
 if(!slot_add_allowed || slots[idx]) return false;
 slots[idx]=cb;contexts[idx]=ctx;return true;
}
static bool furi_hal_gpio_try_remove_int_callback(const GpioPin* g,GpioExtiCallback cb,void* ctx) {
 assert(g && cb);irq_removes++;int idx=pin_index(g);
 if(!slot_remove_allowed || slots[idx]!=cb || contexts[idx]!=ctx)return false;
 slots[idx]=NULL;contexts[idx]=NULL;return true;
}
static void furi_hal_gpio_init(const GpioPin* g,int mode,int pull,int speed) {
 assert(g && mode==GpioModeInterruptFall && pull==GpioPullUp && speed==GpioSpeedLow);
 mode_writes++;
}
static void furi_hal_serial_disable_direction(FuriHalSerialHandle* h,int dir) {
 assert(h && dir==FuriHalSerialDirectionRx);rx_disables++;
}
static void furi_hal_serial_enable_direction(FuriHalSerialHandle* h,int dir) {
 assert(h && dir==FuriHalSerialDirectionRx);rx_enables++;
}
static bool furi_hal_serial_control_handler_expansion_set_callback(void*,void*);
static FuriApiLock api_lock_alloc_locked(void) {return (FuriApiLock)1;}
static void api_lock_wait_unlock_and_free(FuriApiLock lock) {assert(lock);}
static int furi_message_queue_put(FuriMessageQueue* q,const void* msg,uint32_t wait) {
 (void)q;(void)wait;
 const FuriHalSerialControlMessage* m=msg;
 if(m->type==FuriHalSerialControlMessageTypeExpansionSetCallback) {
  assert(furi_hal_serial_control_handler_expansion_set_callback(m->input,m->output));
 } else if(m->type==FuriHalSerialControlMessageTypeExpansionIrq) {irq_posts++;}
 else abort();
 return 0;
}
"""
RUN=r"""
static void expansion(void* ctx) {assert(ctx==&storage);callback_count++;}
static void foreign(void* ctx) {(void)ctx;}
static void reset_case(void) {
 claims=releases=irq_adds=irq_removes=rx_disables=rx_enables=mode_writes=irq_posts=callback_count=0;
 lease_allowed=false;release_allowed=slot_add_allowed=slot_remove_allowed=true;
 for(int i=0;i<16;i++){slots[i]=NULL;contexts[i]=NULL;}
 storage.expansion_serial=NULL;storage.expansion_cb=NULL;storage.expansion_ctx=NULL;
 storage.log_serial=NULL;
 storage.handles[0].id=0;storage.handles[0].in_use=false;
 storage.handles[1].id=1;storage.handles[1].in_use=false;
 e11_exp_owner=e11_exp_mask=0U;e11_exp_handle=NULL;e11_exp_fault=false;
 expected_mask=FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1;
}
static void assert_denied_no_effect(void) {
 assert(rx_disables==0 && rx_enables==0 && mode_writes==0 &&
        !storage.expansion_serial && !storage.expansion_cb && !e11_exp_owner);
}
int main(void) {
 reset_case();
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert_denied_no_effect();assert(claims==1 && !irq_adds);
 furi_hal_serial_control_expansion_irq_callback(NULL);assert(!irq_posts);
 reset_case();lease_allowed=true;slot_add_allowed=false;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert_denied_no_effect();assert(irq_adds==1 && releases==1);
 reset_case();lease_allowed=true;
 slots[7]=foreign;contexts[7]=(void*)9;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert(slots[7]==foreign && contexts[7]==(void*)9);
 assert_denied_no_effect();assert(releases==1 && irq_removes==0);
 reset_case();lease_allowed=true;
 storage.handles[0].in_use=true;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert(!claims && !irq_adds);
 reset_case();lease_allowed=true;
 assert(furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert(storage.expansion_serial==&storage.handles[0] && e11_exp_owner==111U &&
        slots[7]==furi_hal_serial_control_expansion_irq_callback);
 assert(rx_disables==1 && mode_writes==1 && !rx_enables);
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert(claims==1);
 slots[7](contexts[7]);assert(irq_posts==1);
 assert(furi_hal_serial_control_try_set_expansion_callback(0,NULL,NULL));
 assert(!storage.expansion_serial && !storage.expansion_cb &&
        !e11_exp_owner && releases==1 && rx_enables==1 && irq_removes==1);
 assert(!slots[7] && contexts[7]==NULL);
 int old=rx_enables;
 assert(furi_hal_serial_control_enable_expansion_irq(&storage.handles[0],false));
 assert(old==rx_enables && releases==1);
 reset_case();lease_allowed=true;expected_mask=FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1;
 assert(furi_hal_serial_control_try_set_expansion_callback(1,expansion,&storage));
 assert(storage.expansion_serial==&storage.handles[1] && e11_exp_mask==expected_mask);
 assert(slots[0]==furi_hal_serial_control_expansion_irq_callback);
 assert(furi_hal_serial_control_try_set_expansion_callback(1,NULL,NULL));
 assert(releases==1 && rx_enables==1);
 reset_case();lease_allowed=true;expected_mask=FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1;
 slots[0]=foreign;contexts[0]=(void*)5;
 assert(!furi_hal_serial_control_try_set_expansion_callback(1,expansion,&storage));
 assert_denied_no_effect();assert(slots[0]==foreign);
 reset_case();lease_allowed=true;
 assert(furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 slots[7]=foreign;old=rx_enables;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,NULL,NULL));
 assert(storage.expansion_cb==expansion && storage.expansion_serial &&
        e11_exp_fault && e11_exp_owner && releases==0);
 assert(rx_enables==old && slots[7]==foreign && !irq_posts);
 reset_case();lease_allowed=true;release_allowed=false;slot_add_allowed=false;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 assert(e11_exp_fault && e11_exp_owner && !rx_disables);
 reset_case();lease_allowed=true;
 assert(furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 release_allowed=false;old=rx_enables;
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,NULL,NULL));
 assert(e11_exp_fault && e11_exp_owner && rx_enables==old+1 && releases==1);
 assert(!furi_hal_serial_control_try_set_expansion_callback(0,expansion,&storage));
 puts("E11 real native serial RX expansion C: USART/LPUART BUSY/callback/STOP PASS");
 return 0;
}
"""
MASK=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"SERIAL lease fail line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1);
 CHECK(a);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_USART1));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_JS_EXTI7));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1));
 CHECK(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1));
 uint32_t b=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1);
 CHECK(b);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC0));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PC0));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT));
 CHECK(!furi_hal_resource_lease_release(b,FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1));
 CHECK(furi_hal_resource_lease_release(b,FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1));
 CHECK(!furi_hal_resource_lease_release(b,FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1));
 puts("E11 real allocator USART1 PB7/EXTI7 & LPUART1 PC0/EXTI0 masks PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_serial_control.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    pub=(root/"targets/f7/furi_hal/furi_hal_serial_control.h").read_text()
    assert "/* E11 native serial expansion RX pin/EXTI owner. */" in s
    for key in ("FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1",
                "FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1"):
        assert key in h and "mask == "+key in r
    assert "bool furi_hal_serial_control_try_set_expansion_callback(" in pub
    assert "Function,+,furi_hal_serial_control_try_set_expansion_callback,_Bool," in api
    assert s.count("furi_hal_gpio_try_add_int_callback(")==1
    assert s.count("furi_hal_gpio_try_remove_int_callback(")==1
    assert s.index("furi_hal_resource_lease_try_acquire(")<s.index("furi_hal_serial_disable_direction(handle,FuriHalSerialDirectionRx);")
    assert s.index("furi_hal_gpio_try_add_int_callback(")<s.index("furi_hal_serial_disable_direction(handle,FuriHalSerialDirectionRx);")
    assert "return true; /* Keep the SerialControl queue alive even on BUSY. */" in s
    helper=s[s.index("/* E11 native serial expansion RX pin/EXTI owner. */"):
             s.index("static void furi_hal_serial_control_log_callback(")]
    irq=s[s.index("static void furi_hal_serial_control_expansion_irq_callback("):
          s.index("static void furi_hal_serial_control_log_set_handle(")]
    handler=s[s.index("static bool furi_hal_serial_control_handler_expansion_set_callback("):
              s.index("static bool furi_hal_serial_control_handler_expansion_irq(")]
    public=s[s.index("bool furi_hal_serial_control_try_set_expansion_callback("):]
    with tempfile.TemporaryDirectory(prefix="e11_serial_exp_") as tmp:
        d=Path(tmp);exe=d/"test"
        (d/"serial.c").write_text(STUB+"\n"+helper+"\n"+irq+"\n"+handler+"\n"+public+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(d/"serial.c"),"-o",str(exe)],check=True)
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
        (d/"allocator.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"allocator.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 ORIGINAL native SerialControl C and allocator USART/LPUART HOST PASS")
    print("Physical UART, expansion detection and foreign plug-in clients remain OPEN")

if __name__=="__main__":
    main()
