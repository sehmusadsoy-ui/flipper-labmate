#include <furi.h>
#include <storage/storage.h>
#include <string.h>
#include <gui/gui.h>
#include "labmate_deferred.h"
#include "labmate_logger_snapshot.h"
#include "labmate_logger_storage.h"
#include "labmate_history.h"
#include "labmate_profile_storage.h"
#include "labmate_uart.h"

#define LOGGER_SYNC_EVERY_ROWS 10U

/* Prepare a pending logger snapshot with UI mutex held. */
void labmate_deferred_prepare(LabMateApp* app, LabMateDeferredWork* work) {
        work->pending_log = false;
        if(app->screen == LabMateScreenLogger && app->logger_recording) {
            work->pending_log = logger_prepare_row(app, work->pending_log_row, sizeof(work->pending_log_row));
        }
        if(app->logger_busy && app->logger_error &&
           !work->logger_start_requested && !work->logger_stop_requested &&
           (app->logger_file || app->logger_storage)) {
            work->logger_stop_requested = true;
        }
}

/* Execute SD I/O outside UI mutex and any interrupt/render callbacks. */
void labmate_deferred_execute(LabMateApp* app, LabMateDeferredWork* work,
                              ViewPort* viewport) {
        /* Explicit TX is small, synchronous and outside the draw mutex.
         * Its result/total are published only after re-acquiring the mutex. */
        if(work->uart_tx_requested) {
            const bool sent = labmate_uart_send(
                &app->uart, work->uart_tx_payload, work->uart_tx_len);
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            app->uart.tx_sent = sent;
            if(sent) {
                if(UINT32_MAX - app->uart.tx_total < work->uart_tx_len)
                    app->uart.tx_total = UINT32_MAX;
                else app->uart.tx_total += work->uart_tx_len;
            }
            furi_mutex_release(app->mutex);
        }
        if(work->logger_start_requested || work->logger_stop_requested) {
            /* Display OPENING/SAVING without holding the drawing mutex
             * while storage blocks. The main loop may still wait for SD. */
            view_port_update(viewport);
            if(work->logger_stop_requested) labmate_logger_storage_stop(app);
            else labmate_logger_storage_start(app);
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            app->logger_busy = false;
            if(work->logger_stop_requested)
                labmate_logger_dashboard_finalize(app);
            furi_mutex_release(app->mutex);
        }

        /* Profile I/O is deferred until AFTER releasing the UI mutex.
         * No microSD writes are made in an interrupt or drawing callback.
         */
        if(work->profiles_read_requested) {
            LabMateProfileStore restored;
            uint8_t active = LABMATE_PROFILE_COPY_NONE;
            const LabMateProfileIoResult result =
                labmate_profile_sd_load(&restored, &active);
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            app->profiles = restored;
            app->profile_active_copy = active;
            app->profile_io = result;
            app->profile_busy = false;
            furi_mutex_release(app->mutex);
        }
        if(work->profiles_save_requested) {
            uint8_t written_copy = LABMATE_PROFILE_COPY_NONE;
            const bool saved = labmate_profile_sd_save(
                &work->proposed_profiles, work->proposed_copy, &written_copy);
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            if(saved) {
                app->profiles = work->proposed_profiles;
                app->profile_active_copy = written_copy;
                app->profile_io = LabMateProfileIoOk;
                app->profile_notice = work->profiles_delete_requested ? 6U : 1U;
            } else {
                app->profile_notice = 5U; /* WRITE ERR */
            }
            app->profile_busy = false;
            furi_mutex_release(app->mutex);
        }

        /* History directory/file operations never hold the UI mutex. */
        if(work->history_close_requested) labmate_history_close(app);
        if(work->history_scan_requested) labmate_history_scan(app);
        if(work->history_open_requested) labmate_history_open(app);
        if(work->history_delete_requested) {
            /* Confirmation has already snapped a numeric ID. No logger,
             * history reader or GPIO callback may write/remove CSV files.
             */
            const bool can_delete =
                !app->logger_recording && !app->logger_busy &&
                !app->logger_file && !app->logger_storage &&
                !app->history_file && !app->history_storage;
            const bool deleted =
                can_delete && labmate_history_delete_file(work->history_delete_id);
            if(deleted) labmate_history_scan(app);

            furi_mutex_acquire(app->mutex, FuriWaitForever);
            if(deleted && app->history_count > 0U) {
                app->history_selected =
                    work->history_delete_selected < app->history_count ?
                    work->history_delete_selected : (uint8_t)(app->history_count - 1U);
            }
            app->history_delete_notice = deleted ? 1U : 2U;
            app->history_delete_mode = !deleted;
            app->history_delete_confirm = false;
            app->history_busy = false;
            furi_mutex_release(app->mutex);
        }
        if(app->screen == LabMateScreenHistoryDetail && app->history_loading) {
            labmate_history_read_step(app);
        }

        /* SD writes stay outside the mutex and never occur in capture IRQs. */
        if(work->pending_log) {
            size_t bytes = strlen(work->pending_log_row);
            bool ok = app->logger_file &&
                storage_file_write(app->logger_file, work->pending_log_row, bytes) == bytes;
            /* Periodic sync happens outside the GUI mutex and outside IRQs.
             * STOP/BACK still syncs and closes the file immediately. */
            if(ok && ((app->logger_rows + 1U) % LOGGER_SYNC_EVERY_ROWS) == 0U) {
                ok = storage_file_sync(app->logger_file);
            }
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            if(ok) {
                app->logger_rows++;
            } else {
                app->logger_error = true;
                app->logger_recording = false;
                app->logger_busy = true;
                app->logger_busy_stopping = true;
            }
            furi_mutex_release(app->mutex);
            if(!ok) {
                labmate_logger_storage_stop(app);
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                app->logger_busy = false;
                furi_mutex_release(app->mutex);
            }
        }

}
