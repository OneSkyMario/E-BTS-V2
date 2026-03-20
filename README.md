```
 ████████╗ █████╗  ██████╗ ████████╗ ██╗ ██╗      ███████╗      ██╗       █████╗  ██████╗ 
 ╚══██╔══╝██╔══██╗██╔════  ╚══██╔══╝ ██║ ██║      ██╔════╝      ██║      ██╔══██╗ ██╔══██╗
    ██║   ███████║██║         ██║    ██║ ██║      █████╗        ██║      ███████║ ██████╔╝
    ██║   ██╔══██║██║         ██║    ██║ ██║      ██╔══╝        ██║      ██╔══██║ ██╔══██╗
    ██║   ██║  ██║╚██████╗    ██║    ██║ ███████╗ ███████╗      ███████╗ ██║  ██║ ██████╔╝
    ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═╝ ╚══════╝ ╚══════╝      ╚══════╝ ╚═╝  ╚═╝ ╚═════╝ 
```

Maintained by Zaki Al-Farabi, Airis Corolla, Dimash, Amir Yelenov





# ICCA_2026_EBTS

Workspace for data collection, signal analysis, and figure generation for the **E-BTS / ICCA 2026** experiments.

This directory contains oscilloscope recordings, photodiode logs, processed outputs, plotting scripts, and exploratory leftovers used during development and paper preparation.

## Overview

This workspace appears to support validation and analysis of:

- anti-phase LED modulation
- constant vs. flickering signal behavior
- photodiode acquisition using a Teensy
- oscilloscope verification of waveform timing and phase
- intermediate processing and plotting for publication figures

This is best treated as a **research working directory**, not a polished software package. It contains raw data, intermediate files, generated plots, legacy experiments, and utility scripts.

## Important note about missing data

A large video file was intentionally removed from this compressed archive to reduce size:

- `Chronos_leftovers/vid_2026-03-06_17-26-50.mp4`

Because of that, this uploaded archive is **not a fully lossless copy** of the original working directory. The remaining contents still include CSV results and analysis artifacts, but the original video is absent from this compressed version.

## Top-level structure

```text
ICCA_2026_EBTS/
├── Chronos_leftovers/
├── Oscilliscope_Readings_EBTS/
├── photodiode_analysis/
├── photoresistor_leftovers/
├── processed_logs/
├── retinex/
├── target_csv_files_photodiodes/
├── photodiodes_ADC_post_processing.py
└── photodiodes_ADC_teensy_processing.py
```

## Folder descriptions

### `Chronos_leftovers/`
Contains leftover results associated with Chronos-related processing.

Current contents include:
- `Results_zoneA.csv`
- `Results_zoneB.csv`
- `Results_zoneC_intersection.csv`

These appear to be region-based measurement outputs or extracted signal summaries from Chronos recordings.

**Important:** the original large source video
`vid_2026-03-06_17-26-50.mp4`
was removed before compression and is therefore not included here.

### `Oscilliscope_Readings_EBTS/`
Main oscilloscope analysis workspace.

Contains:
- raw oscilloscope CSV captures
- constant-signal and flickering-signal experiments
- analysis scripts
- generated PDF plots
- processed summaries
- an `old/` folder with earlier experiments and previous output sets

Key subfolders include:
- `constant_4ms/`
- `constant_60ms/`
- `flickering_4ms/`
- `flickering_60ms/`
- `plots/`
- `plots_thicker_lines/`
- `plots_top_mid/`
- `plots_4ms_top_mid_bot/`
- `plots_60ms_top_mid_bot/`
- `old/`

Key scripts include:
- `oscil_anal_constant.py` — processes constant-signal oscilloscope data and generates plots / summaries.
- `oscill_analysis_flickering.py` — analyzes two-channel flickering data, including overlay and FFT comparisons.
- `double_chan_flickering_plot.py` — lightweight plotting utility for dual-channel flickering visualization.

This folder appears to be the main location for validating:
- waveform period
- phase offset
- frequency content
- figure generation for the paper

### `photodiode_analysis/`
Contains processed outputs for photodiode experiments.

Each subfolder stores analysis products for a specific Teensy log, such as:
- raw voltage plots
- centered voltage plots
- normalized trace plots
- FFT plots
- phase heatmaps
- correlation heatmaps
- processed CSV files
- summary CSV files

