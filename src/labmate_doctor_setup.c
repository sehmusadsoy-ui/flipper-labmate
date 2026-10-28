#include "labmate_doctor_setup.h"
#include "ui_kit.h"
#include <stdio.h>

void labmate_doctor_setup_reset(LabMateDoctorSetupUi* ui, LabMateDoctorPanel* panel) {
    if(!ui || !panel) return;
    *ui = (LabMateDoctorSetupUi){0};
    panel->field = LabMateDoctorFieldSource;
}

static void frequency_step(LabMateDoctorPanel* p, bool finer) {
    if(finer) {
        if(p->frequency_step_hz > 1U) p->frequency_step_hz /= 10U;
    } else if(p->frequency_step_hz < 1000U) {
        p->frequency_step_hz *= 10U;
    }
}

LabMateDoctorSetupAction labmate_doctor_setup_key(
    LabMateDoctorSetupUi* ui, LabMateDoctorPanel* panel,
    LabMateDoctorSetupKey key, bool long_press) {
    if(!ui || !panel || panel->field >= LabMateDoctorFieldCount)
        return LabMateDoctorSetupStay;

    if(long_press) {
        if(key == LabMateDoctorSetupOk && !ui->editing) ui->info_open = true;
        return LabMateDoctorSetupStay;
    }
    if(ui->info_open) {
        if(key == LabMateDoctorSetupBack || key == LabMateDoctorSetupOk)
            ui->info_open = false;
        return LabMateDoctorSetupStay;
    }
    if(ui->editing) {
        switch(key) {
        case LabMateDoctorSetupUp:
            labmate_doctor_panel_edit(panel, 1);
            break;
        case LabMateDoctorSetupDown:
            labmate_doctor_panel_edit(panel, -1);
            break;
        case LabMateDoctorSetupLeft:
        case LabMateDoctorSetupRight:
            if(panel->field == LabMateDoctorFieldFrequency)
                frequency_step(panel, key == LabMateDoctorSetupLeft);
            break;
        case LabMateDoctorSetupOk:
            ui->editing = false;
            break;
        case LabMateDoctorSetupBack:
            *panel = ui->before_edit;
            ui->editing = false;
            break;
        }
        return LabMateDoctorSetupStay;
    }

    const uint8_t row = panel->field % 3U;
    const uint8_t base = panel->field < 3U ? 0U : 3U;
    switch(key) {
    case LabMateDoctorSetupUp:
        panel->field = (uint8_t)(base + (row + 2U) % 3U);
        break;
    case LabMateDoctorSetupDown:
        panel->field = (uint8_t)(base + (row + 1U) % 3U);
        break;
    case LabMateDoctorSetupLeft:
        if(base == 3U) panel->field = row;
        break;
    case LabMateDoctorSetupRight:
        if(base == 0U) panel->field = (uint8_t)(3U + row);
        else return LabMateDoctorSetupOpenSignal;
        break;
    case LabMateDoctorSetupOk:
        ui->before_edit = *panel;
        ui->editing = true;
        break;
    case LabMateDoctorSetupBack:
        return LabMateDoctorSetupExit;
    }
    return LabMateDoctorSetupStay;
}

static void page_header(Canvas* c, uint8_t page) {
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    canvas_draw_line(c, 7, 2, 4, 5);
    canvas_draw_line(c, 4, 5, 7, 8);
    (void)ui_kit_text(c, 12, 9, 80, page ? "Duty" : "Frequency", NULL);
    for(uint8_t i = 0U; i < 4U; ++i) {
        const uint8_t x = (uint8_t)(99U + 8U * i);
        if(i == page) canvas_draw_box(c, x, 4, 3, 3);
        else canvas_draw_line(c, x, 5, x + 2U, 5);
    }
}

static const char* field_label(uint8_t field) {
    switch(field) {
    case LabMateDoctorFieldSource: return "Source";
    case LabMateDoctorFieldFrequency: return "Reference";
    case LabMateDoctorFieldFrequencyTolerance:
    case LabMateDoctorFieldDutyTolerance: return "Tolerance";
    case LabMateDoctorFieldDuty: return "Target";
    case LabMateDoctorFieldSilence: return "Quiet time";
    default: return "";
    }
}

