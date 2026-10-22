#include "labmate_menu_grid.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    _Static_assert(LabMateGroupCount == 5, "review root tile count");
    _Static_assert(LabMateMenuTileY + LabMateMenuTileRows * LabMateMenuTileHeight
                   <= 52, "root cards must clear footer");
    for(uint8_t i=0;i<LabMateGroupCount;i++) {
        const unsigned x=labmate_menu_tile_x(i);
        const unsigned y=labmate_menu_tile_y(i);
        assert(x + LabMateMenuTileWidth <= 128);
        assert(y + LabMateMenuTileHeight <= 52);
        assert(labmate_nav_group_icon(i)<LabMateToolCount);
        assert(labmate_menu_root_move(i,0,0)==i);
    }
    assert(labmate_menu_root_move(0,1,0)==1);
    assert(labmate_menu_root_move(1,-1,0)==0);
    assert(labmate_menu_root_move(2,1,0)==3);
    assert(labmate_menu_root_move(4,1,0)==4);
    assert(labmate_menu_root_move(0,0,1)==2);
    assert(labmate_menu_root_move(2,0,1)==4);
    assert(labmate_menu_root_move(4,0,1)==0);
    assert(labmate_menu_root_move(1,0,1)==3);
    assert(labmate_menu_root_move(3,0,1)==1);
    assert(labmate_menu_root_move(0,0,-1)==4);
    assert(labmate_menu_root_move(1,0,-1)==3);
    assert(labmate_menu_root_move(255,0,0)==0);
    puts("ULTIMATE ROOT GRID PASS: safe 5-tile geometry, spatial navigation, ID stability");
    return 0;
}
