from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "teensy_log_20260308_012238.csv"

df = pd.read_csv(CSV_PATH)

# only first 2 seconds
df = df[df["teensy_t_us"] <= 2_000_000].copy()

t = df["teensy_t_us"].to_numpy(dtype=float) * 1e-6
ch1 = df["raw1"].to_numpy(dtype=float)
ch5 = df["raw5"].to_numpy(dtype=float)

# remove DC offset
ch1 = ch1 - ch1.mean()
ch5 = ch5 - ch5.mean()

dt = np.median(np.diff(t))
n = len(ch1)

# dominant frequency from FFT
freqs = np.fft.rfftfreq(n, d=dt)
spec = np.abs(np.fft.rfft(ch1))
dom_idx = np.argmax(spec[1:]) + 1
f_dom = freqs[dom_idx]

# cross-correlation to estimate lag
corr = np.correlate(ch1, ch5, mode="full")
lags = np.arange(-n + 1, n)
lag_samples = lags[np.argmax(corr)]
time_shift = lag_samples * dt

# phase difference
phase_deg = (time_shift * f_dom * 360) % 360

# choose representation nearest to ideal antiphase (180°)
if abs(phase_deg - 180) > abs((360 - phase_deg) - 180):
    phase_deg = 360 - phase_deg

antiphase_error_deg = abs(180 - phase_deg)
antiphase_accuracy = 100 * (1 - antiphase_error_deg / 180)

print(f"Dominant frequency: {f_dom:.3f} Hz")
print(f"Lag: {lag_samples} samples")
print(f"Time shift: {time_shift*1000:.3f} ms")
print(f"Phase difference: {phase_deg:.3f} deg")
print(f"Antiphase error: {antiphase_error_deg:.3f} deg")
print(f'Antiphase accuracy: {antiphase_accuracy:.2f}%')