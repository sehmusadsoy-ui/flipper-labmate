#!/usr/bin/env python3
"""E11 H1 no-device cooperative PA7 overlap: REAL patched JS claim + PWM HAL + LabMate C.

Runs the EXACT js_gpio_e11_claim and js_gpio_e11_monitor_mask helper bodies
extracted from the pinned patched Momentum C file alongside the *real*
native PWM HAL and LabMate generator C in one stubbed process. A user-mode
test cannot assert this ran on the Flipper or that arbitrary legacy apps obey.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JOINT_FILE = ROOT / "tests/test_v18_pwm_native_joint.py"
NATIVE_FILE = ROOT / "tests/test_v18_native_pwm_lease.py"
APP_FILE = ROOT / "src/labmate_generator.c"
JS_FILE = "applications/system/js_app/modules/js_gpio.c"
PWM_FILE = "targets/f7/furi_hal/furi_hal_pwm.c"
PIN = "d3f89dfe2ef6b01839201598e9be1590cba80322"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


JS_HEADER = r"""
/* Only PA7 is acquired. Other monitored pins are referenced by the
 * exact native JS pin-mask helper but never modified in this test.
 */
extern const GpioPin gpio_ext_pc0, gpio_ext_pc1, gpio_ext_pc3;
extern const GpioPin gpio_ext_pb2, gpio_ext_pb3, gpio_ext_pa6;
#define FURI_HAL_LEASE_MONITOR_PC0 (1U<<5)
#define FURI_HAL_LEASE_MONITOR_PC1 (1U<<6)
#define FURI_HAL_LEASE_MONITOR_PC3 (1U<<7)
#define FURI_HAL_LEASE_MONITOR_PB2 (1U<<8)
#define FURI_HAL_LEASE_MONITOR_PB3 (1U<<9)
#define FURI_HAL_LEASE_MONITOR_PA6 (1U<<10)
typedef struct {
    const GpioPin* pin;
    FuriHalPwmOutputId pwm_output;
    uint32_t lease_handle, lease_mask;
    uint32_t exti_lease_handle, exti_lease_mask;
    bool lease_fault, configured, pwm_owned;
} JsGpioPinInst;
"""

JS_RUN = r"""
#include "mock_hal.h"
#include <stdio.h>
const GpioPin gpio_ext_pc0 = {10},gpio_ext_pc1 = {11},gpio_ext_pc3 = {13};
const GpioPin gpio_ext_pb2 = {22},gpio_ext_pb3 = {23},gpio_ext_pa6 = {6};
bool labmate_pwm_settings_valid(uint32_t hz,uint8_t duty) {
    return hz>=1U && hz<=50000U && duty>=5U && duty<=95U;
}
uint8_t labmate_pwm_adjust_duty(uint8_t duty,int8_t dir) {
    return (uint8_t)(duty+(dir>0?1:-1));
}
uint32_t labmate_pwm_adjust_hz(uint32_t hz,int8_t dir,uint32_t step) {
    return dir>0?hz+step:hz-step;
}
#define CHECK(x) do { if(!(x)) {fprintf(stderr,"E11 H1 JOINT HOST FAIL line %d: %s\n",__LINE__,#x);abort();} } while(0)
"""
TEST_RUN = r"""
int main(void) {
    LabMateApp app={.generator_freq_index=6,.generator_duty_percent=50,
                    .generator_custom_hz=1000};
    JsGpioPinInst js={.pin=&gpio_ext_pa7,.pwm_output=FuriHalPwmOutputIdTim1PA7};
    CHECK(js_gpio_e11_monitor_mask(&gpio_ext_pa7)==FURI_HAL_LEASE_MONITOR_PA7);

    /* H1 software-model producer: actual LabMate start routes through
     * the real native PWM C owner, not an independent fake boolean. */
    labmate_generator_start(&app);
    CHECK(app.generator_running && !app.generator_blocked);
    CHECK(furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    CHECK((used & FURI_HAL_LEASE_PWM_PA7)==FURI_HAL_LEASE_PWM_PA7);
    unsigned gpio_before=gpio_changes,bus_before=bus_changes, ll_before=mock_ll_writes;
    unsigned claims_before=lease_claims;
    CHECK(!js_gpio_e11_claim(&js));
    CHECK(js.lease_handle==0U && !js.configured);
    CHECK(js.lease_mask==0U);
    CHECK(used==FURI_HAL_LEASE_PWM_PA7);
    CHECK(gpio_changes==gpio_before && bus_changes==bus_before);
    CHECK(mock_ll_writes==ll_before);
    CHECK(lease_claims==claims_before); /* checked running PWM before requesting pin */

    /* The first client's running output is still live; foreign JS may
     * neither acquire PA7 nor retune/stop it. Explicit owner STOP only.
     */
    CHECK(app.generator_running && furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    labmate_generator_stop(&app);
    CHECK(!app.generator_running && !app.generator_release_fault);
    CHECK(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    CHECK(used==0U);

    /* H2 modeled JS reuse, read claim after native HAL really stopped. */
    CHECK(js_gpio_e11_claim(&js));
    CHECK(js.lease_handle && js.lease_mask==FURI_HAL_LEASE_MONITOR_PA7);
    CHECK(used==FURI_HAL_LEASE_MONITOR_PA7);
    gpio_before=gpio_changes;bus_before=bus_changes;ll_before=mock_ll_writes;
    labmate_generator_start(&app); /* JS owns physical pin: native PWM denied */
    CHECK(!app.generator_running && app.generator_blocked);
    CHECK(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    CHECK(gpio_changes==gpio_before && bus_changes==bus_before);
    CHECK(mock_ll_writes==ll_before);
    CHECK(used==FURI_HAL_LEASE_MONITOR_PA7);

    CHECK(furi_hal_resource_lease_release(js.lease_handle,js.lease_mask));
    js.lease_handle=0U;js.lease_mask=0U;
    CHECK(used==0U);
    labmate_generator_start(&app);
    CHECK(app.generator_running && furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    labmate_generator_stop(&app);
    CHECK(!app.generator_running && used==0U);

    puts("E11 H1 COOPERATIVE PWM+JS JOINT ORIGINAL-C HOST PASS");
    puts("NOT native JS CLI execution on device, not live second-client BUSY evidence.");
    return 0;
}
"""


def extract_js_claim(js_source: str) -> str:
    marker = "/* LabMate E11 native JS GPIO connector-owner contract. */"
    if js_source.count(marker) != 1:
        raise ValueError("patched native JS source provenance missing/ambiguous")
    # Extract ONLY original, unchanged pin-mask + claim function bodies.
    first = js_source.index("static uint32_t js_gpio_e11_monitor_mask(", js_source.index(marker))
    mid = js_source.index("static uint32_t js_gpio_e11_exti_mask(", first)
    second = js_source.index("static bool js_gpio_e11_claim(JsGpioPinInst* manager_data)", mid)
    end = js_source.index("ARRAY_DEF(ManagedPinsArray", second)
    pin_mask = js_source[first:mid].split("/* The first actual GPIO operation claims", 1)[0]
    claim = js_source[second:end]
    if claim.count("furi_hal_resource_lease_try_acquire(mask)") != 1:
        raise ValueError("JS native claim primitive missing")
    if "furi_hal_pwm_is_running(manager_data->pwm_output)" not in claim:
        raise ValueError("native JS no longer checks running PWM before GPIO access")
    read_start = js_source.index("static void js_gpio_read(")
    read_end = js_source.index("static void js_gpio_interrupt(", read_start)
    read = js_source[read_start:read_end]
    if not (read.index("js_gpio_e11_claim(manager_data)") <
            read.index("furi_hal_gpio_read(manager_data->pin)")):
        raise ValueError("native JS read does not claim before GPIO hardware access")
    return pin_mask + "\n" + claim


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("momentum_root", type=Path)
    args=parser.parse_args()
    root=args.momentum_root
    native = (root/PWM_FILE).read_text()
    js = (root/JS_FILE).read_text()
    resources=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    # The stock Momentum CLI JS command is not ParallelSafe: do not mistake
    # loader rejection for a live native GPIO lease BUSY refusal.
    js_cli=(root/"applications/system/js_app/js_app.c").read_text()
    flags=(root/"lib/toolbox/cli/cli_command.h").read_text()
    shell=(root/"lib/toolbox/cli/shell/cli_shell.c").read_text()
    if "CLI_COMMAND_INTERFACE(js, js_cli_execute, CliCommandFlagDefault" not in js_cli:
        raise ValueError("pinned native JS CLI app concurrency flag has changed; review H1")
    if "CliCommandFlagDefault = 0" not in flags or "CliCommandFlagParallelSafe = (1 << 0)" not in flags:
        raise ValueError("pinned native JS CLI safety flag contract changed")
    lock=shell.index("if(!(command_data.flags & CliCommandFlagParallelSafe))")
    claim=shell.index("loader_locked = loader_lock(loader)", lock)
    refusal=shell.index("this command cannot be run while an application is open",claim)
    dispatch=shell.index("command_data.execute_callback(", refusal)
    if not lock < claim < refusal < dispatch:
        raise ValueError("pinned CLI loader-lock refusal no longer precedes command dispatch")
    # The built-in gpio CLI is no better as an H1 contender: it too
    # requires an exclusive loader, and its plain read bypasses
    # the native cooperative resource-lease API entirely.
    gpio_cli=(root/"applications/services/cli/cli_main_commands.c").read_text()
    gpio_impl=(root/"applications/services/cli/cli_command_gpio.c").read_text()
    if "CLI_COMMAND_INTERFACE(gpio, cli_command_gpio, CliCommandFlagDefault" not in gpio_cli:
        raise ValueError("pinned GPIO CLI concurrency flag changed; review required")
    if "LL_GPIO_GetPinMode(" not in gpio_impl or "furi_hal_gpio_read(" not in gpio_impl:
        raise ValueError("native gpio CLI read path changed; review required")
    gpio_read=gpio_impl[gpio_impl.index("void cli_command_gpio_read("):
                        gpio_impl.index("void cli_command_gpio_set(")]
    if "furi_hal_resource_lease_try_acquire" in gpio_read:
        raise ValueError("GPIO CLI lease semantics changed; existing H1 limitation needs review")
    if not ("LL_GPIO_GetPinMode(" in gpio_read and "furi_hal_gpio_read(" in gpio_read):
        raise ValueError("GPIO CLI read path no longer matches audit")
    if "furi_hal_gpio_init_simple(" not in gpio_impl or "furi_hal_gpio_write(" not in gpio_impl:
        raise ValueError("GPIO CLI mode/set hazard audit source changed")
    if "native_pwm_try_claim" not in native or "FURI_HAL_PWM_NATIVE_LEASE_API_V1" not in resources:
        raise ValueError("native PWM lease firmware source not patched")
    if "labmate_pwm_pa7_lease_handle" in APP_FILE.read_text():
        raise ValueError("LabMate double-claim regression")
    from_native=load(NATIVE_FILE,"native_pwm_original_c")
    joint=load(JOINT_FILE,"joint_pwm_original_c")
    stubs=from_native.HOST.replace("int main(void){","int old_native_suite_not_run(void){")
    if stubs==from_native.HOST:
        raise ValueError("native host translation-unit main anchor changed")
    helper=extract_js_claim(js)
    calls=set(re.findall(r"\b(LL_[A-Za-z0-9_]+)\s*\(",native))
    constants=set(re.findall(r"\b(LL_[A-Z0-9_]+)\b",native))-calls
    defs="\n".join(f"#define {name}(...) do {{mock_ll_writes++;}} while(0)" for name in sorted(calls))
    defs+="\n"+"\n".join(f"#define {name} 1U" for name in sorted(constants))
    with tempfile.TemporaryDirectory(prefix="e11_h1_host_no_device_") as temp:
        target=Path(temp)
        (target/"mock_hal.h").write_text(joint.HEADER+"\n"+JS_HEADER+"\n"+defs)
        for header in ("labmate_generator.h","furi_hal_pwm.h","furi_hal_resources.h",
                       "furi_hal_bus.h","stm32wbxx_ll_tim.h","stm32wbxx_ll_lptim.h",
                       "stm32wbxx_ll_rcc.h","furi.h"):
            (target/header).write_text('#include "mock_hal.h"\n')
        (target/"native_pwm.c").write_text(native)
        (target/"labmate_generator.c").write_text(APP_FILE.read_text())
        # Native HAL stub-private counters must live in the SAME C unit as
        # the original JS claim so H1 asserts shared ownership state.
        (target/"joint.c").write_text(stubs+"\n"+JS_RUN+helper+"\n"+TEST_RUN)
        exe=target/"joint"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-Wno-unused-variable","-I",str(target),
                        str(target/"native_pwm.c"),str(target/"labmate_generator.c"),
                        str(target/"joint.c"),
                        "-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)


if __name__ == "__main__":
    main()
