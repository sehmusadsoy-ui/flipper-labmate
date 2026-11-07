#pragma once
#include <furi.h>
#include <storage/storage.h>
#include <gui/gui.h>
#include "labmate_profiles.h"
#include "labmate_profile_storage.h"
#include "labmate_ui_prefs_storage.h"
#include "labmate_resource_policy.h"
#include "labmate_dashboard_store.h"
#define GPIO_COUNT LABMATE_MONITOR_PIN_COUNT
#define LABMATE_UART_TX_CAP 12U
typedef enum {LoggerFrequencyLow, LoggerFrequencyHigh, LoggerPulse, LoggerSourceCount} LabMateLoggerSource;
typedef enum {LabMateScreenMenu, LabMateScreenLogger, LabMateScreenHistoryDetail} LabMateScreen;
typedef struct {bool tx_sent; uint32_t tx_total;} LabMateUart;
typedef struct {
    void* mutex;
    LabMateScreen screen;
    LabMateCaptureOwner capture_owner;
    uint8_t gpio_index, capture_pin_index;
    bool capture_blocked, capture_release_fault, frequency_irq_active, frequency_hw_active, pulse_irq_active;
    LabMateLoggerSource logger_source, logger_session_source;
    bool logger_recording, logger_busy, logger_busy_stopping, logger_error;
    uint32_t logger_rows, logger_start_tick, logger_last_tick, logger_next_file_index, logger_session_generation;
    uint8_t logger_session_pin;
    char logger_path[96];
    File* logger_file;
    Storage* logger_storage;
    LabMateDashboardStore doctor_store;
    LabMateUart uart;
    LabMateProfileStore profiles;
    uint8_t profile_active_copy, profile_notice;
    LabMateProfileIoResult profile_io;
    bool profile_busy;
    LabMateUiPreferences ui_prefs;
    uint8_t ui_prefs_active_copy, ui_prefs_notice;
    LabMateUiPrefsIoResult ui_prefs_io;
    bool ui_prefs_busy, settings_toast_active;
    uint32_t settings_toast_tick;
    bool history_loading, history_busy, history_delete_mode, history_delete_confirm;
    uint8_t history_count, history_selected, history_delete_notice;
    File* history_file;
    Storage* history_storage;
} LabMateApp;
typedef struct {
    bool logger_start_requested, logger_stop_requested;
    bool history_scan_requested, history_open_requested, history_close_requested, history_delete_requested;
    uint16_t history_delete_id;
    uint8_t history_delete_selected;
    bool profiles_read_requested, profiles_save_requested, profiles_delete_requested;
    LabMateProfileStore proposed_profiles;
    uint8_t proposed_copy;
    bool ui_prefs_save_requested;
    LabMateUiPreferences proposed_ui_prefs;
    uint8_t proposed_ui_prefs_copy;
    char pending_log_row[160];
    bool pending_log, uart_tx_requested;
    uint8_t uart_tx_len, uart_tx_payload[LABMATE_UART_TX_CAP+2U];
} LabMateDeferredWork;
bool labmate_logger_storage_start(LabMateApp* app);
void labmate_logger_storage_stop(LabMateApp* app);
void labmate_logger_dashboard_finalize(LabMateApp* app);
void labmate_deferred_prepare(LabMateApp* app, LabMateDeferredWork* work);
void labmate_deferred_execute(LabMateApp* app, LabMateDeferredWork* work, ViewPort* viewport);
bool labmate_frequency_low_lease_pending(void);
bool labmate_frequency_tim2_lease_pending(void);
bool labmate_pulse_lease_pending(void);
bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity);
bool labmate_uart_send(LabMateUart* uart, const uint8_t* bytes, size_t size);
void labmate_history_close(LabMateApp* app);
void labmate_history_scan(LabMateApp* app);
void labmate_history_open(LabMateApp* app);
void labmate_history_read_step(LabMateApp* app);
bool labmate_history_delete_file(uint16_t id);
