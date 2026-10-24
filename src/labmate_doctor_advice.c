#include "labmate_doctor_advice.h"
LabMateDoctorAdvice labmate_doctor_advice(
    const LabMateDoctorPanelAssessment* a) {
    const LabMateDoctorAdvice missing = {
        "INSUFFICIENT", "NO PROVEN SAMPLE", "REPEAT CAPTURE"
    };
    if(!a) return missing;
    switch(a->status) {
    case LabMateDoctorPanelSetReference:
        return (LabMateDoctorAdvice){"REFERENCE UNSET","NO COMPARISON","SET REF"};
    case LabMateDoctorPanelNoData:
        return (LabMateDoctorAdvice){"NO SEALED DATA","NO MEASUREMENT","CAPTURE + STOP"};
    case LabMateDoctorPanelBusy:
        return (LabMateDoctorAdvice){"CAPTURE BUSY","LEASE NOT CLEAR","STOP / CHECK"};
    case LabMateDoctorPanelUnsafe:
        return (LabMateDoctorAdvice){"UNSAFE EVIDENCE","CLOCK / LOSS","RETRY SAFELY"};
    case LabMateDoctorPanelInsufficient:
        return missing;
    case LabMateDoctorPanelAssessed: break;
    default: return missing;
    }
    if(!a->doctor.evidence_accepted) return missing;
    switch(a->doctor.verdict) {
    case LabMateDoctorNoSignalObserved:
        return (LabMateDoctorAdvice){
            "NO EDGES SEEN","TIMED OBSERVATION","CHECK WIRING"};
    case LabMateDoctorWithinExpected:
        return (LabMateDoctorAdvice){
            "WITHIN REFERENCE","SEALED SAMPLE","TEST UNDER LOAD"};
    case LabMateDoctorFrequencyDeviation:
        return (LabMateDoctorAdvice){
            "FREQUENCY DIFF","SEALED SAMPLE","VERIFY SOURCE"};
    case LabMateDoctorDutyDeviation:
        return (LabMateDoctorAdvice){
            "DUTY CYCLE DIFF","SEALED PULSE","CHECK PWM DUTY"};
    case LabMateDoctorMultipleDeviations:
        return (LabMateDoctorAdvice){
            "FREQ + DUTY DIFF","SEALED PULSE","RECHECK SIGNAL"};
    default: return missing;
    }
}