static void field_value(const LabMateDoctorPanel* p, uint8_t field,
                        bool editing, char* buf, size_t size) {
    switch(field) {
    case LabMateDoctorFieldSource:
        (void)snprintf(buf, size, "%s",
                       p->source == LabMateSnapshotPulse ? "Pulse" : "Frequency");
        break;
    case LabMateDoctorFieldFrequency:
        if(!p->reference.frequency_millihz && !editing)
            (void)snprintf(buf, size, "Not set");
        else
            (void)snprintf(buf, size, "%lu Hz",
                           (unsigned long)(p->reference.frequency_millihz / 1000U));
        break;
    case LabMateDoctorFieldFrequencyTolerance:
        (void)snprintf(buf, size, "%u.%u%%",
                       (unsigned)(p->reference.frequency_tolerance_permille / 10U),
                       (unsigned)(p->reference.frequency_tolerance_permille % 10U));
        break;
    case LabMateDoctorFieldDuty:
        (void)snprintf(buf, size, "%u.%u%%",
                       (unsigned)(p->reference.expected_duty_permille / 10U),
                       (unsigned)(p->reference.expected_duty_permille % 10U));
        break;
    case LabMateDoctorFieldDutyTolerance:
        (void)snprintf(buf, size, "%u.%u%%",
                       (unsigned)(p->reference.duty_tolerance_permille / 10U),
                       (unsigned)(p->reference.duty_tolerance_permille % 10U));
        break;
    case LabMateDoctorFieldSilence:
        (void)snprintf(buf, size, "%lu ms",
                       (unsigned long)p->reference.minimum_no_signal_window_ms);
        break;
    default:
        if(size) buf[0] = '\0';
        break;
    }
}

static void dim_value(Canvas* c, uint8_t y, const char* text) {
    canvas_set_font(c, FontSecondary);
    const uint16_t width = canvas_string_width(c, text);
    if(!width || width > 121U) return;
    const uint8_t x = (uint8_t)(121U - width);
    canvas_set_color(c, ColorWhite);
    for(uint8_t yy = y + 2U; yy <= y + 9U; ++yy)
        for(uint8_t xx = (uint8_t)(x + (yy & 1U)); xx < 121U; xx += 2U)
            canvas_draw_dot(c, xx, yy);
    canvas_set_color(c, ColorBlack);
}

static void info_panel(Canvas* c, uint8_t field) {
    const char* first = "";
    const char* second = "";
    switch(field) {
    case LabMateDoctorFieldSource:
        first = "Select an input."; second = "Frequency or Pulse."; break;
    case LabMateDoctorFieldFrequency:
        first = "Expected frequency."; second = "Set step with arrows."; break;
    case LabMateDoctorFieldFrequencyTolerance:
    case LabMateDoctorFieldDutyTolerance:
        first = "Allowed difference"; second = "from expected value."; break;
    case LabMateDoctorFieldDuty:
        first = "Set expected duty."; second = "Default is 50.0%."; break;
    case LabMateDoctorFieldSilence:
        first = "Minimum quiet time"; second = "before no signal."; break;
    default: return;
    }
    canvas_set_color(c, ColorWhite);
    canvas_draw_rbox(c, 4, 33, 120, 30, 3);
    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, 4, 33, 120, 30, 3);
    canvas_set_font(c, FontSecondary);
    (void)ui_kit_text(c, 10, 45, 108, first, NULL);
    (void)ui_kit_text(c, 10, 56, 108, second, NULL);
}

void labmate_doctor_setup_draw(
    Canvas* c, const LabMateDoctorPanel* panel,
    const LabMateDoctorSetupUi* ui, uint8_t pulse_phase) {
    if(!c || !panel || !ui || panel->field >= LabMateDoctorFieldCount) return;
    const uint8_t page = panel->field < 3U ? 0U : 1U;
    page_header(c, page);
    for(uint8_t row = 0; row < 3U; ++row) {
        const uint8_t field = (uint8_t)(3U * page + row);
        const bool selected = field == panel->field;
        const bool editing = selected && ui->editing;
        const uint8_t y = (uint8_t)(13U + 13U * row);
        char value[20];
        field_value(panel, field, editing, value, sizeof(value));
        const UiKitSettingsRowState state = editing ? UiKitSettingsEditing :
            selected ? UiKitSettingsSelected : UiKitSettingsNormal;
        if(ui_kit_settings_row(c, y, field_label(field), value, state) &&
           field == LabMateDoctorFieldFrequency &&
           !panel->reference.frequency_millihz && !selected)
            dim_value(c, y, value);
    }
    canvas_set_font(c, FontSecondary);
    ui_kit_pulse_line(c, 4, 59, 27, pulse_phase,
                      panel->reference.frequency_millihz != 0U);
    if(ui->editing && panel->field == LabMateDoctorFieldFrequency) {
        char text[22];
        (void)snprintf(text, sizeof(text), "Step %lu Hz",
                       (unsigned long)panel->frequency_step_hz);
        (void)ui_kit_text(c, 36, 60, 89, text, NULL);
    } else if(ui->editing) {
        (void)ui_kit_text(c, 36, 60, 89,
                          "Up / Down to change", "Up/Down: change");
    } else if(!panel->reference.frequency_millihz) {
        (void)ui_kit_text(c, 36, 60, 89,
                          "Set a reference to start", "Set reference");
    } else {
        (void)ui_kit_text(c, 36, 60, 89, "Ready", NULL);
    }
    if(ui->info_open) info_panel(c, panel->field);
}
