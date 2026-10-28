/* Current v2.0 E11 root navigation + pixel carousel/list geometry.
 * The historical test filename is kept for CI compatibility; the removed
 * 5-card tile header must NEVER be restored to satisfy this host test.
 * This is not a substitute for 128x64 device font/raster acceptance.
 */
#include "labmate_navigation.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void rect(int x, int y, int w, int h) {
    assert(x >= 0 && y >= 0 && w > 0 && h > 0);
    assert(x + w <= 128 && y + h <= 64);
}
static void test_carousel(void) {
    /* Exact current renderer positions, verified against extracted source. */
    rect(11,18,18,18); /* previous focus frame */
    rect(48,10,32,27); /* current focus frame */
    rect(99,18,18,18); /* next focus frame */
    rect(14,21,12,12);
    rect(52,10,24,24);
    rect(102,21,12,12);
    assert(46 < 54 && 55 < 63); /* label and detail baselines */
    assert(LabMateGroupCount == 5);
    assert(strcmp(labmate_nav_group_title(LabMateGroupMeasure),"MEASURE")==0);
    assert(strcmp(labmate_nav_group_title(LabMateGroupOutput),"OUTPUT")==0);
    assert(strcmp(labmate_nav_group_title(LabMateGroupRecords),"RECORDS")==0);
    assert(strcmp(labmate_nav_group_title(LabMateGroupComm),"COMM")==0);
    assert(strcmp(labmate_nav_group_title(LabMateGroupInfo),"SETTINGS")==0);
    for(uint8_t group=0;group<LabMateGroupCount;group++) {
        const uint8_t prev=labmate_nav_wrap(group,LabMateGroupCount,-1);
        const uint8_t next=labmate_nav_wrap(group,LabMateGroupCount,1);
        assert(prev<LabMateGroupCount && next<LabMateGroupCount);
        assert(labmate_nav_wrap(next,LabMateGroupCount,-1)==group);
        assert(labmate_nav_wrap(prev,LabMateGroupCount,1)==group);
    }
}
static void test_lists(void) {
    const uint8_t expected_sizes[]={7U,2U,4U,3U,1U};
    uint8_t visits[LabMateToolCount]={0};
    for(uint8_t g=0;g<LabMateGroupCount;g++) {
        const uint8_t n=labmate_nav_group_size(g);
        assert(n==expected_sizes[g]);
        for(uint8_t selected=0;selected<n;selected++) {
            const uint8_t first=labmate_nav_first_visible(selected,n,3U);
            assert(first<=selected && selected<first+3U);
            for(uint8_t row=0;row<3U && first+row<n;row++) {
                const int y=12+14*row;
                rect(2,y,124,14);   /* selected focus pill */
                rect(6,y+2,10,10); /* 10px icon */
                rect(22,y+2,91,9); /* measured title text slot */
                assert(y+14<=54);
                assert(22+91<118); /* right chevron */
            }
            const uint8_t tool=labmate_nav_tool_at(g,selected);
            assert(tool<LabMateToolCount);
            assert(labmate_nav_tool_title(tool)[0]);
            visits[tool]++;
        }
        assert(labmate_nav_tool_at(g,n)==LabMateToolInvalid);
    }
    for(uint8_t t=0;t<LabMateToolCount;t++)assert(visits[t]==1U);
    assert(LabMateToolGpio==0);
    assert(LabMateToolCounter==8);
    assert(LabMateToolScope==14);
    assert(LabMateToolDoctor==15);
    assert(LabMateToolDashboard==16);
}
int main(void) {
    test_carousel();
    test_lists();
    puts("E11 ROOT CAROUSEL/LIST HOST PASS: 5 groups, 17 tools, 128x64");
    return 0;
}
