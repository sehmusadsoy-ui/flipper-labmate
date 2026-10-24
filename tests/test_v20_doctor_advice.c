#include "labmate_doctor_advice.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void text_ok(const char* t) {
    assert(t && *t && strlen(t) <= 20U);
    for(const char* p=t;*p;p++) assert(*p>=32&&*p<=126);
}
int main(void) {
    for(int x=0;x<=LabMateDoctorPanelAssessed;x++) {
        LabMateDoctorPanelAssessment a={0};
        a.status=(LabMateDoctorPanelStatus)x;
        for(int verdict=0;verdict<=LabMateDoctorMultipleDeviations;verdict++){
            a.doctor.verdict=(LabMateDoctorVerdict)verdict;
            a.doctor.evidence_accepted=true;
            LabMateDoctorAdvice advice=labmate_doctor_advice(&a);
            text_ok(advice.finding);text_ok(advice.evidence);text_ok(advice.next_check);
            assert(strstr(advice.finding,"BROKEN")==NULL);
            assert(strstr(advice.finding,"STUCK")==NULL);
        }
    }
    LabMateDoctorPanelAssessment bad={0};
    bad.status=LabMateDoctorPanelAssessed;
    bad.doctor.verdict=LabMateDoctorFrequencyDeviation;
    assert(!strcmp(labmate_doctor_advice(&bad).finding,"INSUFFICIENT"));
    assert(!strcmp(labmate_doctor_advice(NULL).finding,"INSUFFICIENT"));
    puts("V20 DOCTOR ADVICE HOST PASS: supported/insufficient, no hardware fault claims");
    return 0;
}
