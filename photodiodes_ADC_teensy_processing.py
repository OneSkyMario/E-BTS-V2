import csv
import time
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports

PORT = "COM8"
BAUD = 115200
OUTPUT_DIR = Path("D:/")

DURATION_SECONDS = 10

print("Available ports:")
for p in serial.tools.list_ports.comports():
    print(f"{p.device} - {p.description}")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
filename = OUTPUT_DIR / f"teensy_log_{datetime.now():%Y%m%d_%H%M%S}.csv"

print(f"\nTrying to open {PORT}...")

with serial.Serial(PORT, BAUD, timeout=0.2) as ser, open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "pc_time_s",
        "idx",
        "teensy_t_us",
        "raw1", "raw2", "raw3", "raw4", "raw5",
        "idx_jump",
        "missing_frames"
    ])

    # Give USB serial a moment, then clear old data
    time.sleep(2.0)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Optional handshake check
    ser.write(b"PING\n")
    time.sleep(0.1)

    # Clear any READY/PONG text before starting
    startup_lines = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.5:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            startup_lines.append(line)

    if startup_lines:
        print("Startup lines:")
        for line in startup_lines:
            print("  ", line)

    # Send START and wait for ACK_START
    print("Sending START...")
    ser.write(b"START\n")
    ser.flush()

    got_ack_start = False
    got_header = False

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 2.0:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if not line:
            continue
        print("Teensy:", line)
        if line == "ACK_START":
            got_ack_start = True
        elif line == "idx,t_us,raw1,raw2,raw3,raw4,raw5":
            got_header = True
        if got_ack_start and got_header:
            break

    if not got_ack_start:
        raise RuntimeError("Did not receive ACK_START from Teensy.")

    start_pc = time.perf_counter()
    deadline_pc = start_pc + DURATION_SECONDS

    samples_logged = 0
    total_missing = 0
    bad_lines = 0

    prev_idx = None
    prev_t_us = None

    sum_dt_us = 0
    dt_count = 0
    min_dt_us = None
    max_dt_us = None

    print(f"Logging to {filename}")
    print(f"Will stop after {DURATION_SECONDS} seconds")

    while True:
        now_pc = time.perf_counter()
        if now_pc >= deadline_pc:
            print("Time limit reached.")
            break

        line = ser.readline().decode("ascii", errors="ignore").strip()

        if not line:
            continue

        if line in ("ACK_START", "ACK_STOP", "READY", "PONG"):
            continue

        if line == "idx,t_us,raw1,raw2,raw3,raw4,raw5":
            continue

        parts = line.split(',')
        if len(parts) != 7:
            bad_lines += 1
            if bad_lines <= 10:
                print(f"BAD[{bad_lines}] {repr(line)}")
            continue

        try:
            idx = int(parts[0])
            t_us = int(parts[1])
            raw1 = int(parts[2])
            raw2 = int(parts[3])
            raw3 = int(parts[4])
            raw4 = int(parts[5])
            raw5 = int(parts[6])
        except ValueError:
            bad_lines += 1
            if bad_lines <= 10:
                print(f"BAD[{bad_lines}] parse fail: {repr(line)}")
            continue

        pc_time_s = now_pc - start_pc

        idx_jump = 0
        missing_frames = 0
        if prev_idx is not None:
            idx_jump = idx - prev_idx
            if idx_jump > 1:
                missing_frames = idx_jump - 1
                total_missing += missing_frames

        if prev_t_us is not None:
            dt_us = t_us - prev_t_us
            if dt_us >= 0:
                sum_dt_us += dt_us
                dt_count += 1
                if min_dt_us is None or dt_us < min_dt_us:
                    min_dt_us = dt_us
                if max_dt_us is None or dt_us > max_dt_us:
                    max_dt_us = dt_us

        writer.writerow([
            f"{pc_time_s:.6f}",
            idx,
            t_us,
            raw1, raw2, raw3, raw4, raw5,
            idx_jump,
            missing_frames
        ])

        prev_idx = idx
        prev_t_us = t_us
        samples_logged += 1

        if samples_logged % 500 == 0:
            f.flush()
            print(f"Samples: {samples_logged} | Missing: {total_missing} | Bad: {bad_lines}")

    # Tell Teensy to stop too
    ser.write(b"STOP\n")
    ser.flush()

    # Read a little more to catch ACK_STOP
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.5:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print("Teensy:", line)

    f.flush()

elapsed_s = time.perf_counter() - start_pc
rx_rate_hz = samples_logged / elapsed_s if elapsed_s > 0 else 0.0

if dt_count > 0:
    avg_dt_us = sum_dt_us / dt_count
    teensy_rate_hz = 1_000_000.0 / avg_dt_us if avg_dt_us > 0 else 0.0
else:
    avg_dt_us = 0.0
    teensy_rate_hz = 0.0

print("\nDone.")
print(f"Saved file: {filename}")
print(f"Samples logged: {samples_logged}")
print(f"Elapsed PC time [s]: {elapsed_s:.6f}")
print(f"Received rate on PC [Hz]: {rx_rate_hz:.3f}")
print(f"Total missing frames: {total_missing}")
print(f"Bad lines: {bad_lines}")
print(f"Average Teensy dt [us]: {avg_dt_us:.3f}")
print(f"Estimated Teensy sample rate [Hz]: {teensy_rate_hz:.3f}")
print(f"Min Teensy dt [us]: {min_dt_us}")
print(f"Max Teensy dt [us]: {max_dt_us}")