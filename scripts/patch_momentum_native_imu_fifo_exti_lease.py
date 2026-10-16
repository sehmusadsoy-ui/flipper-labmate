#!/usr/bin/env python3
"""Native JS IMU FIFO PB2/EXTI2 E11 original C + worker BUSY handshake.

Preserve old void FIFO ABI; a real bool TRY_START and owned FIFO STOP make
JS IMU refusal visible. Pinned Momentum only, no flash/device/SD.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
from patch_momentum_native_wiegand_exti_lease import EXPECTED as W_PRE, H,R,W,WH,APP

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
DR="applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c"
DH="applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.h"
IMU="applications/system/js_app/modules/js_vgm/imu.c"
EXPECTED=W_PRE|{H,R,W,WH,APP}
MARK="/* E11 native IMU FIFO PB2+EXTI2 exact callback owner. */"

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned IMU original-C anchor mismatch "+repr(old[:120]))
    return s.replace(old,new,1)

def patch(src,header,imu):
    if MARK in src: raise ValueError("IMU FIFO owner already applied")
    src=once(src,
        "#include <furi_hal.h>\n",
        "#include <furi_hal.h>\n#include <furi_hal_resources.h>\n")
    src=once(src,
        """struct ICM42688P {
    FuriHalSpiBusHandle* spi_bus;
    const GpioPin* irq_pin;
    float accel_scale;
    float gyro_scale;
};""",
        """struct ICM42688P {
    FuriHalSpiBusHandle* spi_bus;
    const GpioPin* irq_pin;
    float accel_scale;
    float gyro_scale;
    /* E11 native IMU FIFO PB2+EXTI2 exact callback owner. */
    uint32_t e11_irq_owner;
    bool e11_irq_fault;
    ICM42688PIrqCallback e11_irq_callback;
    void* e11_irq_context;
};""")
    src=once(src,
        """void icm42688_fifo_enable(
    ICM42688P* icm42688p,
    ICM42688PIrqCallback irq_callback,
    void* irq_context) {
    // FIFO mode: stream""",
        """static void e11_imu_fifo_irq(void* ctx) {
    ICM42688P* sensor=ctx;
    if(!sensor || !sensor->e11_irq_owner || sensor->e11_irq_fault) return;
    if(sensor->e11_irq_callback)
        sensor->e11_irq_callback(sensor->e11_irq_context);
}

bool icm42688_fifo_try_enable(
    ICM42688P* icm42688p,
    ICM42688PIrqCallback irq_callback,
    void* irq_context) {
    if(!icm42688p || !irq_callback || icm42688p->e11_irq_owner ||
       icm42688p->e11_irq_fault) return false;
    /* The pinned in-firmware IMU uses EXTERNAL PB2. Any other pin needs
     * a separate exact physical+EXTI mask and may not steal EXTI.
     */
    if(icm42688p->irq_pin != &gpio_ext_pb2) return false;
    const uint32_t owner=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PB2);
    if(!owner) return false;
    icm42688p->e11_irq_owner=owner;
    icm42688p->e11_irq_callback=irq_callback;
    icm42688p->e11_irq_context=irq_context;
    /* Callback CAS before ANY IMU FIFO SPI register / PB2 mode changes.
     * Refuse occupied native NFC/CC1101 EXTI2 without replacing it.
     */
    if(!furi_hal_gpio_try_add_int_callback(
           icm42688p->irq_pin,e11_imu_fifo_irq,icm42688p)) {
        if(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_IRQ_PB2)) {
            icm42688p->e11_irq_owner=0U;
            icm42688p->e11_irq_callback=NULL;
            icm42688p->e11_irq_context=NULL;
        } else {
            icm42688p->e11_irq_fault=true;
        }
        return false;
    }
    // FIFO mode: stream""")
    src=once(src,
        """    furi_hal_gpio_init(icm42688p->irq_pin, GpioModeInterruptRise, GpioPullDown, GpioSpeedVeryHigh);
    furi_hal_gpio_remove_int_callback(icm42688p->irq_pin);
    furi_hal_gpio_add_int_callback(icm42688p->irq_pin, irq_callback, irq_context);""",
        """    furi_hal_gpio_init(icm42688p->irq_pin,GpioModeInterruptRise,GpioPullDown,GpioSpeedVeryHigh);""")
    src=once(src,
        """    icm42688p_write_reg(icm42688p->spi_bus, ICM42688_INT_SOURCE0, (1 << 2));
}

void icm42688_fifo_disable(ICM42688P* icm42688p) {
    furi_hal_gpio_remove_int_callback(icm42688p->irq_pin);
    furi_hal_gpio_init(icm42688p->irq_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);""",
        """    icm42688p_write_reg(icm42688p->spi_bus, ICM42688_INT_SOURCE0, (1 << 2));
    return true;
}

/* Keep the old published/local void interface for binary compatibility. */
void icm42688_fifo_enable(
    ICM42688P* icm42688p,ICM42688PIrqCallback irq_callback,void* irq_context) {
    (void)icm42688_fifo_try_enable(icm42688p,irq_callback,irq_context);
}

void icm42688_fifo_disable(ICM42688P* icm42688p) {
    if(!icm42688p || !icm42688p->e11_irq_owner || icm42688p->e11_irq_fault)
        return;
    if(!furi_hal_gpio_try_remove_int_callback(
           icm42688p->irq_pin,e11_imu_fifo_irq,icm42688p)) {
        icm42688p->e11_irq_fault=true;
        return;
    }
    furi_hal_gpio_init(icm42688p->irq_pin,GpioModeAnalog,GpioPullNo,GpioSpeedLow);""")
    src=once(src,
        """    icm42688p_write_reg(icm42688p->spi_bus, ICM42688_FIFO_CONFIG, 0);
}

uint16_t icm42688_fifo_get_count(""",
        """    icm42688p_write_reg(icm42688p->spi_bus, ICM42688_FIFO_CONFIG, 0);
    if(furi_hal_resource_lease_release(
           icm42688p->e11_irq_owner,FURI_HAL_LEASE_IRQ_PB2)) {
        icm42688p->e11_irq_owner=0U;
        icm42688p->e11_irq_callback=NULL;
        icm42688p->e11_irq_context=NULL;
    } else {
        icm42688p->e11_irq_fault=true; /* Failed release remains sticky. */
    }
}

uint16_t icm42688_fifo_get_count(""")
    src=once(src,
        """    icm42688p->spi_bus = spi_bus;
    icm42688p->irq_pin = irq_pin;
    return icm42688p;""",
        """    icm42688p->spi_bus = spi_bus;
    icm42688p->irq_pin = irq_pin;
    icm42688p->e11_irq_owner=0U;
    icm42688p->e11_irq_fault=false;
    icm42688p->e11_irq_callback=NULL;
    icm42688p->e11_irq_context=NULL;
    return icm42688p;""")
    src=once(src,
        """void icm42688p_free(ICM42688P* icm42688p) {
    free(icm42688p);
}""",
        """void icm42688p_free(ICM42688P* icm42688p) {
    /* A sticky leased callback must never point to freed sensor memory. */
    if(!icm42688p || icm42688p->e11_irq_owner) return;
    free(icm42688p);
}""")
    header=once(header,
        """void icm42688_fifo_enable(
    ICM42688P* icm42688p,
    ICM42688PIrqCallback irq_callback,
    void* irq_context);""",
        """void icm42688_fifo_enable(
    ICM42688P* icm42688p,
    ICM42688PIrqCallback irq_callback,
    void* irq_context);
/* E11: native IMU PB2+EXTI2 is owned only on true return. */
bool icm42688_fifo_try_enable(
    ICM42688P* icm42688p,
    ICM42688PIrqCallback irq_callback,
    void* irq_context);""")
    imu=once(imu,
        """    bool lefty;
} ImuThread;""",
        """    bool lefty;
    FuriSemaphore* e11_ready;
    bool e11_started;
} ImuThread;""")
    imu=once(imu,
        """    icm42688_fifo_enable(imu->icm42688p, imu_irq_callback, imu);

    while(1) {""",
        """    imu->e11_started=icm42688_fifo_try_enable(imu->icm42688p,imu_irq_callback,imu);
    furi_semaphore_release(imu->e11_ready); /* Always wake the starter. */
    if(!imu->e11_started) {
        FURI_LOG_W(TAG,"IMU FIFO PB2/EXTI2 resource BUSY");
        return 0; /* Do not wait or STOP another EXTI2 owner. */
    }

    while(1) {""")
    imu=once(imu,
        """    imu->thread = furi_thread_alloc_ex("ImuThread", 4096, imu_thread, imu);
    imu->lefty = furi_hal_rtc_is_flag_set(FuriHalRtcFlagHandOrient);
    furi_thread_start(imu->thread);

    return imu;""",
        """    imu->thread = furi_thread_alloc_ex("ImuThread", 4096, imu_thread, imu);
    imu->lefty = furi_hal_rtc_is_flag_set(FuriHalRtcFlagHandOrient);
    imu->e11_started=false;
    imu->e11_ready=furi_semaphore_alloc(1,0);
    furi_thread_start(imu->thread);
    /* Calibration and IRQ setup happen in the worker. Wait for a real
     * ownership result instead of reporting a false-positive sensor.
     */
    const FuriStatus ready=furi_semaphore_acquire(imu->e11_ready,2000);
    const bool success=(ready==FuriStatusOk && imu->e11_started);
    if(!success) {
        furi_thread_flags_set(furi_thread_get_id(imu->thread),ImuStop);
        furi_thread_join(imu->thread);
        furi_thread_free(imu->thread);
        furi_semaphore_free(imu->e11_ready);
        free(imu);
        return NULL;
    }
    furi_semaphore_free(imu->e11_ready);
    imu->e11_ready=NULL;
    return imu;""")
    imu=once(imu,
        """    if(imu->present) {
        imu->thread = imu_start(imu->icm42688p);
    }

    return imu;""",
        """    if(imu->present) {
        imu->thread=imu_start(imu->icm42688p);
        if(!imu->thread) imu->present=false; /* No false active IMU on BUSY. */
    }

    return imu;""")
    return src,header,imu

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Unpinned Momentum source")
        dirty=set()
        for ln in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed native source")
            dirty.add(ln[3:])
        if dirty!=EXPECTED: raise ValueError("Unreviewed previous source "+repr(sorted(dirty^EXPECTED)))
        paths=(DR,DH,IMU)
        before=[(root/p).read_text(encoding="utf-8") for p in paths]
        after=patch(*before)
        print("E11 NATIVE IMU FIFO PB2/EXTI2 SOURCE PREFLIGHT PASS")
        if a.apply:
            for p,s in zip(paths,after): (root/p).write_text(s,encoding="utf-8")
            print("PATCHED ORIGINAL JS IMU C ONLY, NO FLASH")
        else: print("READ ONLY")
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print("E11 IMU FIFO SOURCE REFUSED: "+str(e));raise SystemExit(1)

if __name__=="__main__": main()
