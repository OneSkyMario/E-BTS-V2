from pathlib import Path
import csv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# =========================================================
# USER SETTINGS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "flickering_4ms"     # change as needed
OUTPUT_ROOT = BASE_DIR / "plots_thicker_lines"  # change as needed

SKIP_ANAL_FILES = True
MAX_FREQ_TO_DISPLAY = None   # e.g. 500

# =========================================================
# HELPERS
# =========================================================
def try_float(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None

def read_rows(path: Path):
    with open(path, "r", newline="", errors="ignore") as f:
        return list(csv.reader(f))

def find_data_region(rows):
    header_idx = None
    numeric_start_idx = None

    for i, row in enumerate(rows):
        cells = [str(c).strip() for c in row if str(c).strip() != ""]
        if not cells:
            continue

        lower = [c.lower() for c in cells]
        if any("time" in c for c in lower) and len(cells) >= 2:
            header_idx = i
            break

    if header_idx is not None:
        return header_idx, True

    for i, row in enumerate(rows):
        vals = [try_float(c) for c in row]
        numeric_count = sum(v is not None for v in vals)
        if numeric_count >= 2:
            numeric_start_idx = i
            break

    if numeric_start_idx is None:
        raise ValueError("Could not find numeric waveform data in file.")

    return numeric_start_idx, False

def load_waveform_csv(path: Path) -> pd.DataFrame:
    rows = read_rows(path)
    start_idx, has_header = find_data_region(rows)

    if has_header:
        header = [str(c).strip() for c in rows[start_idx]]
        data_rows = rows[start_idx + 1:]
        df = pd.DataFrame(data_rows, columns=header)
    else:
        data_rows = rows[start_idx:]
        max_len = max(len(r) for r in data_rows)
        padded = [r + [""] * (max_len - len(r)) for r in data_rows]
        df = pd.DataFrame(padded, columns=[f"col{i}" for i in range(max_len)])

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(axis=1, how="all")
    valid_counts = df.notna().sum(axis=1)
    df = df.loc[valid_counts >= 2].copy().reset_index(drop=True)

    if df.shape[1] < 2:
        raise ValueError("Need at least time + one signal column.")
    if df.shape[0] < 2:
        raise ValueError("Not enough waveform rows.")

    return df

def choose_time_and_channels(df: pd.DataFrame):
    cols = list(df.columns)
    lower_cols = [c.lower() for c in cols]

    time_col = None
    for c, lc in zip(cols, lower_cols):
        if "time" in lc:
            time_col = c
            break

    if time_col is None:
        for c in cols:
            x = df[c].dropna().to_numpy()
            if len(x) > 5 and np.all(np.diff(x[: min(len(x), 100)]) >= 0):
                time_col = c
                break

    if time_col is None:
        time_col = cols[0]

    signal_candidates = [c for c in cols if c != time_col]

    preferred = []
    for c in signal_candidates:
        lc = c.lower()
        if "chan" in lc or "ch" in lc or "volt" in lc or "trace" in lc:
            preferred.append(c)

    if len(preferred) >= 2:
        signal_cols = preferred[:2]
    else:
        good = []
        for c in signal_candidates:
            s = df[c].std(skipna=True)
            if pd.notna(s) and s > 0:
                good.append(c)
        signal_cols = good[:2]

    if len(signal_cols) < 2:
        raise ValueError("Could not identify two waveform channels.")

    return time_col, signal_cols[0], signal_cols[1]

def centered(x):
    x = np.asarray(x, dtype=float)
    return x - np.mean(x)

def normalized(x):
    x = centered(x)
    s = np.std(x, ddof=1)
    return x / s if s > 0 else x

def estimate_fs(t):
    dt = np.diff(t)
    dt = dt[dt > 0]
    if len(dt) == 0:
        return np.nan
    return 1.0 / np.median(dt)

def dominant_frequency(x, fs):
    x = centered(x)
    N = len(x)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)
    X = np.fft.rfft(x)
    mag = np.abs(X)
    if len(mag) > 0:
        mag[0] = 0.0
    k = int(np.argmax(mag))
    return freqs, X, float(freqs[k]), k

def wrap_deg(a):
    return ((a + 180.0) % 360.0) - 180.0

def crosscorr_lag(x, y):
    x0 = centered(x)
    y0 = centered(y)
    corr = np.correlate(x0, y0, mode="full")
    lag = int(np.argmax(corr) - (len(x0) - 1))
    return lag, corr
def crop_to_first_n_cycles(t, y, n_cycles=4):
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(y) < 3:
        return t, y

    peak_idx = []
    for i in range(1, len(y) - 1):
        if y[i] > y[i - 1] and y[i] >= y[i + 1]:
            peak_idx.append(i)

    if len(peak_idx) < n_cycles + 1:
        return t, y

    peak_idx = np.array(peak_idx)
    end_idx = peak_idx[n_cycles]
    return t[:end_idx + 1], y[:end_idx + 1]
