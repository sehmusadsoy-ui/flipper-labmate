/* Native Button/Counter STOP bodies are extracted verbatim by the runner. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
/* Link the REAL pure-C snapshot/store implementations below. A mocked
 * publication API would make the new Counter STOP safety gate meaningless.
 */
#include "labmate_dashboard_store.h"
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
#define GPIO_COUNT 8U
#define FURI_HAL_LEASE_IRQ_PC1 0x100U
#define GpioModeAnalog 4

typedef struct { int pin; } GpioPin;
static GpioPin pin={1};
static const GpioPin* labmate_gpio_pins[GPIO_COUNT]={&pin,&pin,&pin,&pin,&pin,&pin,&pin,&pin};
typedef enum {LabMateCaptureNone=0, LabMateCaptureCounter, LabMateCaptureButton} LabMateCaptureOwner;
typedef struct {
    bool counter_active,button_active,capture_release_fault,capture_blocked;
    LabMateCaptureOwner capture_owner;
    uint8_t capture_pin_index;
    uint64_t counter_elapsed_ticks, counter_total, counter_run_start_total;
    uint32_t counter_start_tick, counter_elapsed_seconds;
    uint32_t counter_run_generation, counter_run_tick_hz;
    LabMateDashboardStore doctor_store;
} LabMateApp;
static uint32_t labmate_button_lease_handle;
static bool release_ok,tim2_pending,tim2_healthy;
static unsigned releases,disable_irq,disable_tim2;
static LabMateCaptureOwner labmate_capture_owner_after_stop(LabMateCaptureOwner cur,LabMateCaptureOwner stop){return cur==stop?LabMateCaptureNone:cur;}
static void furi_hal_gpio_disable_int_callback(const GpioPin* p){assert(p);disable_irq++;}
static void furi_hal_gpio_remove_int_callback(const GpioPin* p){assert(p);}
static void labmate_capture_exti_clear(uint32_t line,bool active){assert(line && active);}
static void furi_hal_gpio_init_simple(const GpioPin* p,int mode){assert(p && mode==GpioModeAnalog);}
static bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask){assert(handle && mask);releases++;return release_ok;}
static bool labmate_frequency_tim2_capture_valid(void){return tim2_healthy;}
static void labmate_frequency_tim2_disable(void){disable_tim2++;}
static void labmate_event_counter_poll(LabMateApp* a){assert(a);}
static uint64_t labmate_counter_add_ticks(uint64_t a,uint32_t b){return a+b;}
static uint32_t furi_get_tick(void){return 200U;}
static uint32_t furi_kernel_get_tick_frequency(void){return 100U;}
static uint32_t labmate_counter_elapsed_seconds(uint64_t ticks,uint32_t hz){return (uint32_t)(ticks/hz);}
static void labmate_frequency_tim2_shutdown(void){if(release_ok)tim2_pending=false;}
static bool labmate_frequency_tim2_lease_pending(void){return tim2_pending;}
#include "counter_stop.inc"
#include "button_stop.inc"
static void reset(void){release_ok=true;tim2_pending=false;tim2_healthy=true;releases=0;disable_irq=0;disable_tim2=0;labmate_button_lease_handle=0;}
int main(void){
    unsigned n=0;LabMateApp a;
    reset();a=(LabMateApp){.counter_active=true,.capture_owner=LabMateCaptureCounter,.capture_pin_index=4,.counter_start_tick=100};tim2_pending=true;
    labmate_event_counter_stop(&a);
    assert(!a.counter_active && a.capture_owner==LabMateCaptureNone && a.capture_pin_index==GPIO_COUNT && !a.capture_release_fault);
    assert(disable_tim2==1 && a.counter_elapsed_ticks==100 && !tim2_pending);n++;
    reset();a=(LabMateApp){.counter_active=true,.capture_owner=LabMateCaptureCounter,.capture_pin_index=4};tim2_pending=true;release_ok=false;
    labmate_event_counter_stop(&a);
    assert(!a.counter_active && a.capture_owner==LabMateCaptureCounter && a.capture_pin_index==4);
    assert(a.capture_release_fault && a.capture_blocked && tim2_pending);n++;
    reset();a=(LabMateApp){.counter_active=true,.capture_owner=LabMateCaptureCounter,.capture_pin_index=4};tim2_pending=true;tim2_healthy=false;
    labmate_event_counter_stop(&a);
    assert(a.capture_owner==LabMateCaptureCounter && a.capture_release_fault && a.capture_blocked && !disable_tim2);n++;
    reset();a=(LabMateApp){.button_active=true,.capture_owner=LabMateCaptureButton,.capture_pin_index=1};labmate_button_lease_handle=22;
    labmate_button_capture_stop(&a);
    assert(!a.button_active && a.capture_owner==LabMateCaptureNone && a.capture_pin_index==GPIO_COUNT);
    assert(labmate_button_lease_handle==0 && releases==1 && disable_irq==1);n++;
    reset();a=(LabMateApp){.button_active=true,.capture_owner=LabMateCaptureButton,.capture_pin_index=1};labmate_button_lease_handle=22;release_ok=false;
    labmate_button_capture_stop(&a);
    assert(!a.button_active && a.capture_owner==LabMateCaptureButton && a.capture_pin_index==1);
    assert(a.capture_release_fault && a.capture_blocked && labmate_button_lease_handle==22);n++;
    reset();a=(LabMateApp){.button_active=true,.capture_owner=LabMateCaptureButton,.capture_pin_index=1};
    labmate_button_capture_stop(&a);
    assert(a.button_active && a.capture_owner==LabMateCaptureButton && a.capture_blocked);
    assert(!disable_irq && !releases);n++;
    /* Positive: exact production Counter STOP must publish 43 real edges
     * ONLY after a fully healthy TIM2 stop and returned native lease.
     * Final TIM2 poll stub is a no-op, so the total is pre-observed.
     */
    reset();
    a=(LabMateApp){
        .counter_active=true,.capture_owner=LabMateCaptureCounter,
        .capture_pin_index=4,.counter_start_tick=100,
        .counter_run_generation=1,.counter_run_tick_hz=100,
        .counter_total=61,.counter_run_start_total=18,
    };
    tim2_pending=true;
    labmate_event_counter_stop(&a);
    LabMateSnapshotV1 snap={0};
    assert(!tim2_pending && !a.counter_active &&
           a.capture_owner==LabMateCaptureNone);
    assert(labmate_dashboard_store_read_measurement(
        &a.doctor_store,LabMateSnapshotCounter,&snap));
    assert(snap.capture_generation==1 && snap.source==LabMateSnapshotCounter &&
           snap.pin_index==4 && snap.valid_sample_count==43 &&
           snap.observed_edge_count==43 && snap.ownership_released);
    n++;

    /* Zero edges are not valid numerical evidence; no fake "NO SIGNAL". */
    reset();
    a=(LabMateApp){
        .counter_active=true,.capture_owner=LabMateCaptureCounter,
        .capture_pin_index=4,.counter_start_tick=100,
        .counter_run_generation=2,.counter_run_tick_hz=100,
        .counter_total=18,.counter_run_start_total=18,
    };
    tim2_pending=true;
    labmate_event_counter_stop(&a);
    assert(a.doctor_store.slots[LabMateSnapshotCounter].has_snapshot);
    assert(labmate_dashboard_store_quality(
        &a.doctor_store,LabMateSnapshotCounter)==LabMateSnapshotInsufficient);
    assert(!labmate_dashboard_store_read_measurement(
        &a.doctor_store,LabMateSnapshotCounter,&snap));
    n++;

    /* An unreturned lease MUST NEVER make numerical evidence. */
    reset();
    a=(LabMateApp){
        .counter_active=true,.capture_owner=LabMateCaptureCounter,
        .capture_pin_index=4,.counter_start_tick=100,
        .counter_run_generation=3,.counter_run_tick_hz=100,
        .counter_total=61,.counter_run_start_total=18,
    };
    tim2_pending=true;release_ok=false;
    labmate_event_counter_stop(&a);
    assert(a.capture_release_fault && a.capture_owner==LabMateCaptureCounter);
    assert(!a.doctor_store.slots[LabMateSnapshotCounter].has_snapshot);
    n++;

    /* A changed timebase invalidates the interval: fail closed. */
    reset();
    a=(LabMateApp){
        .counter_active=true,.capture_owner=LabMateCaptureCounter,
        .capture_pin_index=4,.counter_start_tick=100,
        .counter_run_generation=4,.counter_run_tick_hz=101,
        .counter_total=61,.counter_run_start_total=18,
    };
    tim2_pending=true;
    labmate_event_counter_stop(&a);
    assert(a.capture_owner==LabMateCaptureNone);
    assert(!a.doctor_store.slots[LabMateSnapshotCounter].has_snapshot);
    n++;

    printf("Phase2K extracted Button/Counter STOP PASS: %u release and sealed-evidence scenarios\n",n);
    return n==10?0:1;
}
