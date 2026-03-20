from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

p = Path(__file__).resolve().parent / "flickering_60ms/60ms_1_5.csv"

df = pd.read_csv(p)
df = df.iloc[1:].copy()
df.columns = ["time_s", "ch1", "ch2"]
df = df.astype(float)
df = df[(df["time_s"] >= 0) & (df["time_s"] <= 0.3)].copy()

# Flip sign so values plot positive before normalization
df["ch1"] = -df["ch1"]
df["ch2"] = -df["ch2"]

# Center + normalize (z-score)
df["ch1n"] = (df["ch1"] - df["ch1"].mean()) / df["ch1"].std()
df["ch2n"] = (df["ch2"] - df["ch2"].mean()) / df["ch2"].std()

plt.figure(figsize=(12, 6))
plt.plot(df["time_s"], df["ch1n"], color="0.15", linestyle="-",  linewidth=4.0, label="Channel 1 normalized")
plt.plot(df["time_s"], df["ch2n"], color="0.55", linestyle="--", linewidth=4.0, label="Channel 2 normalized")

plt.xlabel("Time [s]")
plt.ylabel("Normalized amplitude [z-score]")
plt.title("4ms_1_5 - First 0.03 s centered + normalized overlay")
plt.grid(True, alpha=0.25)
plt.legend(frameon=True, facecolor="white", edgecolor="black")
plt.tight_layout()
plt.savefig(p.with_name("60ms_1_5_first_30ms_normalized_overlay.pdf"), format="pdf", bbox_inches="tight")
plt.show()