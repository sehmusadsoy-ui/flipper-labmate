#include "labmate_doctor_frequency_policy.h"
#include <assert.h>
#include <stdio.h>

static LabMateDoctorFrequencyCandidate low(void){return (LabMateDoctorFrequencyCandidate){
  .path=LabMateDoctorFrequencyLowPC1,.pin_index=1,.owned_active=true,
  .source_clock_running=true,.start_tick=100,.stop_tick=200,
  .last_publication_tick=199,.start_tick_hz=1000,.stop_tick_hz=1000,
  .start_clock_hz=64000000,.stop_clock_hz=64000000,
  .irq_or_timer_edge_count=20,.publication_count=10,
  .frequency_millihz=100000,.low_period_cycles=640000};}
static LabMateDoctorFrequencyCandidate high(void){
  LabMateDoctorFrequencyCandidate c=low();
  c.path=LabMateDoctorFrequencyHighPB3;c.pin_index=4;
  c.irq_or_timer_edge_count=40;c.publication_count=1;
  c.low_period_cycles=0;c.high_gate_edges=32;
  c.high_gate_cycles=20480000;return c;}
int main(void){unsigned n=0;
#define G(expr) do{assert((expr));n++;}while(0)
LabMateDoctorFrequencyCandidate c=low();G(labmate_doctor_frequency_policy_accept(&c));
c=high();G(labmate_doctor_frequency_policy_accept(&c));
G(!labmate_doctor_frequency_policy_accept(NULL));
c=low();c.path=(LabMateDoctorFrequencyPath)3;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.pin_index=4;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.pin_index=1;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.owned_active=false;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.source_clock_running=false;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.release_fault=true;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.hold=true;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.stop_tick_hz=999;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.stop_clock_hz=48000000;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.stop_tick=100;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.last_publication_tick=99;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.last_publication_tick=201;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.stop_tick=800;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.stop_tick=350000;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.irq_or_timer_edge_count=1;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.publication_count=0;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.frequency_millihz=100001;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.low_period_cycles=0;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.low_period_cycles=1;c.frequency_millihz=(uint32_t)64000000000ULL;
G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.low_period_cycles=UINT32_C(0x80000000);G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.low_mailbox_overwrites=1;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.low_mailbox_exhausted=true;G(!labmate_doctor_frequency_policy_accept(&c));
c=low();c.high_gate_edges=32;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_gate_edges=1;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_gate_edges=41;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_gate_cycles=0;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_gate_cycles=UINT32_C(0x80000000);G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_audit_exhausted=true;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.low_period_cycles=640000;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.high_gate_cycles=6400000;G(!labmate_doctor_frequency_policy_accept(&c));
c=high();c.frequency_millihz=100001;G(!labmate_doctor_frequency_policy_accept(&c));
#undef G
printf("PHASE3D FREQUENCY PRE-STOP POLICY PASS: %u positive/negative gates\n",n);
return n==34?0:1;}
