#include "labmate_doctor_panel.h"

void labmate_doctor_panel_init(LabMateDoctorPanel* p) {
    if(!p) return;
    *p = (LabMateDoctorPanel){0};
    p->source = LabMateSnapshotFrequency;
    p->frequency_step_hz = 1U;
    p->reference.frequency_tolerance_permille = 50U;
    p->reference.expected_duty_permille = 500U;
    p->reference.duty_tolerance_permille = 50U;
    p->reference.minimum_no_signal_window_ms = 1000U;
    /* frequency_millihz remains ZERO until the user explicitly sets it. */
}

void labmate_doctor_panel_move(LabMateDoctorPanel* p, int8_t d) {
    if(!p || !d) return;
    p->field = (uint8_t)((p->field + LabMateDoctorFieldCount +
            (d > 0 ? 1U : LabMateDoctorFieldCount - 1U)) % LabMateDoctorFieldCount);
}

static uint32_t saturating_edit(uint32_t value, uint32_t step, uint32_t max,
                                 int8_t direction) {
    if(direction > 0) return value > max - step ? max : value + step;
    return value < step ? 0U : value - step;
}

void labmate_doctor_panel_edit(LabMateDoctorPanel* p, int8_t d) {
    if(!p || !d) return;
    switch(p->field) {
    case LabMateDoctorFieldSource:
        p->source = p->source == LabMateSnapshotFrequency ?
            LabMateSnapshotPulse : LabMateSnapshotFrequency;
        break;
    case LabMateDoctorFieldFrequency:
        p->reference.frequency_millihz = saturating_edit(
            p->reference.frequency_millihz, p->frequency_step_hz * 1000U,
            100000000U, d);
        break;
    case LabMateDoctorFieldFrequencyTolerance:
        p->reference.frequency_tolerance_permille = (uint16_t)saturating_edit(
            p->reference.frequency_tolerance_permille, 10U, 1000U, d);
        break;
    case LabMateDoctorFieldDuty:
        p->reference.expected_duty_permille = (uint16_t)saturating_edit(
            p->reference.expected_duty_permille, 10U, 1000U, d);
        break;
    case LabMateDoctorFieldDutyTolerance:
        p->reference.duty_tolerance_permille = (uint16_t)saturating_edit(
            p->reference.duty_tolerance_permille, 10U, 1000U, d);
        break;
    case LabMateDoctorFieldSilence:
        p->reference.minimum_no_signal_window_ms = saturating_edit(
            p->reference.minimum_no_signal_window_ms, 100U, 10000U, d);
        if(!p->reference.minimum_no_signal_window_ms)
            p->reference.minimum_no_signal_window_ms = 100U;
        break;
    default: break;
    }
}

void labmate_doctor_panel_step(LabMateDoctorPanel* p) {
    if(!p) return;
    switch(p->frequency_step_hz) {
    case 1U: p->frequency_step_hz = 10U; break;
    case 10U: p->frequency_step_hz = 100U; break;
    case 100U: p->frequency_step_hz = 1000U; break;
    default: p->frequency_step_hz = 1U; break;
    }
}

LabMateDoctorPanelAssessment labmate_doctor_panel_assess(
    const LabMateDoctorPanel* p, const LabMateDashboardStore* store) {
    LabMateDoctorPanelAssessment a = {
        LabMateDoctorPanelInsufficient, {LabMateDoctorNotReady, false}};
    if(!p || !store) return a;
    if(!p->reference.frequency_millihz) {
        a.status = LabMateDoctorPanelSetReference;
        return a;
    }
    if(p->source > LabMateSnapshotPulse) return a;
    const LabMateDashboardSlot* slot = &store->slots[p->source];
    if(!slot->has_snapshot) {
        a.status = LabMateDoctorPanelNoData;
        return a;
    }
    if(slot->latest.quality == LabMateSnapshotBusy) {
        a.status = LabMateDoctorPanelBusy;
        return a;
    }
    if(slot->latest.quality == LabMateSnapshotClockUnsafe ||
       slot->latest.quality == LabMateSnapshotOverflow ||
       slot->latest.quality == LabMateSnapshotInvalid ||
       slot->latest.quality == LabMateSnapshotStale) {
        a.status = LabMateDoctorPanelUnsafe;
        return a;
    }
    LabMateDoctorResult r = {LabMateDoctorNotReady, false};
    if(!labmate_doctor_evaluate(&slot->latest, &p->reference, &r)) return a;
    if(!r.evidence_accepted) return a;
    a.status = LabMateDoctorPanelAssessed;
    a.doctor = r;
    return a;
}

const char* labmate_doctor_panel_status_text(const LabMateDoctorPanelAssessment* a) {
    if(!a) return "WAIT";
    switch(a->status) {
    case LabMateDoctorPanelSetReference: return "SET REF FIRST";
    case LabMateDoctorPanelNoData: return "NO SEALED DATA";
    case LabMateDoctorPanelBusy: return "BUSY - WAIT";
    case LabMateDoctorPanelUnsafe: return "DATA UNSAFE";
    case LabMateDoctorPanelInsufficient: return "INSUFFICIENT";
    case LabMateDoctorPanelAssessed:
        return a->doctor.evidence_accepted ?
            labmate_doctor_verdict_text(a->doctor.verdict) : "INSUFFICIENT";
    default: return "INSUFFICIENT";
    }
}
