from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FILE = Path(__file__).with_name("keysight_1_1.csv")

OUTDIR = Path(__file__).resolve().parent / "pdf_results_keysight_1_1_thicker_lines"
OUTDIR.mkdir(exist_ok=True)

NUM_PEAKS_TO_SHOW = 4


def wrap_phase_deg(x):
    return (x + 180.0) % 360.0 - 180.0


def load_keysight_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        skiprows=2,
        header=None,
        names=["time_s", "ch1_v", "ch2_v"]
    )

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna().copy()
    df = df.sort_values("time_s").reset_index(drop=True)

    if len(df) < 8:
        raise ValueError("Not enough valid samples in CSV.")

    return df


def compute_fft(t, y):
    y_ac = y - np.mean(y)
    dt = np.mean(np.diff(t))
    if dt <= 0:
        raise ValueError("Invalid time axis.")

    fs = 1.0 / dt
    n = len(y_ac)

    window = np.hanning(n)
    y_win = y_ac * window

    fft_vals = np.fft.rfft(y_win)
    freqs = np.fft.rfftfreq(n, d=dt)
    mag = np.abs(fft_vals)

    return {
        "dt": dt,
        "fs": fs,
        "n": n,
        "freqs": freqs,
        "fft": fft_vals,
        "mag": mag,
    }


def dominant_frequency_from_both(freqs, mag1, mag2):
    combined = 0.5 * (mag1 + mag2)
    if len(combined) < 2:
        raise ValueError("FFT spectrum too short.")

    idx = np.argmax(combined[1:]) + 1
    return idx, freqs[idx]


def channel_stats(y, dominant_freq, phase_deg):
    y = np.asarray(y)
    mean_v = float(np.mean(y))
    min_v = float(np.min(y))
    max_v = float(np.max(y))
    ptp_v = float(np.ptp(y))
    amp_v = 0.5 * ptp_v
    rms_total = float(np.sqrt(np.mean(y ** 2)))
    rms_ac = float(np.sqrt(np.mean((y - mean_v) ** 2)))
    period_s = float(1.0 / dominant_freq) if dominant_freq > 0 else np.nan

    return {
        "mean_v": mean_v,
        "min_v": min_v,
        "max_v": max_v,
        "peak_to_peak_v": ptp_v,
        "amplitude_v": amp_v,
        "rms_total_v": rms_total,
        "rms_ac_v": rms_ac,
        "frequency_hz": float(dominant_freq),
        "period_s": period_s,
        "phase_deg": float(phase_deg),
    }


def first_n_fft_peaks(freqs, mag, n=4, min_freq=0.0):
    freqs = np.asarray(freqs)
    mag = np.asarray(mag)

    mask = freqs > min_freq
    freqs_sel = freqs[mask]
    mag_sel = mag[mask]

    if len(freqs_sel) < 3:
        return np.array([]), np.array([])

    peak_idx = []
    for i in range(1, len(mag_sel) - 1):
        if mag_sel[i] > mag_sel[i - 1] and mag_sel[i] > mag_sel[i + 1]:
            peak_idx.append(i)

    if not peak_idx:
        return np.array([]), np.array([])

    peak_idx = np.array(peak_idx)
    first_idx = peak_idx[:n]

    return freqs_sel[first_idx], mag_sel[first_idx]


def save_time_plot(t, y, title, ylabel, outpath):
    plt.figure(figsize=(10, 5))
    plt.plot(t, y, linewidth=4)
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, format="pdf", bbox_inches="tight")
    plt.close()

def save_time_overlay_plot(t, y1, y2, outpath, num_cycles=2):
    # find rising edges from CH1
    y_mid = 0.5 * (np.min(y1) + np.max(y1))
    high = y1 > y_mid
    rising_idx = np.where((~high[:-1]) & (high[1:]))[0] + 1

    if len(rising_idx) >= num_cycles + 1:
        i0 = rising_idx[0]
        i1 = rising_idx[num_cycles]
        t_plot = t[i0:i1]
        y1_plot = y1[i0:i1]
        y2_plot = y2[i0:i1]
    else:
        t_plot = t
        y1_plot = y1
        y2_plot = y2

    plt.figure(figsize=(10, 5))
    plt.plot(t_plot, y1_plot, linewidth=4, label="CH1", zorder=2)
    plt.plot(t_plot, y2_plot, linewidth=4, linestyle="--", alpha=0.8, label="CH2", zorder=3)
    plt.title(f"Time Domain - First {num_cycles} Cycles")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath, format="pdf", bbox_inches="tight")
    plt.close()


