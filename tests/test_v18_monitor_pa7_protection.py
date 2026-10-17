#!/usr/bin/env python3
"""E11 Monitor all eight pin leases: execute ACTUAL production monitor C.
Host-only mock; independent native firmware GPIO services are NOT migrated.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/labmate_monitor_gpio.c"
MOCK=r"""
#ifndef E11_GPIO_MONITOR_TEST_H
#define E11_GPIO_MONITOR_TEST_H
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define GPIO_COUNT 8U
#define GpioModeAnalog 0
#define GpioModeInput 1
#ifdef TEST_API
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_MONITOR_PC0 (1U<<5)
#define FURI_HAL_LEASE_MONITOR_PC1 (1U<<7)
#define FURI_HAL_LEASE_MONITOR_PC3 (1U<<14)
#define FURI_HAL_LEASE_MONITOR_PB2 (1U<<9)
#define FURI_HAL_LEASE_MONITOR_PB3 (1U<<3)
#define FURI_HAL_LEASE_MONITOR_PA4 (1U<<11)
#define FURI_HAL_LEASE_MONITOR_PA6 (1U<<15)
#define FURI_HAL_LEASE_MONITOR_PA7 (1U<<1)
#endif
typedef struct {uint8_t index;} GpioPin;
typedef struct {
    uint8_t gpio_index;
    bool generator_running,generator_blocked,generator_release_fault;
    bool monitor_active,monitor_blocked,monitor_release_fault;
    bool gpio_state,gpio_previous_state;
} LabMateApp;
extern const GpioPin* const labmate_gpio_pins[GPIO_COUNT];
extern unsigned writes,reads,claims,releases;
extern bool lease_available,release_ok;
extern uint32_t last_mask;
bool labmate_monitor_pin_allowed(uint8_t index,bool reserved);
uint8_t labmate_monitor_entry_pin(uint8_t index,bool reserved);
void furi_hal_gpio_init_simple(const GpioPin* pin,int mode);
bool furi_hal_gpio_read(const GpioPin* pin);
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask);
#endif
"""
HARNESS=r"""
#include <assert.h>
#include "mock.h"
unsigned writes,reads,claims,releases;
bool lease_available,release_ok=true;
uint32_t last_mask;
static const GpioPin pins[GPIO_COUNT]={{0},{1},{2},{3},{4},{5},{6},{7}};
const GpioPin* const labmate_gpio_pins[GPIO_COUNT]={
    &pins[0],&pins[1],&pins[2],&pins[3],
    &pins[4],&pins[5],&pins[6],&pins[7]
};
bool labmate_monitor_pin_allowed(uint8_t n,bool reserved) {
    return n<GPIO_COUNT && !(reserved&&n==7U);
}
uint8_t labmate_monitor_entry_pin(uint8_t n,bool reserved) {
    return labmate_monitor_pin_allowed(n,reserved)?n:1U;
}
static const uint32_t masks[GPIO_COUNT]={
    1U<<5,1U<<7,1U<<14,1U<<9,1U<<3,1U<<11,1U<<15,1U<<1
};
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask!=0U);
    claims++;
    last_mask=mask;
    return lease_available?91U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
    assert(h==91U && mask==last_mask);
    releases++;
    return release_ok;
}
void furi_hal_gpio_init_simple(const GpioPin* pin,int mode) {
    assert(pin && pin->index<GPIO_COUNT);
    assert(mode==GpioModeInput || mode==GpioModeAnalog);
    writes++;
}
bool furi_hal_gpio_read(const GpioPin* pin) {
    assert(pin && pin->index<GPIO_COUNT);
    reads++;
    return true;
}
#include "labmate_monitor_gpio.c"
int main(void) {
    (void)masks; /* stock SDK retains mock mapping without leasing */
    LabMateApp app={.gpio_index=0U};
    bool level=false;
    /* Missing API or denied lease must not modify input, analog or read. */
    labmate_monitor_gpio_activate(&app);
    assert(app.monitor_blocked && !app.monitor_active);
    assert(writes==0U && reads==0U);
    assert(!labmate_monitor_gpio_read(&app,0U,&level));
    assert(!level);
    labmate_monitor_gpio_release(&app,0U);
    assert(writes==0U && releases==0U);
#ifdef TEST_API
    assert(claims==1U && last_mask==masks[0]);
    lease_available=true;
    /* Exercise every real pin mapping and repeated claim/release. */
    for(uint8_t i=0U;i<GPIO_COUNT;++i) {
        app.gpio_index=i;
        /* Every mapped connector pin must fail without GPIO mutation
         * if another firmware owner holds that exact physical resource.
         * A rejected START must not arm a sample or perform a cleanup.
         */
        lease_available=false;
        const unsigned denied_writes=writes, denied_reads=reads;
        const unsigned denied_claims=claims, denied_releases=releases;
        level=false;
        labmate_monitor_gpio_activate(&app);
        assert(app.monitor_blocked && !app.monitor_active);
        assert(last_mask==masks[i] && claims==denied_claims+1U);
        assert(writes==denied_writes && reads==denied_reads);
        assert(!labmate_monitor_gpio_read(&app,i,&level) && !level);
        labmate_monitor_gpio_release(&app,i);
        assert(writes==denied_writes && releases==denied_releases);
        lease_available=true;
        labmate_monitor_gpio_activate(&app);
        assert(app.monitor_active && !app.monitor_blocked &&
               app.gpio_index==i && last_mask==masks[i]);
        assert(labmate_monitor_gpio_read(&app,i,&level) && level);
        unsigned w=writes, n=reads, attempts=claims;
        labmate_monitor_gpio_activate(&app); /* cannot take second lease */
        assert(app.monitor_blocked && writes==w && reads==n && claims==attempts);
        assert(!labmate_monitor_gpio_read(&app,i,&level));
        /* Wrong index must not teardown another pinned owner. */
        labmate_monitor_gpio_release(&app,(uint8_t)((i+1U)%GPIO_COUNT));
        assert(writes==w);
        labmate_monitor_gpio_release(&app,i);
        assert(!app.monitor_active && releases==(unsigned)i+1U);
        assert(writes==w+1U);
        app.monitor_blocked=false;
    }
    /* A denied PWM claim locally excludes PA7 before trying monitor mask. */
    unsigned w=writes,n=claims;
    app.gpio_index=7U;
    app.generator_blocked=true;
    labmate_monitor_gpio_activate(&app);
    assert(app.gpio_index==1U && last_mask==masks[1]);
    assert(writes==w+1U && claims==n+1U);
    labmate_monitor_gpio_release(&app,1U);
    app.generator_blocked=false;
    /* Failed RELEASE retains the opaque handle, forbids any other pin. */
    app.gpio_index=5U;
    release_ok=false;
    labmate_monitor_gpio_activate(&app);
    assert(app.monitor_active);
    labmate_monitor_gpio_release(&app,5U);
    assert(app.monitor_release_fault && app.monitor_blocked &&
           !app.monitor_active);
    w=writes;n=claims;
    app.gpio_index=0U;
    labmate_monitor_gpio_activate(&app);
    assert(!app.monitor_active && app.monitor_blocked);
    assert(writes==w && claims==n);
    assert(!labmate_monitor_gpio_read(&app,5U,&level));
#else
    assert(claims==0U && releases==0U);
    lease_available=true;
    app.gpio_index=7U;
    labmate_monitor_gpio_activate(&app);
    assert(app.monitor_blocked && writes==0U && reads==0U);
#endif
    assert(!labmate_monitor_gpio_read(&app,GPIO_COUNT,&level));
    assert(!labmate_monitor_gpio_read(&app,0U,NULL));
    return 0;
}
"""

def run(with_api: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="labmate_e11_monitor_") as d:
        root=Path(d)
        (root/"mock.h").write_text(MOCK)
        for h in ("labmate_monitor_gpio.h","labmate_capture_core.h",
                  "labmate_resource_policy.h","furi_hal.h","furi_hal_resources.h"):
            (root/h).write_text('#include "mock.h"\n')
        shutil.copy2(SOURCE,root/SOURCE.name)
        (root/"harness.c").write_text(HARNESS)
        exe=root/"run"
        args=[os.environ.get("CC","cc"),"-std=c11","-Wall","-Wextra",
              "-Werror","-pedantic","-O0","-I",str(root)]
        if with_api: args.append("-DTEST_API=1")
        subprocess.run(args+[str(root/"harness.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

def main() -> None:
    code=SOURCE.read_text()
    assert code.index("furi_hal_resource_lease_try_acquire(mask)") < code.index(
        "furi_hal_gpio_init_simple(pin, GpioModeInput)")
    assert "app->monitor_release_fault = true;" in code
    assert "app->generator_running || app->generator_blocked" in code
    assert "app->generator_release_fault;" in code
    session=(ROOT/"src/labmate_capture_session.c").read_text()
    assert "app->generator_running || app->generator_blocked" in session
    assert "app->generator_release_fault" in session
    run(False)
    run(True)
    print("E11 MONITOR 8/8 ACTUAL C DRIVER HOST PASS:")
    print("stock SDK / denied claim: zero GPIO/read mutations; all 8 masks")
    print("claim, pin-only reads, wrong-pin STOP, BUSY, failed release block.")
    print("NOT mandatory GPIO ownership in independent Momentum services.")

if __name__=="__main__":
    main()