The current archive contains analysis outputs for at least:
- `teensy_log_20260308_012212`
- `teensy_log_20260308_012238`

Most outputs here are HTML visualizations plus processed tables.

### `photoresistor_leftovers/`
Contains older or exploratory CSV logs that do not appear to be part of the finalized workflow.

Useful mainly as:
- backup raw logs
- discarded trials
- preliminary experiments

### `processed_logs/`
Stores processed Teensy log outputs, including:
- processed CSV files
- HTML plots
- raw voltage visualizations
- centered voltage visualizations
- PSD plots
- summary CSV files

This folder appears to be the output destination for post-processing scripts that convert raw ADC logs into cleaner analysis-ready data.

### `retinex/`
Small image-processing experiment folder.

Contains:
- `input.jpg`
- `output.jpg`
- `Retinex_anal`

The script applies **Single Scale Retinex (SSR)** using OpenCV for illumination / contrast enhancement. This appears exploratory and separate from the main signal-processing pipeline.

### `target_csv_files_photodiodes/`
Contains selected target photodiode CSV files and small plotting / phase-check utilities.

Key files include:
- `teensy_log_20260308_012212.csv`
- `teensy_log_20260308_012238.csv`
- `plotter.py`
- `anti_phase_shower.py`
- several PDF plots for early-window visualization

This folder appears to collect the main photodiode CSV files used for focused analysis or figure generation.

## Root-level scripts

### `photodiodes_ADC_teensy_processing.py`
Python script for **logging photodiode ADC data from a Teensy** over serial.

Main behavior:
- opens a serial connection to the Teensy
- performs a simple handshake (`PING`, `START`, `STOP`)
- writes logs to CSV
- records index jumps and missing-frame counts
- tracks timing and estimated sampling statistics

Current script-specific settings include:
- serial port: `COM8`
- baud rate: `115200`
- output directory: `D:/`
- logging duration: `10` seconds

These values should be edited before reuse on another machine.

### `photodiodes_ADC_post_processing.py`
Python script for **post-processing logged photodiode CSV files**.

Main behavior:
- loads a Teensy CSV log
- optionally crops startup artifacts
- re-zeros index and time
- converts ADC counts to voltages
- saves a processed CSV
- generates an interactive Plotly HTML visualization

Important defaults currently include:
- input file: `teensy_log_20260308_012238.csv`
- output directory: `processed_logs`
- reference voltage: `3.3 V`
- ADC resolution: `12-bit` (`4095` max count)

## Suggested workflow

A rough workflow implied by this directory is:

1. acquire raw photodiode data from the Teensy
2. save the acquisition as a timestamped CSV log
3. post-process the log into voltage traces and plots
4. validate signal timing and phase using oscilloscope captures
5. generate PDF / HTML figures for reporting or paper writing
6. use selected target files for focused comparisons and publication figures

## Requirements

The scripts in this directory appear to use the following Python packages:

- `pandas`
- `numpy`
- `matplotlib`
- `plotly`
- `pyserial`
- `opencv-python`

Install them with:

```bash
pip install pandas numpy matplotlib plotly pyserial opencv-python
```

## Notes on reproducibility

This directory contains a mixture of:
- raw data
- generated outputs
- older experiments
- one-off analysis scripts
- machine-specific paths and settings

So reproducibility may require:
- updating hardcoded file paths
- changing the serial port
- selecting the intended input CSV manually
- regenerating figures from raw CSV files
- separating legacy outputs from final figures

## Suggested cleanup

If this folder is going to be shared publicly or archived long-term, it may help to reorganize it into clearer sections such as:

- `raw_data/`
- `processed_data/`
- `figures/`
- `scripts/`
- `legacy/`
- `notes/`

That would make the project easier to navigate, reproduce, and hand off to someone else.

## Status

This archive is a **compressed working snapshot** of the ICCA 2026 E-BTS analysis directory.

It is useful for reviewing experiments, scripts, and generated outputs, but it should not be assumed to contain every original raw asset.

Most notably, the following large source file was removed before compression:

- `Chronos_leftovers/vid_2026-03-06_17-26-50.mp4`
