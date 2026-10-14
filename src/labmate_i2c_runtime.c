#include "labmate_i2c_runtime.h"
#include "labmate_i2c_momentum.h"
#include "labmate_i2c_session.h"
#include <furi.h>
#include <stdlib.h>
#include <string.h>

/* On-device bounded scanning worker: the GUI is never blocked by 112
 * sequential HAL probes. Stop/exit JOIN is safe only because the custom
 * HAL contract guarantees bounded acquire and probe calls.
 */
struct LabMateI2cRuntime {
    FuriThread* worker;
    FuriMutex* mutex;
    LabMateCommOwner* owner;
    LabMateI2cControl model;
    bool finished;
    bool stop_requested;
    LabMateI2cRuntimeStatus status;
};

static bool labmate_i2c_runtime_stop_requested(void* context) {
    LabMateI2cRuntime* s = context;
    if(furi_mutex_acquire(s->mutex, FuriWaitForever) != FuriStatusOk)
        return true;
    const bool stop = s->stop_requested;
    furi_mutex_release(s->mutex);
    return stop;
}

static int32_t labmate_i2c_runtime_worker(void* context) {
    LabMateI2cRuntime* s = context;
    LabMateI2cControl model;
    labmate_i2c_control_reset(&model);
    LabMateI2cMomentum bridge = {
        .stop_context = s,
        .stop_requested = labmate_i2c_runtime_stop_requested,
    };
    const LabMateI2cSessionOps ops = labmate_i2c_momentum_ops(&bridge);
    (void)labmate_i2c_session_execute(&model, &ops);
    /* The worker never acquires the LabMate UI mutex. Model publishing and
     * STOP flag checks use only this separate runtime mutex.
     */
    furi_mutex_acquire(s->mutex, FuriWaitForever);
    s->model = model;
    s->finished = true;
    furi_mutex_release(s->mutex);
    return 0;
}

LabMateI2cRuntime* labmate_i2c_runtime_alloc(void) {
    LabMateI2cRuntime* s = calloc(1U, sizeof(*s));
    if(!s) return NULL;
    s->mutex = furi_mutex_alloc(FuriMutexTypeNormal);
    if(!s->mutex) {
        free(s);
        return NULL;
    }
    labmate_i2c_control_reset(&s->model);
    s->status = labmate_i2c_momentum_available() ?
        LabMateI2cRuntimeReady : LabMateI2cRuntimeApiMissing;
    return s;
}

/* Complete a terminated worker and drop OUR application-local claim. */
static void labmate_i2c_runtime_reap(LabMateI2cRuntime* s) {
    if(!s || !s->worker) return;
    furi_thread_join(s->worker);
    furi_thread_free(s->worker);
    s->worker = NULL;
    if(s->owner) {
        (void)labmate_comm_local_release(s->owner, LabMateCommI2c3);
        s->owner = NULL;
    }
    if(s->model.state == LabMateI2cControlFinished)
        s->status = s->model.scan.total_found > 0U ?
            LabMateI2cRuntimeResults : LabMateI2cRuntimeNoDevices;
    else if(s->model.state == LabMateI2cControlCancelled)
        s->status = LabMateI2cRuntimeCancelled;
    else
        s->status = LabMateI2cRuntimeFailed;
}

void labmate_i2c_runtime_poll(LabMateI2cRuntime* s) {
    if(!s || !s->worker) return;
    furi_mutex_acquire(s->mutex, FuriWaitForever);
    const bool finished = s->finished;
    furi_mutex_release(s->mutex);
    if(finished) labmate_i2c_runtime_reap(s);
}

bool labmate_i2c_runtime_start(
    LabMateI2cRuntime* s, LabMateCommOwner* owner, LabMateCommBusy busy) {
    if(!s || !owner) return false;
    labmate_i2c_runtime_poll(s);
    if(s->worker) return false;
    if(!labmate_i2c_momentum_available()) {
        s->status = LabMateI2cRuntimeApiMissing;
        return false;
    }
    if(!labmate_comm_local_claim(owner, LabMateCommI2c3, busy)) {
        s->status = LabMateI2cRuntimeBusy;
        return false;
    }
    s->owner = owner;
    furi_mutex_acquire(s->mutex, FuriWaitForever);
    s->finished = false;
    s->stop_requested = false;
    labmate_i2c_control_reset(&s->model);
    furi_mutex_release(s->mutex);

    s->worker =
        furi_thread_alloc_ex("LabMateI2C", 2048U, labmate_i2c_runtime_worker, s);
    if(!s->worker) {
        (void)labmate_comm_local_release(s->owner, LabMateCommI2c3);
        s->owner = NULL;
        s->status = LabMateI2cRuntimeFailed;
        return false;
    }
    s->status = LabMateI2cRuntimeScanning;
    furi_thread_start(s->worker);
    return true;
}

void labmate_i2c_runtime_stop(LabMateI2cRuntime* s) {
    if(!s || !s->worker) return;
    furi_mutex_acquire(s->mutex, FuriWaitForever);
    s->stop_requested = true;
    furi_mutex_release(s->mutex);
    /* Bounded firmware acquire (50ms) and per-probe (5ms) are essential:
     * never change this to stock FuriWaitForever acquisition. */
    labmate_i2c_runtime_reap(s);
}

LabMateI2cRuntimeStatus labmate_i2c_runtime_snapshot(
    LabMateI2cRuntime* s, uint8_t page, LabMateI2cView* out) {
    if(!out) return LabMateI2cRuntimeFailed;
    memset(out, 0, sizeof(*out));
    if(!s) return LabMateI2cRuntimeFailed;
    furi_mutex_acquire(s->mutex, FuriWaitForever);
    (void)labmate_i2c_present(&s->model, page, out);
    const LabMateI2cRuntimeStatus status = s->status;
    furi_mutex_release(s->mutex);
    return status;
}

void labmate_i2c_runtime_free(LabMateI2cRuntime* s) {
    if(!s) return;
    labmate_i2c_runtime_stop(s);
    furi_mutex_free(s->mutex);
    free(s);
}
