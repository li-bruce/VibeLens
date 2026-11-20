"""Diagnose a real catalog-reader/atomic-replacement collision on an isolated copy."""
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

RUN = Path(__file__).resolve().parent
APP = RUN.parents[2]
PACK = APP.parent / "asset-transport-skills/vibelens"
FIXTURE = RUN / "sqlite-handle-repro"
FIXTURE.mkdir(exist_ok=False)
DATABASE = FIXTURE / "application.sqlite"
assert DATABASE.resolve().is_relative_to(RUN)
with zipfile.ZipFile(RUN / "failed-unified-original-evidence.zip") as archive:
    DATABASE.write_bytes(archive.read("var/db/application.sqlite"))

WRITER = r'''
import { Store } from 'APP_STORE';
import readline from 'node:readline';
const store = new Store(process.argv[2]);
console.log(JSON.stringify({stage:'writer_ready',pid:process.pid}));
const input=readline.createInterface({input:process.stdin});
input.on('line',line=>{
  const op=JSON.parse(line).op;
  if(op==='close'){store.close();console.log(JSON.stringify({stage:'writer_closed'}));input.close();return;}
  try{store.persist();console.log(JSON.stringify({ok:true,pid:process.pid,method:'Store.persist'}));}
  catch(error){console.log(JSON.stringify({ok:false,pid:process.pid,method:'Store.persist',code:error.code,errno:error.errno,syscall:error.syscall,path:error.path,dest:error.dest,stack:error.stack}));}
});
'''.replace("APP_STORE", (APP / "src/store.mjs").as_uri())
READER = r'''
import json,os,sys
from pathlib import Path
pack,app,filename=sys.argv[1:]
sys.path.insert(0,str(Path(pack)/'scripts'))
from bo_observer.data import catalog
store=json.loads((Path(app)/'bo_stategraph/databases.json').read_text(encoding='utf-8-sig'))['stores'][0]
os.environ[store['url_env']]='sqlite:///'+Path(filename).as_posix()
original=catalog._inspect
held=False
def barrier(inspector,method,*args,**kwargs):
    global held
    value=original(inspector,method,*args,**kwargs)
    if method=='get_table_names' and not held:
        held=True
        database_list=[list(row) for row in inspector.bind.exec_driver_sql('PRAGMA database_list').fetchall()]
        print(json.dumps({'stage':'actual_reflection_connection_held','pid':os.getpid(),'tables':value,'database_list':database_list,'canonical_module':catalog.__file__}),flush=True)
        assert sys.stdin.readline().strip()=='release'
    return value
catalog._inspect=barrier
result=catalog.collect(store,root=Path(app))
print(json.dumps({'stage':'canonical_collect_returned','pid':os.getpid(),'resources':len(result['resources']),'coverage':result['coverage']}),flush=True)
# Remain alive after collect/dispose so writer success cannot be attributed to process exit.
assert sys.stdin.readline().strip()=='exit'
'''
(FIXTURE / "writer.mjs").write_text(WRITER, encoding="utf-8")
(FIXTURE / "reader.py").write_text(READER, encoding="utf-8")


