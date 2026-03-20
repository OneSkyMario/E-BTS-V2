from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent

DATASETS = [
    {
        "input_dir": BASE_DIR / "constant_60ms",
        "output_dir": BASE_DIR / "plots_ms_top_mid_bot",
        "prefix": "4ms",
        "channels": ["top", "mid", "bot"],
    },
    {
        "input_dir": BASE_DIR / "constant_60ms",
        "output_dir": BASE_DIR / "plots_60ms_top_mid_bot",
        "prefix": "60ms",
        "channels": ["top", "mid", "bot"],
    },
]


def find_data_start(lines):
    number_re = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")

    for i, line in enumerate(lines):
        matches = number_re.findall(line)
        if len(matches) >= 2:
            return i

    raise ValueError("Could not find waveform data rows in file.")


def parse_waveform_file(path: Path) -> pd.DataFrame:
    print(f"Reading: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    start_idx = find_data_start(lines)
    data_lines = lines[start_idx:]

    rows = []
    number_re = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")

    for line in data_lines:
        nums = number_re.findall(line)
        if len(nums) < 2:
            continue

        try:
            t = float(nums[0])
            v = float(nums[1])
            rows.append((t, v))
        except ValueError:
            continue

    if not rows:
        raise ValueError(f"No numeric waveform rows parsed from {path}")

    df = pd.DataFrame(rows, columns=["time_s", "voltage_V"])
    df = df.dropna(subset=["time_s", "voltage_V"]).reset_index(drop=True)

    if df.empty:
        raise ValueError(f"Parsed dataframe is empty for {path}")

    print(f"  Parsed rows: {len(df)}")
    return df


def align_multiple_dataframes(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    min_len = min(len(df) for df in dfs.values())
    if min_len == 0:
        raise ValueError("At least one waveform has zero valid rows.")

    return {name: df.iloc[:min_len].copy() for name, df in dfs.items()}


def center_signal(x: np.ndarray) -> np.ndarray:
    return x - np.mean(x)


def normalize_signal(x: np.ndarray) -> np.ndarray:
    std = np.std(x)
    if std == 0:
        return np.zeros_like(x)
    return (x - np.mean(x)) / std


def compute_fft(time_s: np.ndarray, signal: np.ndarray):
    if len(time_s) < 2:
        raise ValueError("Need at least 2 samples for FFT.")

    dt = np.median(np.diff(time_s))
    if dt <= 0:
        raise ValueError("Non-positive time step detected.")

    y = signal - np.mean(signal)
    freqs = np.fft.rfftfreq(len(y), d=dt)
    mags = np.abs(np.fft.rfft(y))
    return freqs, mags


def save_line_plot(x, ys, labels, title, xlabel, ylabel, out_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4.8))

    for y, label in zip(ys, labels):
        if label.lower().startswith("bot"):
            ax.plot(x, y, linewidth=3.0, linestyle="--", alpha=0.85, label=label)
        else:
            ax.plot(x, y, linewidth=3.0, label=label)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    if len(labels) > 1:
        ax.legend()

    fig.tight_layout()
    fig.savefig(out_path, format="pdf")
    plt.close(fig)
    print(f"Saved: {out_path}")


def summarize_channel(name: str, v: np.ndarray) -> dict:
    return {
        "channel": name,
        "mean_V": float(np.mean(v)),
        "std_V": float(np.std(v)),
        "min_V": float(np.min(v)),
        "max_V": float(np.max(v)),
        "peak_to_peak_V": float(np.max(v) - np.min(v)),
    }


def write_summary_txt(out_path: Path, dt, fs, stats_list):
    lines = [
        "Oscilloscope Summary",
        "====================",
        "",
        f"Estimated dt [s]: {dt:.9e}",
        f"Estimated fs [Hz]: {fs:.3f}",
        "",
    ]

    for stats in stats_list:
        lines.append(f"{stats['channel']} channel:")
        for k, v in stats.items():
            if k != "channel":
                lines.append(f"  {k}: {v}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {out_path}")


def process_dataset(input_dir: Path, output_dir: Path, prefix: str, channels: list[str]):
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing dataset: {prefix}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    dfs = {}
    for ch in channels:
        path = input_dir / f"{prefix}_{ch}.csv"
        dfs[ch] = parse_waveform_file(path)

    dfs = align_multiple_dataframes(dfs)

    ref_channel = channels[0]
    t = dfs[ref_channel]["time_s"].to_numpy(dtype=float)
    t = t - t[0]

    raw_signals = {}
    centered_signals = {}
    normalized_signals = {}
    fft_freqs = {}
    fft_mags = {}
    stats_list = []

    for ch in channels:
        v = dfs[ch]["voltage_V"].to_numpy(dtype=float)
        raw_signals[ch] = v
        centered_signals[ch] = center_signal(v)
        normalized_signals[ch] = normalize_signal(v)

        f, m = compute_fft(t, v)
        fft_freqs[ch] = f
        fft_mags[ch] = m

        stats_list.append(summarize_channel(ch, v))

    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt

    processed_df = pd.DataFrame({"time_s": t})
    for ch in channels:
        processed_df[f"{ch}_V"] = raw_signals[ch]
        processed_df[f"{ch}_centered_V"] = centered_signals[ch]
        processed_df[f"{ch}_normalized"] = normalized_signals[ch]

    processed_df.to_csv(output_dir / f"{prefix}_processed.csv", index=False)
    print(f"Saved: {output_dir / f'{prefix}_processed.csv'}")

    for ch in channels:
        save_line_plot(
            t,
            [raw_signals[ch]],
            [ch.capitalize()],
            f"{prefix} {ch} waveform",
            "Time [s]",
            "Voltage [V]",
            output_dir / f"{prefix}_{ch}_raw.pdf",
        )

    save_line_plot(
        t,
        [raw_signals[ch] for ch in channels],
        [ch.capitalize() for ch in channels],
        f"{prefix} overlay raw",
        "Time [s]",
        "Voltage [V]",
        output_dir / f"{prefix}_overlay_raw.pdf",
    )

    save_line_plot(
        t,
        [centered_signals[ch] for ch in channels],
        [f"{ch.capitalize()} centered" for ch in channels],
        f"{prefix} overlay centered",
        "Time [s]",
        "Centered voltage [V]",
        output_dir / f"{prefix}_overlay_centered.pdf",
    )

    save_line_plot(
        t,
        [normalized_signals[ch] for ch in channels],
        [f"{ch.capitalize()} normalized" for ch in channels],
        f"{prefix} overlay normalized",
        "Time [s]",
        "Normalized amplitude",
        output_dir / f"{prefix}_overlay_normalized.pdf",
    )

    save_line_plot(
        fft_freqs[channels[0]],
        [fft_mags[ch] for ch in channels],
        [f"{ch.capitalize()} FFT" for ch in channels],
        f"{prefix} FFT",
        "Frequency [Hz]",
        "Magnitude",
        output_dir / f"{prefix}_fft.pdf",
    )

    stats_df = pd.DataFrame(stats_list)
    stats_df.to_csv(output_dir / f"{prefix}_summary.csv", index=False)
    print(f"Saved: {output_dir / f'{prefix}_summary.csv'}")

    write_summary_txt(
        output_dir / f"{prefix}_summary.txt",
        dt,
        fs,
        stats_list,
    )


def main():
    for ds in DATASETS:
        try:
            process_dataset(
                input_dir=ds["input_dir"],
                output_dir=ds["output_dir"],
                prefix=ds["prefix"],
                channels=ds["channels"],
            )
        except Exception as e:
            print(f"Failed dataset {ds['prefix']}: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()