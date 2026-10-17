#!/usr/bin/env python3
"""E11 native USART1 PB7/EXTI7 and LPUART1 PC0/EXTI0 expansion IRQ owner.

Original pinned Momentum serial-control queue/client path, exact ownership
and truthful bool registration. Stages source only, NO FLASH/SD/USB.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_nfc_irq_exti_lease import EXPECTED as NFC_PRE, IRQ, NFC, I
from patch_momentum_native_onewire_slave_exti_lease import H, R, GH, GC, OH, OC, DALLAS, API
from patch_momentum_native_subghz_tx_lease import S as SUB

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
SER="targets/f7/furi_hal/furi_hal_serial_control.c"
PUB="targets/f7/furi_hal/furi_hal_serial_control.h"
MARK="/* E11 native serial expansion RX pin/EXTI owner. */"
EXPECTED=NFC_PRE | {H,R,GH,GC,OH,OC,DALLAS,API,SUB,IRQ,NFC,I}

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned native serial exact-source anchor missing/ambiguous "+repr(old[:120]))
    return s.replace(old,new,1)

def patch(h,r,src,pub,api):
    if MARK in src or "FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1" in h:
        raise ValueError("Native serial expansion already patched")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 (FuriHalLeasePa2|FuriHalLeaseExti2)\n",
        "#define FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 (FuriHalLeasePa2|FuriHalLeaseExti2)\n"
        "/* USART1 RX PB7 / LPUART1 RX PC0: distinct physical EXTI aliases. */\n"
        "#define FuriHalLeasePb7 (1UL<<30)\n#define FuriHalLeaseLpuart1 (1UL<<31)\n"
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1 (FuriHalLeaseUsart1|FuriHalLeasePb7|FuriHalLeaseExti7)\n"
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n")
    src=once(src,'#include "furi_hal_serial.h"\n',
        '#include "furi_hal_serial.h"\n#include <furi_hal_resources.h>\n')
    src=once(src,
        "FuriHalSerialControl* furi_hal_serial_control = NULL;\n",
        """FuriHalSerialControl* furi_hal_serial_control = NULL;

/* E11 native serial expansion RX pin/EXTI owner. */
static uint32_t e11_exp_owner;
static uint32_t e11_exp_mask;
static FuriHalSerialHandle* e11_exp_handle;
static bool e11_exp_fault;

