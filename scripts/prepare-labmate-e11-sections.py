#!/usr/bin/env python3
"""App-only E11 linker layout; no runtime firmware patch or device access."""
import argparse
from pathlib import Path
import subprocess

PIN='d3f89dfe2ef6b01839201598e9be1590cba80322'
ANCHOR='''        self.app_env.Append(
            CCFLAGS=self.app.cflags,
'''
HOOK='''        # Keep LabMate's entry in .text and bound each code allocation.
        if self.app.appid == "labmate":
            self.app_env.Replace(
                LINKER_SCRIPT_PATH=self.app._appdir.File("labmate_sections.ld")
            )
'''
DEP_ANCHOR='''        app_artifacts.compact = self.app_env.EmbedAppMetadata(
'''
DEP='''        if self.app.appid == "labmate":
            self.app_env.Depends(app_artifacts.debug, self.app_env["LINKER_SCRIPT_PATH"])

'''
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('sdk',type=Path);p.add_argument('--apply',action='store_true');ns=p.parse_args()
    sdk=ns.sdk.resolve()
    assert subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()==PIN,'Wrong E11 SDK'
    staged=sdk/'applications_user/labmate/labmate_sections.ld'
    assert staged.is_file(),'Stage the reviewed application linker script first'
    layout=staged.read_text(encoding='utf-8')
    assert 'KEEP(*(.text.labmate_app))' in layout and '.text.ui 0x00000000' in layout and '.text.core 0x00000000' in layout
    path=sdk/'scripts/fbt_tools/fbt_extapps.py';text=path.read_text(encoding='utf-8')
    assert text.count(ANCHOR)==1 and text.count(DEP_ANCHOR)==1,'FBT anchors changed'
    if HOOK in text:
        assert text.count(HOOK)==text.count(DEP)==1
        print('LABMATE SPLIT-SECTION HOOK ALREADY PRESENT');return
    assert 'labmate_sections.ld' not in text and '-flinker-output=nolto-rel' not in text,'Unexpected build hook'
    if ns.apply:
        path.write_text(text.replace(ANCHOR,HOOK+ANCHOR).replace(DEP_ANCHOR,DEP+DEP_ANCHOR),encoding='utf-8')
        print('LABMATE-ONLY SPLIT-SECTION LINK APPLIED; NO FIRMWARE/DEVICE CHANGE')
    else: print('LABMATE SPLIT-SECTION LINK CHECK PASS; source unchanged')
if __name__=='__main__':main()