class UniqueProcess(ctypes.Structure):
    _fields_ = [("pid", w.DWORD), ("started", w.FILETIME)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [
        ("process", UniqueProcess), ("name", w.WCHAR * 256),
        ("service", w.WCHAR * 64), ("kind", w.UINT),
        ("status", w.ULONG), ("session", w.DWORD), ("restartable", w.BOOL),
    ]


def holders(filename):
    """Query Windows Restart Manager for this one fixture; never shut down anything."""
    api = ctypes.WinDLL("rstrtmgr")
    api.RmStartSession.argtypes = [ctypes.POINTER(w.DWORD), w.DWORD, w.LPWSTR]
    api.RmRegisterResources.argtypes = [w.DWORD, w.UINT, ctypes.POINTER(w.LPCWSTR), w.UINT, ctypes.c_void_p, w.UINT, ctypes.c_void_p]
    api.RmGetList.argtypes = [w.DWORD, ctypes.POINTER(w.UINT), ctypes.POINTER(w.UINT), ctypes.POINTER(ProcessInfo), ctypes.POINTER(w.DWORD)]
    api.RmEndSession.argtypes = [w.DWORD]
    session, key = w.DWORD(), ctypes.create_unicode_buffer(33)
    rc = api.RmStartSession(ctypes.byref(session), 0, key)
    if rc:
        return {"error": rc, "stage": "start"}
    try:
        names = (w.LPCWSTR * 1)(str(filename))
        rc = api.RmRegisterResources(session, 1, names, 0, None, 0, None)
        if rc:
            return {"error": rc, "stage": "register"}
        required, size, reason = w.UINT(), w.UINT(), w.DWORD()
        rc = api.RmGetList(session, ctypes.byref(required), ctypes.byref(size), None, ctypes.byref(reason))
        if rc == 0:
            return {"pids": [], "processes": []}
        if rc != 234:
            return {"error": rc, "stage": "count"}
        size.value = required.value
        rows = (ProcessInfo * size.value)()
        rc = api.RmGetList(session, ctypes.byref(required), ctypes.byref(size), rows, ctypes.byref(reason))
        if rc:
            return {"error": rc, "stage": "list"}
        return {"pids": [row.process.pid for row in rows[:size.value]], "processes": [{"pid": row.process.pid, "name": row.name} for row in rows[:size.value]]}
    finally:
        api.RmEndSession(session)


def receive(process):
    line = process.stdout.readline()
    if not line:
        raise RuntimeError("Child ended before its protocol response: " + process.stderr.read())
    return json.loads(line)


def persist(process):
    process.stdin.write('{"op":"persist"}\n')
    process.stdin.flush()
    return receive(process)


env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "VIBELENS_SKILL": str(PACK), "BO_DIAGNOSTIC_SKILL": str(PACK)}
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
writer = reader = None
result = {"source": "controlled_real_catalog_connection_and_unmodified_native_Store.persist", "fixture": str(DATABASE), "original_application_database_modified": False, "installed_files_modified": False, "reader_patch_scope": "Process-local barrier after canonical get_table_names SQL, preserving the actual result and connection; no installed file edit."}
try:
    writer = subprocess.Popen(["node", str(FIXTURE / "writer.mjs"), str(DATABASE)], cwd=APP, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags)
    result["writer_ready"] = receive(writer)
    result["before_collector"] = persist(writer)
    result["holders_before"] = holders(DATABASE)
    reader = subprocess.Popen([sys.executable, "-B", str(FIXTURE / "reader.py"), str(PACK), str(APP), str(DATABASE)], cwd=APP, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags)
    result["reader_held"] = receive(reader)
    result["holders_while_reflecting"] = holders(DATABASE)
    result["while_collector_connection_open"] = persist(writer)
    reader.stdin.write("release\n")
    reader.stdin.flush()
    result["reader_returned"] = receive(reader)
    result["reader_still_alive_after_dispose"] = reader.poll() is None
    result["holders_after_dispose"] = holders(DATABASE)
    result["after_canonical_dispose_same_reader_process"] = persist(writer)
    reader.stdin.write("exit\n")
    reader.stdin.flush()
    reader.wait(timeout=10)
    result["reader_exit_code"] = reader.returncode
    result["reader_stderr"] = reader.stderr.read()
    result["fixture_database_sha256"] = hashlib.sha256(DATABASE.read_bytes()).hexdigest()
    result["valid_reproduction"] = (
        result["before_collector"]["ok"]
        and result["reader_held"]["stage"] == "actual_reflection_connection_held"
        and not result["while_collector_connection_open"]["ok"]
        and result["while_collector_connection_open"]["code"] == "EPERM"
        and result["after_canonical_dispose_same_reader_process"]["ok"]
        and result["reader_still_alive_after_dispose"]
    )
    if "pids" in result["holders_while_reflecting"]:
        assert result["reader_held"]["pid"] in result["holders_while_reflecting"]["pids"]
    assert result["valid_reproduction"], result
finally:
    for process in [reader, writer]:
        if process is not None and process.poll() is None:
            if process is writer:
                try:
                    process.stdin.write('{"op":"close"}\n')
                    process.stdin.flush()
                    process.wait(timeout=5)
                except Exception:
                    process.terminate()
            else:
                process.terminate()
            process.wait(timeout=10)
    (FIXTURE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
