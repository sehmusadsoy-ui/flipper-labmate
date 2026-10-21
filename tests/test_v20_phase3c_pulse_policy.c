#include "labmate_doctor_pulse_policy.h"
#include <assert.h>
#include <stdio.h>

static LabMateDoctorPulseCandidate good(void) {
    return (LabMateDoctorPulseCandidate){
        .pair={.pairs=3,.edges=20,.high_cycles=32000,.low_cycles=32000},
        .start_tick=100,.stop_tick=200,.last_edge_tick=199,
        .start_tick_hz=1000,.stop_tick_hz=1000,
        .start_clock_hz=64000000,.stop_clock_hz=64000000,
        .native_owner_confirmed=true,.irq_active=true,.timebase_enabled=true
    };
}
int main(void) {
    unsigned n=0;
    LabMateDoctorPulseCandidate c=good();
    assert(labmate_doctor_pulse_policy_accept(&c));n++;
    c.native_owner_confirmed=false;
    assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.irq_active=false;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.release_fault=true;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.timebase_enabled=false;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.stop_clock_hz=48000000;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.stop_tick_hz=500;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.stop_tick=c.start_tick;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.last_edge_tick=201;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.last_edge_tick=99;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.stop_tick=1000;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.stop_tick=350000;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.exhausted=true;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.pairs=0;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.edges=2;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.high_cycles=0;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.low_cycles=0;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.high_cycles=UINT32_MAX;assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();c.pair.high_cycles=1;c.pair.low_cycles=1;
    assert(!labmate_doctor_pulse_policy_accept(&c));n++;
    c=good();assert(!labmate_doctor_pulse_policy_accept(NULL));n++;
    printf("PHASE3C PULSE STOP POLICY PASS: %u acceptance/rejection gates\n",n);
    return n == 20U ? 0 : 1;
}
