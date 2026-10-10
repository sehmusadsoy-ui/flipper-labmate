#include "labmate_pulse_math.h"

bool labmate_pulse_period_and_duty(
    uint32_t high_cycles,
    uint32_t low_cycles,
    uint32_t* period_cycles,
    uint32_t* duty_permille) {
    if(!period_cycles || !duty_permille) return false;

    const uint64_t period = (uint64_t)high_cycles + low_cycles;
    if(period == 0U || period > UINT32_MAX) return false;

    const uint32_t duty = (uint32_t)(
        ((uint64_t)high_cycles * 1000ULL + period / 2ULL) / period);

    *period_cycles = (uint32_t)period;
    *duty_permille = duty;
    return true;
}

/* Same insertion sort and exact middle selection as v1.6 Stable. */
uint32_t labmate_pulse_median5(const uint32_t values[LABMATE_PULSE_MEDIAN_SAMPLES]) {
    uint32_t sorted[LABMATE_PULSE_MEDIAN_SAMPLES];
    for(uint8_t i = 0U; i < LABMATE_PULSE_MEDIAN_SAMPLES; ++i) {
        uint32_t value = values[i];
        uint8_t j = i;
        while(j > 0U && sorted[j - 1U] > value) {
            sorted[j] = sorted[j - 1U];
            --j;
        }
        sorted[j] = value;
    }
    return sorted[LABMATE_PULSE_MEDIAN_SAMPLES / 2U];
}