# =========================================================
# PDF PLOTTING HELPERS
# =========================================================
def save_single_pdf(t, y, title, ylabel, out_path, max_time_s=None):
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    if max_time_s is not None:
        mask = t <= max_time_s
        t_plot = t[mask]
        y_plot = y[mask]
    else:
        t_plot = t
        y_plot = y

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(t_plot, y_plot, linewidth=4.0)
    ax.set_title(title)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="pdf")
    plt.close(fig)

def save_overlay_pdf(t, y1, y2, label1, label2, title, ylabel, out_path):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(t, y1, linewidth=4.0, label=label1)
    ax.plot(t, y2, linewidth=4.0, label=label2)
    ax.set_title(title)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="pdf")
    plt.close(fig)

def save_fft_pdf(freqs1, X1, freqs2, X2, f_shared, out_path, label1, label2):
    mag1 = np.abs(X1).copy()
    mag2 = np.abs(X2).copy()
    if len(mag1) > 0:
        mag1[0] = 0.0
    if len(mag2) > 0:
        mag2[0] = 0.0

    x1 = freqs1
    y1 = mag1
    x2 = freqs2
    y2 = mag2

    if MAX_FREQ_TO_DISPLAY is not None:
        m1 = x1 <= MAX_FREQ_TO_DISPLAY
        m2 = x2 <= MAX_FREQ_TO_DISPLAY
        x1, y1 = x1[m1], y1[m1]
        x2, y2 = x2[m2], y2[m2]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(x1, y1, linewidth=4.0, label=label1)
    ax.plot(x2, y2, linewidth=4.0, label=label2)
    ax.axvline(f_shared, linestyle="--", linewidth=4.0, label=f"shared peak {f_shared:.3f} Hz")
    ax.set_title("FFT magnitude comparison")
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("FFT magnitude")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="pdf")
    plt.close(fig)

def save_combined_report_pdf(
    out_path, t, y1, y2, y1c, y2c, y1n, y2n,
    freqs1, X1, freqs2, X2, f_shared, summary_text
):
    with PdfPages(out_path) as pdf:
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(t, y1, linewidth=4.0)
        ax.set_title("Channel 1 raw")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Voltage [V]")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(t, y2, linewidth=4.0)
        ax.set_title("Channel 2 raw")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Voltage [V]")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(t, y1c, linewidth=4.0, label="Channel 1 centered")
        ax.plot(t, y2c, linewidth=4.0, label="Channel 2 centered")
        ax.set_title("Centered overlay")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Centered voltage [V]")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(t, y1n, linewidth=4.0, label="Channel 1 normalized")
        ax.plot(t, y2n, linewidth=4.0, label="Channel 2 normalized")
        ax.set_title("Centered + normalized overlay")
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Normalized amplitude [z-score]")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        mag1 = np.abs(X1).copy()
        mag2 = np.abs(X2).copy()
        if len(mag1) > 0:
            mag1[0] = 0.0
        if len(mag2) > 0:
            mag2[0] = 0.0

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(freqs1, mag1, linewidth=4.0, label="Channel 1")
        ax.plot(freqs2, mag2, linewidth=4.0, label="Channel 2")
        ax.axvline(f_shared, linestyle="--", linewidth=4.0, label=f"shared peak {f_shared:.3f} Hz")
        ax.set_title("FFT magnitude comparison")
        ax.set_xlabel("Frequency [Hz]")
        ax.set_ylabel("FFT magnitude")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(10, 6))
        plt.axis("off")
        plt.text(0.01, 0.99, summary_text, va="top", family="monospace", fontsize=10)
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

