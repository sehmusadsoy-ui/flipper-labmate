#!/usr/bin/env python3
"""Read-only host simulation of E11 operator USB FAP install decisions.

No physical port is connected. File readback, immutable PC backups, typed
consent, valid firmware identity, final MD5 and legacy cleanup are verified
using a mocked Flipper CLI with Momentum's REAL '[F] name 12345b' format.
"""
import builtins
import hashlib
from pathlib import Path
import runpy
import sys
import tempfile
import types


def make_fake(initial, firmware_ok=True):
    class FakeDevice:
        CLI_PROMPT=">: "
        def __init__(self, *_):
            self.files=dict(initial)
            self.events=[]
            self.current=""
            self.firmware_ok=firmware_ok
            self.read=types.SimpleNamespace(until=self.until)
            self.lists=[]
            self.consent_seen=False

        def __enter__(self):
            return self

        def __exit__(self,*_):
            return False

        def exist_dir(self,path):
            return path=="/ext/apps"

        def send_and_wait_eol(self,command):
            assert command.startswith('storage list "') and command.endswith('"\r')
            self.current=command.split('"')[1]
            self.lists.append(self.current)
            return b''

        def until(self,mark):
            assert mark==">: "
            if self.current=="/ext/apps":
                return b'\t[D] Tools\r\n'
            if self.current=="/ext/apps/Tools":
                output=b''
                for path,data in sorted(self.files.items()):
                    if path.startswith("/ext/apps/Tools/"):
                        output+=("\t[F] %s %db\r\n"%(path.rsplit("/",1)[-1],len(data))).encode()
                return output or b"\tEmpty\r\n"
            return b"Empty\r\n"

        def has_error(self,data):
            return b"Storage error:" in data

        def send_and_wait_prompt(self,command):
            if command=="device_info\r":
                commit="d3f89dfe" if self.firmware_ok else "00000000"
                return (f"hardware_model : Flipper Zero\r\n"
                        f"firmware_commit : {commit}\r\n"
                        f"firmware_commit_dirty : true\r\n"
                        f"firmware_version : mntm-dev\r\n"
                        f"firmware_api_major : 87\r\n"
                        f"firmware_api_minor : 1\r\n").encode()
            assert command=="loader info\r"
            self.events.append("loader info")
            return b"No application is running\r\n"

        def exist_file(self,path):
            return path in self.files

        def read_file(self,path):
            self.events.append("read old")
            return bytes(self.files[path])

        def hash_flipper(self,path):
            return hashlib.md5(self.files[path]).hexdigest()

        def size(self,path):
            return len(self.files[path])

        def send_file(self,from_pc,path):
            assert path=="/ext/apps/Tools/labmate.fap"
            assert "loader info" in self.events
            self.events.append("write canonical")
            self.files[path]=Path(from_pc).read_bytes()

        def remove(self,path):
            assert path!="/ext/apps/Tools/labmate.fap"
            assert "write canonical" in self.events
            self.events.append("remove legacy")
            del self.files[path]

    return FakeDevice


def run_case(globals_,initial,mode,firmware_ok=True,consent=True):
    old_filename="/ext/apps/Tools/LabMate-Counter-Step3-E11-Trial.fap"
    target="/ext/apps/Tools/labmate.fap"
    fake=make_fake(initial,firmware_ok=firmware_ok)()
    with tempfile.TemporaryDirectory() as d:
        folder=Path(d)
        fap=folder/"labmate.fap"
        proposed=b"\x7fELF"+b"NEW-V2.0-"*35
        fap.write_bytes(proposed)
        backup=folder/"backups"
        globals_["main"].__globals__["verify_fap"]=lambda file_path: hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        io=builtins.input
        argv=sys.argv
        def input_with_backup(prompt):
            fake.consent_seen=True
            if mode=="migrate":
                saved=list(backup.rglob("*.fap"))
                assert len(saved)==1 and saved[0].read_bytes()==initial[old_filename]
            if mode=="canonical":
                saved=list(backup.rglob("*.fap"))
                assert len(saved)==1 and saved[0].read_bytes()==initial[target]
            assert "write canonical" not in fake.events
            return "YUKLE-E11-LABMATE" if consent else ""
        try:
            builtins.input=input_with_backup
            sys.argv=["test","--fap",str(fap),"--backup-root",str(backup),"--port","COM42","--apply"]
            if mode in ("ambiguous","wrong_firmware","declined"):
                try:
                    globals_["main"]()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Unsafe plan was not blocked")
                assert "write canonical" not in fake.events
                assert "remove legacy" not in fake.events
            else:
                assert globals_["main"]()==0
                assert fake.files[target]==proposed
                assert "write canonical" in fake.events
                if mode=="migrate":
                    assert old_filename not in fake.files
                    assert fake.events.index("write canonical")<fake.events.index("remove legacy")
                if mode=="first":
                    assert not list(backup.rglob("*.fap"))
        finally:
            builtins.input=io
            sys.argv=argv
    return fake


def main():
    source=Path(__file__).with_name("install-v20-e11-usb.py")
    sys.path.insert(0,str(source.parent))
    globals_=runpy.run_path(str(source))
    pkg=types.ModuleType("flipper")
    pkg.__path__=[]
    storage=types.ModuleType("flipper.storage")
    cdc=types.ModuleType("flipper.utils.cdc")
    utility=types.ModuleType("flipper.utils")
    utility.__path__=[]
    previous={k:sys.modules.get(k) for k in ("flipper","flipper.storage","flipper.utils","flipper.utils.cdc")}
    current=[None]
    storage.FlipperStorage=lambda port: current[0]
    cdc.resolve_port=lambda logger,port: "COM42"
    sys.modules.update({"flipper":pkg,"flipper.storage":storage,"flipper.utils":utility,"flipper.utils.cdc":cdc})
    try:
        target="/ext/apps/Tools/labmate.fap"
        legacy="/ext/apps/Tools/LabMate-Counter-Step3-E11-Trial.fap"
        old=b"\x7fELF"+b"PREVIOUS-TESTED-STABLE-E11-"*30
        for mode,inventory,firmware_ok,consent in [
            ("migrate",{legacy:old},True,True),
            ("canonical",{target:old},True,True),
            ("first",{},True,True),
            ("ambiguous",{legacy:old,"/ext/apps/Tools/labmate-duplicate.fap":old},True,True),
            ("wrong_firmware",{legacy:old},False,True),
            ("declined",{legacy:old},True,False),
        ]:
            current[0]=make_fake(inventory,firmware_ok)()
            fake=current[0]
            # run_case creates the transport via make_fake, so share instance
            original_make_fake=globals()["make_fake"]
            try:
                globals()["make_fake"]=lambda *_args,**_kw: (lambda: fake)
                run_case(globals_,inventory,mode,firmware_ok,consent)
            finally:
                globals()["make_fake"]=original_make_fake
        print("HOST USB E11: legacy migration/backup, canonical replacement, first install,")
        print("ambiguous rejection, wrong firmware rejection, operator consent rejection: PASS")
    finally:
        for name,value in previous.items():
            if value is None:
                sys.modules.pop(name,None)
            else:
                sys.modules[name]=value


if __name__=="__main__":
    main()
