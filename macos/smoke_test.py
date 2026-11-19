#!/usr/bin/env python3
"""Smoke test for SpikeGLX_NISIM.app on macOS (standard library only).

Usage: python3 smoke_test.py path/to/SpikeGLX_NISIM.app [--port 4142]

Puts a _Configs/mainapp.ini beside the .app that names an existing data
folder (so the first-start dialog doesn't block) and turns on the command
server on 127.0.0.1. Starts the app with the working folder "/", as Finder
does, then checks over the command server that:
- the app answers (GETVERSION);
- SETDATADIR and SETMULTIDRIVEENABLE work and the app stays alive (they
  crashed it before they were moved onto the GUI thread);
- the app saved its settings in _Configs beside the .app.
Exits 0 on success. Removes the _Configs it made; refuses to run if one exists.
"""
import argparse
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("app", type=Path)
ap.add_argument("--port", type=int, default=4142)
ap.add_argument("--start-timeout", type=float, default=120)
args = ap.parse_args()

app = args.app.resolve()
exe = app / "Contents" / "MacOS" / app.stem
cfg_dir = app.parent / "_Configs"
if not exe.is_file():
    sys.exit(f"no executable at {exe}")
if cfg_dir.exists():
    sys.exit(f"{cfg_dir} already exists; not touching it")

work = Path(tempfile.mkdtemp(prefix="sglx-smoke-")).resolve()
d1, d2, d3 = (work / name for name in ("data1", "data2", "data3"))
for d in (d1, d2, d3):
    d.mkdir()

cfg_dir.mkdir()
ini = cfg_dir / "mainapp.ini"
ini.write_text(
    f"[MainApp]\ndataDir={d1}\n\n"
    f"[CmdSrv]\nenabled=true\niface=127.0.0.1\nport={args.port}\n"
)

log_path = work / "app.log"
log = open(log_path, "w")
proc = subprocess.Popen([str(exe)], cwd="/", stdout=log, stderr=subprocess.STDOUT)
failures = []


def alive():
    return proc.poll() is None


def send(line):
    with socket.create_connection(("127.0.0.1", args.port), timeout=20) as s:
        s.sendall((line + "\n").encode())
        buf = b""
        while not (buf.endswith(b"OK\n") or b"ERROR" in buf):
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    time.sleep(0.5)  # a crash after the reply shows up as a dead process
    return buf.decode(errors="replace").strip()


def check(line, expect):
    try:
        reply = send(line)
    except OSError as e:
        reply = f"<{e}>"
    ok = alive() and expect(reply)
    print(f"{'ok  ' if ok else 'FAIL'} {line} -> {reply!r} (running={alive()})")
    if not ok:
        failures.append(line)


def first_line(reply):
    return reply.splitlines()[0] if reply else ""


try:
    deadline = time.time() + args.start_timeout
    while True:
        if not alive():
            failures.append(f"app exited during start-up (code {proc.returncode})")
            break
        try:
            socket.create_connection(("127.0.0.1", args.port), timeout=1).close()
            print(f"command server listening after {args.start_timeout - (deadline - time.time()):.1f} s")
            break
        except OSError:
            if time.time() > deadline:
                failures.append("command server never started listening")
                break
            time.sleep(0.5)

    if not failures:
        check("GETVERSION", lambda r: r.startswith("SpikeGLX v") and r.endswith("OK"))
        check("GETDATADIR 0", lambda r: first_line(r) == str(d1))
        check(f"SETDATADIR 0 {d2}", lambda r: r == "OK")
        check("GETDATADIR 0", lambda r: first_line(r) == str(d2))
        check("SETMULTIDRIVEENABLE 1", lambda r: r == "OK")
        check(f"SETDATADIR 1 {d3}", lambda r: r == "OK")
        check("GETDATADIR 1", lambda r: first_line(r) == str(d3))
        check("SETMULTIDRIVEENABLE 0", lambda r: r == "OK")
        check("SETDATADIR 0 /no/such/folder", lambda r: r.startswith("ERROR"))
        check("GETVERSION", lambda r: r.endswith("OK"))

        text = ini.read_text()
        saved = (str(d2) in text and str(d3) in text
                 and "multidrive=false" in text and "[RgtSrv]" in text)
        print(f"{'ok  ' if saved else 'FAIL'} settings saved beside the .app ({ini})")
        if not saved:
            failures.append("settings not saved")
            print(text)
finally:
    if alive():
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    log.close()
    shutil.rmtree(cfg_dir, ignore_errors=True)

if failures:
    print("\nFAILED:", "; ".join(failures))
    print("--- app output ---")
    print(log_path.read_text()[-6000:])
    sys.exit(1)
print("\nsmoke test passed")
