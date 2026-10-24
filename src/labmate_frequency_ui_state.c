#include "labmate_frequency_ui_state.h"
bool labmate_frequency_ui_live(
    bool high_pin, bool high_active, bool low_active,
    bool correct_owner, bool blocked, bool release_fault) {
    return (high_pin ? high_active && !low_active :
                       low_active && !high_active) &&
           correct_owner && !blocked && !release_fault;
}
