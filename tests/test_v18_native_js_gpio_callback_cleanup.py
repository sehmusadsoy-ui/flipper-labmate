#!/usr/bin/env python3
"""Execute original pinned patched native JS GPIO exact callback teardown C.

The helper itself is extracted from production C; verify both mode and
destructor call sites do not raw-disable, reset, or free on lost owner.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

HEAD=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
typedef struct {unsigned pin;} GpioPin;
typedef void (*GpioExtiCallback)(void*);
typedef struct {int id;} FuriSemaphore;
typedef struct {
 const GpioPin* pin;
 bool had_interrupt;
 FuriSemaphore* interrupt_semaphore;
 bool lease_fault;
} JsGpioPinInst;
static const GpioPin ext_pb2={2};
static FuriSemaphore semaphore={9};
static GpioExtiCallback current_callback;
static void* current_context;
static int attempts,register_mutations;
static void js_gpio_int_cb(void* arg) {(void)arg;}
static bool furi_hal_gpio_try_remove_int_callback(
 const GpioPin* pin,GpioExtiCallback cb,void* ctx) {
 assert(pin==&ext_pb2 && cb);attempts++;
 if(current_callback!=cb || current_context!=ctx) return false;
 current_callback=NULL;current_context=NULL;register_mutations++;
 return true;
}
"""
RUN=r"""
static void foreign(void* x) {(void)x;}
static void reset_state(void) {
 attempts=register_mutations=0;
 current_callback=NULL;current_context=NULL;
}
int main(void) {
 reset_state();
 JsGpioPinInst data={.pin=&ext_pb2,.interrupt_semaphore=&semaphore};
 assert(js_gpio_e11_try_remove_callback(&data));
 assert(!attempts && !register_mutations);
 data.had_interrupt=true;
 current_callback=js_gpio_int_cb;current_context=&semaphore;
 assert(js_gpio_e11_try_remove_callback(&data));
 assert(!data.had_interrupt && !current_callback && attempts==1 &&
        register_mutations==1 && !data.lease_fault);
 assert(js_gpio_e11_try_remove_callback(&data) && attempts==1);
 reset_state();
 data.had_interrupt=true;
 current_callback=foreign;current_context=(void*)1;
 assert(!js_gpio_e11_try_remove_callback(&data));
 assert(data.had_interrupt && data.lease_fault && attempts==1 &&
        register_mutations==0 && current_callback==foreign && current_context==(void*)1);
 assert(!js_gpio_e11_try_remove_callback(&data) && attempts==1);
 reset_state();data.lease_fault=false;data.had_interrupt=true;
 current_callback=js_gpio_int_cb;current_context=(void*)999;
 assert(!js_gpio_e11_try_remove_callback(&data));
 assert(data.lease_fault && data.had_interrupt && current_callback==js_gpio_int_cb);
 reset_state();data.lease_fault=false;data.had_interrupt=true;
 assert(!js_gpio_e11_try_remove_callback(&data) && data.lease_fault);
 assert(!js_gpio_e11_try_remove_callback(NULL));
 puts("E11 genuine native JS GPIO C: exact callback and ctx, denied STOP, sticky PASS");
 return 0;
}
"""
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    src=(root/"applications/system/js_app/modules/js_gpio.c").read_text()
    gpio=(root/"targets/f7/furi_hal/furi_hal_gpio.c").read_text()
    marker="/* E11 JS GPIO exact callback-and-semaphore owner cleanup. */"
    assert src.count(marker)==1
    assert src.count("js_gpio_e11_try_remove_callback(manager_data)")==2
    assert "furi_hal_gpio_remove_int_callback(manager_data->pin);" not in src
    assert "furi_hal_gpio_disable_int_callback(manager_data->pin);" not in src
    assert "furi_hal_gpio_try_remove_int_callback(" in gpio
    a=src.index(marker)
    b=src.index("static bool js_gpio_e11_claim(",a)
    helper=src[a:b]
    assert "furi_hal_gpio_try_remove_int_callback(" in helper
    assert helper.index("furi_hal_gpio_try_remove_int_callback(")<helper.index("data->had_interrupt=false;")
    mode=src[src.index("static void js_gpio_init("):src.index("static void js_gpio_write(")]
    assert "if(!js_gpio_e11_try_remove_callback(manager_data))" in mode
    assert mode.index('GPIO callback ownership lost')<mode.index("furi_hal_gpio_init(manager_data->pin, mode, pull")
    teardown=src[src.index("static void js_gpio_destroy("):]
    assert teardown.index("if(!js_gpio_e11_try_remove_callback(manager_data))") < teardown.index("if(manager_data->pwm_owned)")
    assert teardown.index("continue;")<teardown.index("furi_hal_gpio_init(")
    assert teardown.index("continue;")<teardown.index("furi_semaphore_free(manager_data->interrupt_semaphore)")
    with tempfile.TemporaryDirectory(prefix="e11_js_gpio_cb_") as directory:
        exe=Path(directory)/"test"
        f=Path(directory)/"actual.c"
        f.write_text(HEAD+"\n"+helper+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",str(f),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 original JS GPIO source callback C + mode/teardown denial HOST PASS")
    print("Native GPIO compare-remove C already independently compiled by OneWire gate")
    print("Physical JS GPIO teardown and system button callback coexistence OPEN")

if __name__=="__main__":
    main()
