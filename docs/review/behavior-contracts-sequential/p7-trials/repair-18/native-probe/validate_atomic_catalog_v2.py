"""Validate the installed atomic catalog against the unchanged native publisher."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

RUN = Path(__file__).resolve().parent
APP = RUN.parents[2]
PACK = Path(os.environ["VIBELENS_SKILL"])
OLD = APP / "review/runtime/repair17-native-browser-20261120"
FIXTURE = RUN / "isolated-v2"
FIXTURE.mkdir(exist_ok=False)
sha = lambda value: hashlib.sha256(value).hexdigest()
assert sha((OLD / "reproduce_sqlite_replace.py").read_bytes()) == "7cfe07308dba3d796178396d81bc8b62c07941299e6619c3dbcf05ce1b503e49"

WRITER = r'''
import { Store } from 'APP_STORE';
import readline from 'node:readline';
const store=new Store(process.argv[2]);
console.log(JSON.stringify({stage:'writer_ready',pid:process.pid}));
const input=readline.createInterface({input:process.stdin});
input.on('line',line=>{
  const command=JSON.parse(line);
  if(command.op==='close'){store.close();input.close();return;}
  try{
    if(command.op==='publish_schema'){
      if(!/^[a-z0-9_]+$/.test(command.table))throw new Error('Invalid fixture table');
      store.transaction(()=>store.run('CREATE TABLE "'+command.table+'" (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)'));
    }else store.persist();
    console.log(JSON.stringify({stage:'publication',ok:true,pid:process.pid,method:'Unmodified Store.persist',operation:command.op}));
  }catch(error){console.log(JSON.stringify({stage:'publication',ok:false,pid:process.pid,code:error.code,syscall:error.syscall,stack:error.stack}));}
});
'''.replace("APP_STORE", (APP / "src/store.mjs").as_uri())

READER = r'''
import ctypes,hashlib,json,os,sys
from ctypes import wintypes as w
from pathlib import Path
pack,app,filename,phase=sys.argv[1:]
sys.path.insert(0,str(Path(pack)/'scripts'))
from bo_observer.data import catalog,sqlite_snapshot as snapshot
store=json.loads((Path(app)/'bo_stategraph/databases.json').read_text(encoding='utf-8-sig'))['stores'][0]
store['sqlite_file_mode']='atomic_replace'
os.environ[store['url_env']]='sqlite:///'+Path(filename).as_posix()
held=False
streams=[]
aliases=[]
images=[]
def actual_handle_path(stream):
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    method=kernel.GetFinalPathNameByHandleW
    method.argtypes=[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD];method.restype=w.DWORD
    buffer=ctypes.create_unicode_buffer(32768)
    count=method(msvcrt.get_osfhandle(stream.fileno()),buffer,len(buffer),0)
    assert 0<count<len(buffer)
    return buffer.value
def pause(value):
    print(json.dumps(value),flush=True)
    assert sys.stdin.readline().strip()=='release'
original_open=snapshot._open_windows_link
def open_with_barrier(path):
    global held
    stream=original_open(path)
    streams.append(stream);aliases.append(str(path))
    if phase=='snapshot_handle' and not held:
        held=True
        pause({'stage':'barrier','phase':phase,'pid':os.getpid(),'stream_closed':stream.closed,
               'actual_windows_handle_path':actual_handle_path(stream),'alias_path':str(path),
               'alias_differs_from_published_path':Path(path)!=Path(filename),
               'same_file_before_replacement':(os.fstat(stream.fileno()).st_dev,os.fstat(stream.fileno()).st_ino)==(os.stat(filename).st_dev,os.stat(filename).st_ino),
               'file_inode_before_replacement':os.fstat(stream.fileno()).st_ino})
    return stream
snapshot._open_windows_link=open_with_barrier
original_image=snapshot.read_image
def read_image(path):
    image=original_image(path)
    images.append(hashlib.sha256(image).hexdigest())
    return image
snapshot.read_image=read_image
original_inspect=catalog._inspect
def inspect_with_barrier(inspector,method,*args,**kwargs):
    global held
    value=original_inspect(inspector,method,*args,**kwargs)
    if phase=='reflection' and method=='get_table_names' and not held:
        held=True
        pause({'stage':'barrier','phase':phase,'pid':os.getpid(),'tables':value,
               'database_list':[list(row) for row in inspector.bind.exec_driver_sql('PRAGMA database_list').fetchall()],
               'query_only':inspector.bind.exec_driver_sql('PRAGMA query_only').scalar(),
               'all_file_streams_closed':all(stream.closed for stream in streams),
               'snapshot_sha256':images[-1]})
    return value
catalog._inspect=inspect_with_barrier
def collect(stage):
    value=catalog.collect(store,root=Path(app))
    print(json.dumps({'stage':stage,'pid':os.getpid(),'sqlite_file_mode':store['sqlite_file_mode'],
        'canonical_catalog':catalog.__file__,'canonical_snapshot':snapshot.__file__,
        'image_sha256':images[-1],'catalog':value,'all_file_streams_closed':all(stream.closed for stream in streams),
        'remaining_aliases':[name for name in aliases if Path(name).exists()]}),flush=True)
collect('first_catalog')
assert sys.stdin.readline().strip()=='next'
collect('next_catalog')
assert sys.stdin.readline().strip()=='exit'
'''

(FIXTURE / "writer.mjs").write_text(WRITER, encoding="utf-8")
(FIXTURE / "reader.py").write_text(READER, encoding="utf-8")
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "VIBELENS_SKILL": str(PACK), "BO_DIAGNOSTIC_SKILL": str(PACK)}
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def receive(process):
    line = process.stdout.readline()
    if not line:
        raise RuntimeError("Child ended before response: " + process.stderr.read())
    return json.loads(line)


def send(process, value):
    process.stdin.write(value + "\n")
    process.stdin.flush()


def publish(process, **command):
    send(process, json.dumps(command))
    result = receive(process)
    assert result["ok"], result
    return result


def tables(result):
    return {item["name"] for item in result["catalog"]["resources"] if item["kind"] == "table"}


results = []
for phase in ["snapshot_handle", "reflection"]:
    folder = FIXTURE / phase
    folder.mkdir()
    temporary = folder / "snapshot-temp"
    temporary.mkdir()
    database = folder / "application.sqlite"
    assert database.resolve().is_relative_to(FIXTURE)
    with zipfile.ZipFile(OLD / "failed-unified-original-evidence.zip") as archive:
        database.write_bytes(archive.read("var/db/application.sqlite"))
    writer = reader = None
    result = {"phase": phase, "database": str(database), "provider": str(PACK), "sqlite_file_mode": "atomic_replace"}
    try:
        writer = subprocess.Popen(["node", str(FIXTURE / "writer.mjs"), str(database)], cwd=APP, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags)
        result["writer_ready"] = receive(writer)
        result["without_collector"] = publish(writer, op="persist")
        result["old_image_sha256"] = sha(database.read_bytes())
        reader = subprocess.Popen([sys.executable, "-B", str(FIXTURE / "reader.py"), str(PACK), str(APP), str(database), phase], cwd=APP, env={**env, "TEMP": str(temporary), "TMP": str(temporary)}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags)
        result["barrier"] = receive(reader)
        assert result["barrier"]["stage"] == "barrier" and result["barrier"]["phase"] == phase
        if phase == "snapshot_handle":
            assert result["barrier"]["same_file_before_replacement"] and result["barrier"]["alias_differs_from_published_path"]
            assert not result["barrier"]["stream_closed"]
        else:
            assert result["barrier"]["query_only"] == 1 and result["barrier"]["all_file_streams_closed"]
            assert result["barrier"]["database_list"] == [[0, "main", ""]]
        new_table = "diag_" + phase + "_v2"
        result["publication_while_held"] = publish(writer, op="publish_schema", table=new_table)
        result["new_image_sha256"] = sha(database.read_bytes())
        assert result["new_image_sha256"] != result["old_image_sha256"]
        send(reader, "release")
        result["first_catalog"] = receive(reader)
        assert result["first_catalog"]["stage"] == "first_catalog"
        assert result["first_catalog"]["image_sha256"] == result["old_image_sha256"]
        assert new_table not in tables(result["first_catalog"])
        assert result["first_catalog"]["all_file_streams_closed"] and result["first_catalog"]["remaining_aliases"] == []
        send(reader, "next")
        result["next_catalog"] = receive(reader)
        assert result["next_catalog"]["stage"] == "next_catalog"
        assert result["next_catalog"]["image_sha256"] == result["new_image_sha256"]
        assert tables(result["next_catalog"]) == tables(result["first_catalog"]) | {new_table}
        resource = next(item for item in result["next_catalog"]["catalog"]["resources"] if item["name"] == new_table)
        assert {field["name"] for field in resource["fields"]} == {"id", "payload"}
        assert result["next_catalog"]["remaining_aliases"] == [] and result["next_catalog"]["all_file_streams_closed"]
        assert sha(database.read_bytes()) == result["new_image_sha256"], "Collector changed the published bytes"
        send(reader, "exit")
        reader.wait(timeout=10)
        result["reader_exit"] = reader.returncode
        result["reader_stderr"] = reader.stderr.read()
        assert reader.returncode == 0, result["reader_stderr"]
        result["after_collector"] = publish(writer, op="persist")
        result["valid"] = True
    finally:
        for process in [reader, writer]:
            if process is not None and process.poll() is None:
                if process is writer:
                    try:
                        send(process, '{"op":"close"}')
                        process.wait(timeout=5)
                    except Exception:
                        process.terminate()
                else:
                    process.terminate()
                process.wait(timeout=10)
        (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    results.append(result)

summary = {"version": 2, "based_on_repro_sha256": sha((OLD / "reproduce_sqlite_replace.py").read_bytes()), "provider": str(PACK), "store_source_sha256": sha((APP / "src/store.mjs").read_bytes()), "valid": all(row["valid"] for row in results), "case_results": results, "business_database_modified": False, "business_source_or_installation_modified": False, "browser_or_recording_started": False}
(RUN / "isolated-v2-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"valid": summary["valid"], "provider": str(PACK), "cases": [{"phase": row["phase"], "publication_while_held": row["publication_while_held"]["ok"], "old_snapshot_consistent": True, "new_schema_on_next_poll": True} for row in results]}, ensure_ascii=False))
