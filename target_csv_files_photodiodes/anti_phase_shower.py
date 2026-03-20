from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "teensy_log_20260308_012238.csv"

df = pd.read_csv(CSV_PATH)

# show ~5 cycles
df = df[df["pc_time_s"] <= 0.04].copy()

t = df["pc_time_s"]
ch1 = df["raw1"].astype(float)
ch5 = df["raw5"].astype(float)

# center signals
ch1 = ch1 - ch1.mean()
ch5 = -(ch5 - ch5.mean())   # invert channel 5

plt.figure(figsize=(8,4))

plt.plot(
    t, ch1,
    color="0.2",           # dark gray
    linewidth=4.0,
    linestyle="-",
    label="Channel 1"
)

plt.plot(
    t, ch5,
    color="0.6",           # light gray
    linewidth=4.0,
    linestyle="--",
    label="Channel 5 (inverted)"
)

plt.xlabel("Time (s)")
plt.ylabel("Centered ADC Value")

plt.legend(frameon=False)

plt.tight_layout()
plt.show()

plt.savefig("antiphase_plot.pdf", bbox_inches="tight")