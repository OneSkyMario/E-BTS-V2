import pandas as pd
from pathlib import Path
import plotly.graph_objects as go

# =========================
# User settings
# =========================
INPUT_CSV = Path(r"teensy_log_20260308_012238.csv")   # change this
OUTPUT_DIR = Path(r"processed_logs")                  # change if needed

VREF = 3.3
ADC_MAX = 4095.0   # 12-bit ADC

# If True, crop everything up to and including the last startup discontinuity
ENABLE_CROP = True

# =========================
# Setup
# =========================
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

processed_csv_path = OUTPUT_DIR / f"{INPUT_CSV.stem}_processed.csv"
plot_html_path = OUTPUT_DIR / f"{INPUT_CSV.stem}_plot.html"

# =========================
# Load data
# =========================
df = pd.read_csv(INPUT_CSV)

required_cols = ["idx", "teensy_t_us", "raw1", "raw2", "raw3", "raw4", "raw5"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing required column: {col}")

# =========================
# Crop startup artifact
# =========================
crop_start = 0

if ENABLE_CROP:
    if "missing_frames" in df.columns:
        bad_idxs = df.index[df["missing_frames"] > 0].tolist()
        if bad_idxs:
            crop_start = bad_idxs[-1] + 1
    elif "idx_jump" in df.columns:
        bad_idxs = df.index[df["idx_jump"] > 1].tolist()
        if bad_idxs:
            crop_start = bad_idxs[-1] + 1

df = df.iloc[crop_start:].copy().reset_index(drop=True)

if len(df) == 0:
    raise ValueError("No data left after cropping.")

# =========================
# Re-zero index and time
# =========================
df["idx"] = df["idx"] - int(df["idx"].iloc[0])
df["teensy_t_us"] = df["teensy_t_us"] - int(df["teensy_t_us"].iloc[0])

if "pc_time_s" in df.columns:
    df["pc_time_s"] = df["pc_time_s"] - float(df["pc_time_s"].iloc[0])

df["time_s"] = df["teensy_t_us"] / 1_000_000.0

# =========================
# Convert raw ADC counts to voltage
# =========================
raw_cols = ["raw1", "raw2", "raw3", "raw4", "raw5"]
voltage_cols = []

for i, raw_col in enumerate(raw_cols, start=1):
    v_col = f"voltage{i}"
    df[v_col] = df[raw_col] * (VREF / ADC_MAX)
    voltage_cols.append(v_col)

# =========================
# Save processed CSV
# =========================
df.to_csv(processed_csv_path, index=False)

# =========================
# Interactive plot
# =========================
fig = go.Figure()

for i, v_col in enumerate(voltage_cols, start=1):
    fig.add_trace(
        go.Scatter(
            x=df["time_s"],
            y=df[v_col],
            mode="lines",
            name=f"Photodiode {i}",
            hovertemplate="Time = %{x:.6f} s<br>Voltage = %{y:.6f} V<extra></extra>"
        )
    )

buttons = []

# Show all
buttons.append(
    dict(
        label="Show all",
        method="update",
        args=[
            {"visible": [True, True, True, True, True]},
            {"title": "Photodiode voltages vs time"}
        ]
    )
)

# Show one at a time
for i in range(5):
    visible = [False] * 5
    visible[i] = True
    buttons.append(
        dict(
            label=f"Photodiode {i+1}",
            method="update",
            args=[
                {"visible": visible},
                {"title": f"Photodiode {i+1} voltage vs time"}
            ]
        )
    )

fig.update_layout(
    title="Photodiode voltages vs time",
    xaxis_title="Time [s]",
    yaxis_title="Voltage [V]",
    hovermode="x unified",
    updatemenus=[
        dict(
            type="dropdown",
            direction="down",
            buttons=buttons,
            x=1.02,
            y=1.0,
            xanchor="left",
            yanchor="top"
        )
    ],
    legend_title="Channels"
)

fig.write_html(plot_html_path, include_plotlyjs=True)

# =========================
# Summary
# =========================
print("Processing complete.")
print(f"Input file: {INPUT_CSV}")
print(f"Cropped initial rows: {crop_start}")
print(f"Remaining rows: {len(df)}")
print(f"Processed CSV saved to: {processed_csv_path}")
print(f"Interactive plot saved to: {plot_html_path}")

# Optional quick stats
for i, v_col in enumerate(voltage_cols, start=1):
    print(
        f"{v_col}: min={df[v_col].min():.6f} V, "
        f"max={df[v_col].max():.6f} V, "
        f"mean={df[v_col].mean():.6f} V"
    )