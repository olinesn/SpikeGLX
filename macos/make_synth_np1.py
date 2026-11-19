#!/usr/bin/env python3
"""Write a small synthetic SpikeGLX Neuropixels 1.0 AP recording.

Output: <dir>/synth_g0/synth_g0_imec0/synth_g0_t0.imec0.ap.bin + .meta
385 channels (384 AP + 1 SY), int16, 30 kHz, interleaved by sample.
Content: Gaussian noise (~8 counts), a slow 7 Hz wave, six "units" whose
spikes span ~10 neighbouring sites, and a 1 Hz sync square wave on SY bit 6.
"""
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

out_root = Path(sys.argv[1])
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

srate = 30000
n_ap = 384
n_sy = 1
n_chan = n_ap + n_sy
n_samp = int(secs * srate)

rng = np.random.default_rng(1)
data = np.zeros((n_samp, n_chan), dtype=np.float32)
data[:, :n_ap] = rng.normal(0, 8, size=(n_samp, n_ap))

t = np.arange(n_samp) / srate
data[:, :n_ap] += (20 * np.sin(2 * np.pi * 7 * t))[:, None]

# Spike waveform: 2 ms, negative peak then slower positive rebound.
w_t = np.arange(-30, 60) / srate
wave = -np.exp(-((w_t / 0.00025) ** 2)) + 0.35 * np.exp(-(((w_t - 0.0006) / 0.0004) ** 2))
units = [(3, 140, 20), (40, 120, 18), (95, 90, 25), (150, 150, 12), (210, 110, 30), (300, 140, 20), (360, 80, 15)]
for centre, amp, rate in units:
    n_spk = rng.poisson(rate * secs)
    times = rng.integers(100, n_samp - 100, size=n_spk)
    for ch in range(max(0, centre - 6), min(n_ap, centre + 7)):
        gain = amp * np.exp(-((ch - centre) ** 2) / 8.0)
        for s in times:
            data[s - 30:s + 60, ch] += gain * wave

data[:, :n_ap] = np.clip(data[:, :n_ap], -512, 511)
sync = ((t % 1.0) < 0.5).astype(np.int16) << 6
out = np.rint(data).astype(np.int16)
out[:, n_ap] = sync

run_dir = out_root / "synth_g0" / "synth_g0_imec0"
run_dir.mkdir(parents=True, exist_ok=True)
bin_path = run_dir / "synth_g0_t0.imec0.ap.bin"
meta_path = run_dir / "synth_g0_t0.imec0.ap.meta"
raw = out.tobytes(order="C")
bin_path.write_bytes(raw)

imro = "(0,384)" + "".join(f"({c} 0 0 500 250 1)" for c in range(n_ap))
chan_map = "(384,384,1)" + "".join(f"(AP{c};{c}:{c})" for c in range(n_ap)) + "(SY0;768:768)"

meta = {
    "acqApLfSy": "384,384,1",
    "appVersion": "20250915",
    "fileCreateTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "fileName": str(bin_path),
    "fileSHA1": hashlib.sha1(raw).hexdigest().upper(),
    "fileSizeBytes": str(len(raw)),
    "fileTimeSecs": f"{n_samp / srate:.6f}",
    "firstSample": "0",
    "gateMode": "Immediate",
    "imAiRangeMax": "0.6",
    "imAiRangeMin": "-0.6",
    "imCalibrated": "false",
    "imChan0apGain": "500",
    "imChan0lfGain": "250",
    "imChan0Ref": "ext",
    "imDatPrb_pn": "PRB_1_4_0480_1",
    "imDatPrb_type": "0",
    "imDatPrb_sn": "0",
    "imMaxInt": "512",
    "imSampRate": str(srate),
    "imTrgRising": "true",
    "imTrgSource": "0",
    "nDataDirs": "1",
    "nSavedChans": str(n_chan),
    "snsApLfSy": "384,0,1",
    "snsSaveChanSubset": "0:383,768",
    "syncSourceIdx": "0",
    "syncSourcePeriod": "1",
    "trigMode": "Immediate",
    "typeImEnabled": "1",
    "typeNiEnabled": "0",
    "typeObEnabled": "0",
    "typeThis": "imec",
    "userNotes": "synthetic test data (not a recording)",
    "~imroTbl": imro,
    "~snsChanMap": chan_map,
}
meta_path.write_text("".join(f"{k}={v}\n" for k, v in meta.items()))
print(bin_path, len(raw), "bytes")
print(meta_path)