# =========================================================
# PROCESS ONE FILE
# =========================================================
def process_waveform_file(csv_path: Path, output_root: Path):
    print(f"Processing {csv_path.name}")

    df = load_waveform_csv(csv_path)
    time_col, ch1_col, ch2_col = choose_time_and_channels(df)

    t = df[time_col].to_numpy(dtype=float)
    y1 = df[ch1_col].to_numpy(dtype=float)
    y2 = df[ch2_col].to_numpy(dtype=float)

    mask = np.isfinite(t) & np.isfinite(y1) & np.isfinite(y2)
    t, y1, y2 = t[mask], y1[mask], y2[mask]

    if len(t) < 10:
        raise ValueError("Too few valid waveform samples after cleaning.")

    t = t - t[0]

    y1c = centered(y1)
    y2c = centered(y2)
    y1n = normalized(y1)
    y2n = normalized(y2)

    fs = estimate_fs(t)

    freqs1, X1, f1, _ = dominant_frequency(y1, fs)
    freqs2, X2, f2, _ = dominant_frequency(y2, fs)

    N = len(y1c)
    freqs_shared = np.fft.rfftfreq(N, d=1.0 / fs)
    A1 = np.fft.rfft(y1c)
    A2 = np.fft.rfft(y2c)
    avg_mag = (np.abs(A1) + np.abs(A2)) / 2.0
    if len(avg_mag) > 0:
        avg_mag[0] = 0.0
    k_shared = int(np.argmax(avg_mag))
    f_shared = float(freqs_shared[k_shared])

    phase1_deg = float(np.degrees(np.angle(A1[k_shared])))
    phase2_deg = float(np.degrees(np.angle(A2[k_shared])))
    phase_diff_deg = wrap_deg(phase2_deg - phase1_deg)

    lag_samples, _ = crosscorr_lag(y1, y2)
    lag_seconds = lag_samples / fs if np.isfinite(fs) and fs > 0 else np.nan
    corrcoef = float(np.corrcoef(y1c, y2c)[0, 1])

    out_dir = output_root / csv_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    processed = pd.DataFrame({
        "time_s": t,
        "ch1_raw": y1,
        "ch2_raw": y2,
        "ch1_centered": y1c,
        "ch2_centered": y2c,
        "ch1_normalized": y1n,
        "ch2_normalized": y2n,
    })
    processed.to_csv(out_dir / "processed_waveform.csv", index=False)

    save_single_pdf(
    t, y1,
    f"{csv_path.stem} - Channel 1 raw",
    "Voltage [V]",
    out_dir / "channel1_raw.pdf",
    max_time_s=0.03
)

    save_single_pdf(
    t, y2,
    f"{csv_path.stem} - Channel 2 raw",
    "Voltage [V]",
    out_dir / "channel2_raw.pdf",
    max_time_s=0.03
)

    save_overlay_pdf(
        t, y1c, y2c,
        "Channel 1 centered", "Channel 2 centered",
        f"{csv_path.stem} - Centered overlay",
        "Centered voltage [V]",
        out_dir / "overlay_centered.pdf"
    )

    save_overlay_pdf(
        t, y1n, y2n,
        "Channel 1 normalized", "Channel 2 normalized",
        f"{csv_path.stem} - Centered + normalized overlay",
        "Normalized amplitude [z-score]",
        out_dir / "overlay_centered_normalized.pdf"
    )

    save_fft_pdf(
        freqs1, X1, freqs2, X2, f_shared,
        out_dir / "fft_comparison.pdf",
        "Channel 1", "Channel 2"
    )

    summary = f"""File: {csv_path.name}
Detected columns:
  time   = {time_col}
  ch1    = {ch1_col}
  ch2    = {ch2_col}

Samples: {len(t)}
Estimated sampling rate: {fs:.6f} Hz

Channel 1:
  mean           = {np.mean(y1):.6f} V
  std            = {np.std(y1, ddof=1):.6f} V
  peak-to-peak   = {(np.max(y1)-np.min(y1)):.6f} V
  dominant freq  = {f1:.6f} Hz

Channel 2:
  mean           = {np.mean(y2):.6f} V
  std            = {np.std(y2, ddof=1):.6f} V
  peak-to-peak   = {(np.max(y2)-np.min(y2)):.6f} V
  dominant freq  = {f2:.6f} Hz

Comparison:
  shared dominant frequency = {f_shared:.6f} Hz
  phase(channel2 - channel1)= {phase_diff_deg:.6f} deg
  corrcoef(centered)        = {corrcoef:.6f}
  xcorr lag                 = {lag_samples} samples
  xcorr lag                 = {lag_seconds:.9f} s
"""

    with open(out_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)

    save_combined_report_pdf(
        out_dir / "analysis_report.pdf",
        t, y1, y2, y1c, y2c, y1n, y2n,
        freqs1, X1, freqs2, X2, f_shared, summary
    )

    print(f"  saved -> {out_dir}")

# =========================================================
# MAIN
# =========================================================
def main():
    print("Current working dir :", Path.cwd())
    print("Script dir          :", BASE_DIR)
    print("INPUT_DIR           :", INPUT_DIR)
    print("INPUT_DIR resolved  :", INPUT_DIR.resolve())
    print("Exists?             :", INPUT_DIR.exists())
    print("Is dir?             :", INPUT_DIR.is_dir())

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.glob("*.csv"))
    if SKIP_ANAL_FILES:
        files = [f for f in files if "_anal" not in f.stem.lower()]

    if not files:
        print(f"No waveform CSV files found in {INPUT_DIR}")
        return

    for f in files:
        try:
            process_waveform_file(f, OUTPUT_ROOT)
        except Exception as e:
            print(f"Failed on {f.name}: {e}")

    print("Done.")

if __name__ == "__main__":
    main()