static uint32_t e11_exp_mask_for(const FuriHalSerialHandle* handle,const GpioPin* pin) {
    if(handle->id==FuriHalSerialIdUsart && pin==&gpio_usart_rx)
        return FURI_HAL_LEASE_NATIVE_SERIAL_EXP_USART1;
    if(handle->id==FuriHalSerialIdLpuart && pin==&gpio_ext_pc0)
        return FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1;
    return 0U; /* Unknown UART or GPIO must not be modified. */
}
""")
    src=once(src,
        """static void furi_hal_serial_control_expansion_irq_callback(void* context) {
    UNUSED(context);

    FuriHalSerialControlMessage message;""",
        """static void furi_hal_serial_control_expansion_irq_callback(void* context) {
    UNUSED(context);
    if(!e11_exp_owner || e11_exp_fault) return;

    FuriHalSerialControlMessage message;""")
    src=once(src,
        """static void
    furi_hal_serial_control_enable_expansion_irq(FuriHalSerialHandle* handle, bool enable) {
    const GpioPin* gpio = furi_hal_serial_get_gpio_pin(handle, FuriHalSerialDirectionRx);

    if(enable) {
        furi_hal_serial_disable_direction(handle, FuriHalSerialDirectionRx);
        furi_hal_gpio_add_int_callback(gpio, furi_hal_serial_control_expansion_irq_callback, NULL);
        furi_hal_gpio_init(gpio, GpioModeInterruptFall, GpioPullUp, GpioSpeedLow);
    } else {
        furi_hal_gpio_remove_int_callback(gpio);
        furi_hal_serial_enable_direction(handle, FuriHalSerialDirectionRx);
    }
}""",
        """static bool
    furi_hal_serial_control_enable_expansion_irq(FuriHalSerialHandle* handle, bool enable) {
    if(!handle || e11_exp_fault) return false;
    const GpioPin* gpio = furi_hal_serial_get_gpio_pin(handle,FuriHalSerialDirectionRx);
    const uint32_t mask=e11_exp_mask_for(handle,gpio);
    if(!mask) return false;
    if(enable) {
        if(e11_exp_owner || handle->in_use) return false;
        const uint32_t lease=furi_hal_resource_lease_try_acquire(mask);
        if(!lease) return false;
        e11_exp_owner=lease;
        e11_exp_mask=mask;
        e11_exp_handle=handle;
        /* The exact callback CAS happens BEFORE disabling the UART RX
         * direction or touching its physical PB7/PC0 GPIO mode.
         */
        if(!furi_hal_gpio_try_add_int_callback(
               gpio,furi_hal_serial_control_expansion_irq_callback,NULL)) {
            if(furi_hal_resource_lease_release(lease,mask)) {
                e11_exp_owner=0U;
                e11_exp_mask=0U;
                e11_exp_handle=NULL;
            } else {
                e11_exp_fault=true; /* Sticky ownership on failed release. */
            }
            return false;
        }
        furi_hal_serial_disable_direction(handle,FuriHalSerialDirectionRx);
        furi_hal_gpio_init(gpio,GpioModeInterruptFall,GpioPullUp,GpioSpeedLow);
        return true;
    }
    /* BUSY/denied start is never a license to enable an unrelated UART,
     * clear foreign EXTI, or reset a nonowned physical GPIO.
     */
    if(!e11_exp_owner) return true;
    if(e11_exp_handle!=handle || e11_exp_mask!=mask) {
        e11_exp_fault=true;
        return false;
    }
    if(!furi_hal_gpio_try_remove_int_callback(
           gpio,furi_hal_serial_control_expansion_irq_callback,NULL)) {
        e11_exp_fault=true;
        return false;
    }
    furi_hal_serial_enable_direction(handle,FuriHalSerialDirectionRx);
    if(furi_hal_resource_lease_release(e11_exp_owner,mask)) {
        e11_exp_owner=0U;
        e11_exp_mask=0U;
        e11_exp_handle=NULL;
        return true;
    }
    e11_exp_fault=true;
    return false;
}""")
    src=once(src,
        """        furi_hal_serial_control_enable_expansion_irq(
            furi_hal_serial_control->expansion_serial, false);
    }

    if(furi_hal_serial_control->log_serial) {""",
        """        if(!furi_hal_serial_control_enable_expansion_irq(
               furi_hal_serial_control->expansion_serial,false)) {
            FURI_LOG_W(TAG,"Expansion IRQ cannot release its exact owner");
            return; /* Logging must not steal UART/EXTI on refused STOP. */
        }
    }

    if(furi_hal_serial_control->log_serial) {""")
    src=once(src,
        """        furi_hal_serial_control_enable_expansion_irq(
            furi_hal_serial_control->expansion_serial, true);
    }
}""",
        """        if(!furi_hal_serial_control_enable_expansion_irq(
               furi_hal_serial_control->expansion_serial,true)) {
            FURI_LOG_W(TAG,"Expansion IRQ BUSY during logging resume");
        }
    }
}""")
    src=once(src,
        """        } else if(furi_hal_serial_control->expansion_serial == handle) {
            furi_hal_serial_control_enable_expansion_irq(handle, false);
        }
        // Return handle""",
        """        } else if(furi_hal_serial_control->expansion_serial == handle) {
            if(!furi_hal_serial_control_enable_expansion_irq(handle,false)) {
                *(FuriHalSerialHandle**)output=NULL;
                return true; /* Failed STOP cannot hand out foreign UART. */
            }
        }
        // Return handle""")
    src=once(src,
        """        furi_hal_serial_control_enable_expansion_irq(handle, true);
    }

    return true;
}""",
        """        if(!furi_hal_serial_control_enable_expansion_irq(handle,true)) {
            FURI_LOG_W(TAG,"Expansion IRQ BUSY after serial release");
        }
    }

    return true;
}""")
    src=once(src,
        """static bool furi_hal_serial_control_handler_expansion_set_callback(void* input, void* output) {
    UNUSED(output);

    FuriHalSerialControlMessageExpCallback* message_input = input;
    FuriHalSerialHandle* handle = &furi_hal_serial_control->handles[message_input->id];

    const bool enable_irq = message_input->callback != NULL;

    if(enable_irq) {
        furi_check(furi_hal_serial_control->expansion_serial == NULL);
        furi_check(furi_hal_serial_control->expansion_cb == NULL);
        furi_hal_serial_control->expansion_serial = handle;
    } else {
        furi_check(furi_hal_serial_control->expansion_serial == handle);
        furi_check(furi_hal_serial_control->expansion_cb != NULL);
        furi_hal_serial_control->expansion_serial = NULL;
    }

    furi_hal_serial_control->expansion_cb = message_input->callback;
    furi_hal_serial_control->expansion_ctx = message_input->context;

    furi_hal_serial_control_enable_expansion_irq(handle, enable_irq);

    return true;
}""",
        """static bool furi_hal_serial_control_handler_expansion_set_callback(void* input, void* output) {
    FuriHalSerialControlMessageExpCallback* msg=input;
    bool accepted=false;
    if(msg->id >= FuriHalSerialIdMax) goto done;
    FuriHalSerialHandle* handle=&furi_hal_serial_control->handles[msg->id];
    if(msg->callback) {
        if(furi_hal_serial_control->expansion_serial ||
           furi_hal_serial_control->expansion_cb || handle->in_use ||
           furi_hal_serial_control->log_serial==handle) goto done;
        if(!furi_hal_serial_control_enable_expansion_irq(handle,true)) goto done;
        /* Publish the software registration only after hardware owner. */
        furi_hal_serial_control->expansion_serial=handle;
        furi_hal_serial_control->expansion_cb=msg->callback;
        furi_hal_serial_control->expansion_ctx=msg->context;
        accepted=true;
    } else {
        if(furi_hal_serial_control->expansion_serial!=handle ||
           !furi_hal_serial_control->expansion_cb) goto done;
        if(!furi_hal_serial_control_enable_expansion_irq(handle,false)) goto done;
        furi_hal_serial_control->expansion_serial=NULL;
        furi_hal_serial_control->expansion_cb=NULL;
        furi_hal_serial_control->expansion_ctx=NULL;
        accepted=true;
    }
done:
    if(output) *(bool*)output=accepted;
    return true; /* Keep the SerialControl queue alive even on BUSY. */
}""")
    src=once(src,
        """void furi_hal_serial_control_set_expansion_callback(
    FuriHalSerialId serial_id,
    FuriHalSerialControlExpansionCallback callback,
    void* context) {
    furi_check(serial_id <= FuriHalSerialIdMax);
    furi_check(furi_hal_serial_control);

    FuriHalSerialControlMessageExpCallback message_input = {
        .id = serial_id,
        .callback = callback,
        .context = context,
    };
    FuriHalSerialControlMessage message;
    message.type = FuriHalSerialControlMessageTypeExpansionSetCallback;
    message.api_lock = api_lock_alloc_locked();
    message.input = &message_input;
    furi_message_queue_put(furi_hal_serial_control->queue, &message, FuriWaitForever);
    api_lock_wait_unlock_and_free(message.api_lock);
}""",
        """bool furi_hal_serial_control_try_set_expansion_callback(
    FuriHalSerialId serial_id,
    FuriHalSerialControlExpansionCallback callback,
    void* context) {
    if(serial_id >= FuriHalSerialIdMax || !furi_hal_serial_control) return false;
    FuriHalSerialControlMessageExpCallback message_input={
        .id=serial_id,.callback=callback,.context=context,
    };
    bool accepted=false;
    FuriHalSerialControlMessage message;
    message.type=FuriHalSerialControlMessageTypeExpansionSetCallback;
    message.api_lock=api_lock_alloc_locked();
    message.input=&message_input;
    message.output=&accepted;
    furi_message_queue_put(furi_hal_serial_control->queue,&message,FuriWaitForever);
    api_lock_wait_unlock_and_free(message.api_lock);
    return accepted;
}

/* ABI compatibility: internal clients can use bool TRY API for BUSY. */
void furi_hal_serial_control_set_expansion_callback(
    FuriHalSerialId serial_id,
    FuriHalSerialControlExpansionCallback callback,
    void* context) {
    if(!furi_hal_serial_control_try_set_expansion_callback(serial_id,callback,context)) {
        FURI_LOG_W(TAG,"Expansion IRQ registration BUSY");
    }
}""")
    pub=once(pub,
        "void furi_hal_serial_control_set_expansion_callback(",
        "/* E11: true only if native UART RX pin/EXTI is safely owned. */\n"
        "bool furi_hal_serial_control_try_set_expansion_callback(\n"
        "    FuriHalSerialId serial_id,\n"
        "    FuriHalSerialControlExpansionCallback callback,\n"
        "    void* context);\n"
        "void furi_hal_serial_control_set_expansion_callback(")
    api=once(api,
        'Function,+,furi_hal_serial_control_set_expansion_callback,void,"FuriHalSerialId, FuriHalSerialControlExpansionCallback, void*"\n',
        'Function,+,furi_hal_serial_control_set_expansion_callback,void,"FuriHalSerialId, FuriHalSerialControlExpansionCallback, void*"\n'
        'Function,+,furi_hal_serial_control_try_set_expansion_callback,_Bool,"FuriHalSerialId, FuriHalSerialControlExpansionCallback, void*"\n')
    return h,r,src,pub,api

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unpinned Momentum revision")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed native source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native input "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,SER,PUB,API)
        originals=[(root/x).read_text(encoding="utf-8") for x in paths]
        updated=patch(*originals)
        print("E11 NATIVE SERIAL USART1+LPUART1 EXPANSION EXACT SOURCE PREFLIGHT PASS")
        if a.apply:
            for name,value in zip(paths,updated):
                (root/name).write_text(value,encoding="utf-8")
            print("SOURCE ONLY; NO FLASH, DEVICE OR SD")
        else:
            print("READ ONLY; NO MODIFICATIONS")
        return 0
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print("E11 SERIAL SOURCE REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
