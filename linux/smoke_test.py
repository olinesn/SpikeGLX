#!/usr/bin/env python3
"""Smoke test for the Linux build of SpikeGLX_NISIM (standard library only).

Usage: python3 linux/smoke_test.py PATH [--port 4142]
  PATH is the built program (out/SpikeGLX_NISIM) or the AppImage.

Needs an X display (DISPLAY set): a desktop session, or a virtual X server
such as Xvfb (not tried yet). SpikeGLX keeps its settings in _Configs in its "app folder": the
working folder for the bare program, the AppImage's folder for an AppImage.
The test puts a _Configs/mainapp.ini there that names an existing data folder
(so the first-start dialog doesn't block) and turns on the command server on
127.0.0.1, starts the app, then checks over the command server that:
- the app answers (GETVERSION);
- SETDATADIR and SETMULTIDRIVEENABLE work and the app stays alive;
- VERIFYSHA1 passes a synthetic recording and fails a copy with one byte changed;
- the app saved its settings in _Configs.
Exits 0 on success. Removes the _Configs it made; refuses to run if one exists.
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("app", type=Path)
ap.add_argument("--port", type=int, default=4142)
ap.add_argument("--start-timeout", type=float, default=120)
args = ap.parse_args()

exe = args.app.resolve()
if not exe.is_file() or not os.access(exe, os.X_OK):
    sys.exit(f"not an executable file: {exe}")
if not os.environ.get("DISPLAY"):
    sys.exit("no DISPLAY: run this in a desktop session or under a virtual X server")

work = Path(tempfile.mkdtemp(prefix="sglx-smoke-")).resolve()
is_appimage = exe.suffix == ".AppImage"
app_dir = exe.parent if is_appimage else work / "app"
app_dir.mkdir(exist_ok=True)
cfg_dir = app_dir / "_Configs"
if cfg_dir.exists():
    sys.exit(f"{cfg_dir} already exists; not touching it")

d1, d2, d3 = (work / name for name in ("data1", "data2", "data3"))
for d in (d1, d2, d3):
    d.mkdir()

# A short synthetic NP1.0 recording, and a copy with one byte changed.
subprocess.run([sys.executable, "-I", str(HERE.parent / "macos" / "make_synth_np1.py"),
                str(work / "rec"), "0.2"], check=True, stdout=subprocess.DEVNULL)
good = next((work / "rec").rglob("*.ap.bin"))
bad = work / "bad" / good.name
bad.parent.mkdir()
shutil.copy(good, bad)
shutil.copy(good.with_suffix(".meta"), bad.with_suffix(".meta"))
with open(bad, "r+b") as f:
    f.seek(1000)
    b = f.read(1)
    f.seek(1000)
    f.write(bytes([b[0] ^ 0xFF]))

cfg_dir.mkdir()
ini = cfg_dir / "mainapp.ini"
ini.write_text(
    f"[MainApp]\ndataDir={d1}\n\n"
    f"[CmdSrv]\nenabled=true\niface=127.0.0.1\nport={args.port}\n"
)

log_path = work / "app.log"
log = open(log_path, "w")
proc = subprocess.Popen([str(exe)], cwd=str(app_dir), stdout=log, stderr=subprocess.STDOUT)
failures = []


def alive():
    return proc.poll() is None


def send(line):
    with socket.create_connection(("127.0.0.1", args.port), timeout=60) as s:
        s.sendall((line + "\n").encode())
        buf = b""
        while not (buf.endswith(b"OK\n") or (b"ERROR" in buf and buf.endswith(b"\n"))):
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
    shown = reply if len(reply) < 120 else reply[:50] + " ... " + reply[-60:]
    print(f"{'ok  ' if ok else 'FAIL'} {line} -> {shown!r} (running={alive()})")
    if not ok:
        failures.append(line)


def first_line(reply):
    return reply.splitlines()[0] if reply else ""


try:
    t0 = time.time()
    while True:
        if not alive():
            failures.append(f"app exited during start-up (code {proc.returncode})")
            break
        try:
            socket.create_connection(("127.0.0.1", args.port), timeout=1).close()
            print(f"command server listening after {time.time() - t0:.1f} s")
            break
        except OSError:
            if time.time() - t0 > args.start_timeout:
                failures.append("command server never started listening")
                break
            time.sleep(0.25)

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
        check(f"VERIFYSHA1 {good}", lambda r: r.endswith("OK") and "ERROR" not in r)
        check(f"VERIFYSHA1 {bad}", lambda r: "ERROR" in r and "does not match" in r)
        check("GETVERSION", lambda r: r.endswith("OK"))

        text = ini.read_text()
        saved = (str(d2) in text and str(d3) in text
                 and "multidrive=false" in text and "[RgtSrv]" in text)
        print(f"{'ok  ' if saved else 'FAIL'} settings saved in {ini}")
        if not saved:
            failures.append("settings not saved")
            print(text)
finally:
    if alive():
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
    log.close()
    shutil.rmtree(cfg_dir, ignore_errors=True)

if failures:
    print("\nFAILED:", "; ".join(failures))
    print("--- app output ---")
    print(log_path.read_text()[-6000:])
    sys.exit(1)
shutil.rmtree(work, ignore_errors=True)
print("\nsmoke test passed")
