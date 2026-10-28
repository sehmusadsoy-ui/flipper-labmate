#pragma once
#include "labmate_internal.h"

/* Only UI-owned state is updated. Call from app thread under app mutex. */
void labmate_ui_motion_init(LabMateApp* app);
void labmate_ui_motion_step(LabMateApp* app);
void labmate_ui_motion_carousel(LabMateApp* app, uint8_t old_index, int8_t direction);
void labmate_ui_motion_list(LabMateApp* app, uint8_t old_index);
void labmate_ui_motion_info_cancel(LabMateApp* app);
void labmate_ui_motion_info_page(LabMateApp* app, uint8_t old_guide, int8_t direction);
void labmate_ui_motion_info_scroll(LabMateApp* app);
void labmate_ui_motion_info_section(LabMateApp* app, uint8_t old_section, int8_t direction);
bool labmate_ui_motion_is_active(const LabMateApp* app);