def save_fft_overlay_plot(freqs, mag1, mag2, outpath, f0=None):
    pfx1, pmy1 = first_n_fft_peaks(freqs, mag1, n=NUM_PEAKS_TO_SHOW, min_freq=0.0)
    pfx2, pmy2 = first_n_fft_peaks(freqs, mag2, n=NUM_PEAKS_TO_SHOW, min_freq=0.0)

    plt.figure(figsize=(10, 5))

    if len(pfx1) > 0:
        plt.plot(pfx1, pmy1, linewidth=4, marker="o", label="CH1", zorder=2)
        for f, m in zip(pfx1, pmy1):
            plt.annotate(f"{f:.2f} Hz", (f, m), textcoords="offset points", xytext=(0, 8), ha="center")

    if len(pfx2) > 0:
        plt.plot(pfx2, pmy2, linewidth=4, linestyle="--", marker="o", alpha=0.8, label="CH2", zorder=3)
        for f, m in zip(pfx2, pmy2):
            plt.annotate(f"{f:.2f} Hz", (f, m), textcoords="offset points", xytext=(0, -14), ha="center")

    if f0 is not None and np.isfinite(f0) and f0 > 0:
        plt.axvline(f0, linestyle=":", linewidth=2.5, label=f"shared dominant {f0:.3f} Hz")

        xmax = min(freqs[-1], max(5 * f0, 2 * f0))
        if xmax > 0:
            plt.xlim(0, xmax)

    plt.title(f"FFT - First {NUM_PEAKS_TO_SHOW} Peaks")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("FFT Magnitude")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath, format="pdf", bbox_inches="tight")
    plt.close()


def main():
    print(f"Using file: {FILE}")
    if not FILE.exists():
        raise FileNotFoundError(f"CSV file not found: {FILE}")

    df = load_keysight_csv(FILE)

    t = df["time_s"].to_numpy(dtype=float)
    ch1 = df["ch1_v"].to_numpy(dtype=float)
    ch2 = df["ch2_v"].to_numpy(dtype=float)

    fft1 = compute_fft(t, ch1)
    fft2 = compute_fft(t, ch2)

    freqs = fft1["freqs"]
    mag1 = fft1["mag"].copy()
    mag2 = fft2["mag"].copy()

    if len(mag1) > 0:
        mag1[0] = 0.0
    if len(mag2) > 0:
        mag2[0] = 0.0

    dom_idx, dom_freq = dominant_frequency_from_both(freqs, mag1, mag2)

    phase1_deg = np.degrees(np.angle(fft1["fft"][dom_idx]))
    phase2_deg = np.degrees(np.angle(fft2["fft"][dom_idx]))
    phase_diff_deg = wrap_phase_deg(phase2_deg - phase1_deg)

    period_s = 1.0 / dom_freq if dom_freq > 0 else np.nan
    time_delay_s = phase_diff_deg / 360.0 / dom_freq if dom_freq > 0 else np.nan

    stats1 = channel_stats(ch1, dom_freq, phase1_deg)
    stats2 = channel_stats(ch2, dom_freq, phase2_deg)

    save_time_plot(t, ch1, "Time Domain - Channel 1", "Voltage (V)", OUTDIR / "ch1_time.pdf")
    save_time_plot(t, ch2, "Time Domain - Channel 2", "Voltage (V)", OUTDIR / "ch2_time.pdf")
    save_time_overlay_plot(t, ch1, ch2, OUTDIR / "both_channels_time.pdf")
    save_fft_overlay_plot(freqs, mag1, mag2, OUTDIR / "both_channels_fft.pdf", dom_freq)

    summary = pd.DataFrame([
        {"channel": "CH1", **stats1},
        {"channel": "CH2", **stats2},
    ])
    summary.to_csv(OUTDIR / "channel_summary.csv", index=False)

    report_lines = [
        f"Input file: {FILE}",
        f"Samples: {len(df)}",
        f"Sample interval dt: {fft1['dt']:.12e} s",
        f"Sample rate fs: {fft1['fs']:.6f} Hz",
        "",
        "=== CH1 ===",
        f"Mean voltage:        {stats1['mean_v']:.9f} V",
        f"Min voltage:         {stats1['min_v']:.9f} V",
        f"Max voltage:         {stats1['max_v']:.9f} V",
        f"Peak-to-peak:        {stats1['peak_to_peak_v']:.9f} V",
        f"Amplitude:           {stats1['amplitude_v']:.9f} V",
        f"RMS total:           {stats1['rms_total_v']:.9f} V",
        f"RMS AC:              {stats1['rms_ac_v']:.9f} V",
        f"Dominant frequency:  {stats1['frequency_hz']:.9f} Hz",
        f"Period:              {stats1['period_s']:.12e} s",
        f"Phase:               {stats1['phase_deg']:.6f} deg",
        "",
        "=== CH2 ===",
        f"Mean voltage:        {stats2['mean_v']:.9f} V",
        f"Min voltage:         {stats2['min_v']:.9f} V",
        f"Max voltage:         {stats2['max_v']:.9f} V",
        f"Peak-to-peak:        {stats2['peak_to_peak_v']:.9f} V",
        f"Amplitude:           {stats2['amplitude_v']:.9f} V",
        f"RMS total:           {stats2['rms_total_v']:.9f} V",
        f"RMS AC:              {stats2['rms_ac_v']:.9f} V",
        f"Dominant frequency:  {stats2['frequency_hz']:.9f} Hz",
        f"Period:              {stats2['period_s']:.12e} s",
        f"Phase:               {stats2['phase_deg']:.6f} deg",
        "",
        "=== RELATION BETWEEN CHANNELS ===",
        f"Shared dominant frequency: {dom_freq:.9f} Hz",
        f"Shared period:             {period_s:.12e} s",
        f"Phase difference CH2-CH1:  {phase_diff_deg:.6f} deg",
        f"Equivalent time delay:     {time_delay_s:.12e} s",
    ]

    report_path = OUTDIR / "analysis_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n".join(report_lines))
    print(f"\nSaved outputs to: {OUTDIR}")


if __name__ == "__main__":
    main()