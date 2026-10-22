#pragma once
/* v2.0 monochrome navigation: five tiles, fixed 128x64 geometry.
 * UI-only model. No Flipper HAL/heap, no tool-ID or Profile renumbering.
 * Row-major root: MEASURE OUTPUT / RECORDS COMM / INFO.
 */
#include <stdint.h>
#include "labmate_navigation.h"
enum {
    LabMateMenuTileWidth = 62,
    LabMateMenuTileHeight = 12,
    LabMateMenuTileY = 15,
    LabMateMenuTileGapY = 0,
    LabMateMenuTileRows = 3,
    LabMateMenuTileColumns = 2,
};
static inline uint8_t labmate_menu_tile_x(uint8_t index) {
    return (uint8_t)(1U + (index % 2U) * 64U);
}
static inline uint8_t labmate_menu_tile_y(uint8_t index) {
    return (uint8_t)(LabMateMenuTileY + (index / 2U) * LabMateMenuTileHeight);
}
/* Physical arrow semantics: L/R travel between columns; U/D travel
 * vertically and wrap inside their own column. INFO is the lone last tile.
 * The stable group IDs/order remain unchanged.
 */
static inline uint8_t labmate_menu_root_move(uint8_t selected, int8_t dx, int8_t dy) {
    if(selected >= LabMateGroupCount) selected = 0U;
    if(dx < 0) return (selected & 1U) ? (uint8_t)(selected - 1U) : selected;
    if(dx > 0) return !(selected & 1U) && selected + 1U < LabMateGroupCount ?
        (uint8_t)(selected + 1U) : selected;
    if(dy > 0) {
        const uint8_t next = (uint8_t)(selected + 2U);
        return next < LabMateGroupCount ? next : (uint8_t)(selected & 1U);
    }
    if(dy < 0) {
        return selected >= 2U ? (uint8_t)(selected - 2U) :
            (selected & 1U) ? 3U : 4U;
    }
    return selected;
}
