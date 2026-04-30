#!/usr/bin/env python3
"""
Mini README
-----------
Purpose:
  Like limit_test_avg_3.py, but reports only RMS and Max for each line.
  Also includes a combined summary across all files.

Input:
  - One or more CSV files (looped prompt; Enter to quit)

Output:
  - Prints time summary plus AC line and per-channel RMS/Max for the test region.
  - Prints combined RMS/Max across all files.
"""

from pathlib import Path
import shlex
from datetime import datetime
import pandas as pd

# -------- Settings --------
CHANNELS = range(1, 9)
TEST_COLUMNS = [f"ch{ch}_power" for ch in CHANNELS]  # detect test when any channel is non-zero
AC_COLUMN = "ps_acLineWatts"
TIME_COLUMN = "timestamp"  # optional timestamp column

# -------- Selection --------
def prompt_metrics():
    options = [
        "AC line",
        "Power",
        "Voltage",
        "Current",
        "Impedance",
        "All",
    ]
    print("\nSelect metrics to analyze (comma separated):")
    for i, opt in enumerate(options, start=1):
        print(f"  {i}. {opt}")
    raw = input("Choice (e.g., 1,3,5 or 6 for All): ").strip().lower()
    if not raw:
        return ["All"]
    picks = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(options):
                picks.add(options[idx - 1])
    if not picks or "All" in picks:
        return ["All"]
    return list(picks)


def prompt_choice(label, options, allow_blank=False):
    while True:
        print(f"\n{label}")
        for i, opt in enumerate(options, start=1):
            print(f"  {i}. {opt}")
        raw = input("Select a number: ").strip()
        if allow_blank and raw == "":
            return None
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        idx = int(raw)
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print("Invalid selection.")
# -------- Analysis --------
def analyze_csv(csv_path, print_summary=True, selected=None):
    print(f"\n📄 Reading: {csv_path.name}")

    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # ---- Use only the power columns that exist in this file ----
    present_test_cols = [col for col in TEST_COLUMNS if col in df.columns]
    if not present_test_cols:
        print("❌ No channel power columns found for test detection.")
        return

    # ---- Handle timestamps ----
    if TIME_COLUMN in df.columns:
        t_raw = df[TIME_COLUMN]
        t_dt = pd.to_datetime(t_raw, errors="coerce")
    else:
        t_dt = pd.Series(range(len(df)))  # fallback to sample index

    # ---- Detect test region ----
    test_mask = (df[present_test_cols] != 0).any(axis=1)
    if not test_mask.any():
        print("❌ Test region not detected (ch1/ch2 never non-zero)")
        return

    test_indices = test_mask[test_mask].index
    start_i = test_indices[0]
    end_i = test_indices[-1]

    # ---- Slice test region ----
    df_test = df.iloc[start_i:end_i + 1]
    t_test = t_dt.iloc[start_i:end_i + 1]
    t_start = t_test.iloc[0]
    t_end = t_test.iloc[-1]
    total_time = (t_end - t_start).total_seconds() if hasattr(t_start, "to_pydatetime") else end_i - start_i

    pre_time = (t_start - t_dt.iloc[0]).total_seconds() if hasattr(t_start, "to_pydatetime") else start_i
    post_time = (t_dt.iloc[-1] - t_end).total_seconds() if hasattr(t_start, "to_pydatetime") else len(df) - 1 - end_i

    if print_summary:
        print("\n========= TIME SUMMARY =========")
        print(f"Start time       : {t_start}")
        print(f"End time         : {t_end}")
        print(f"Pre-test duration: {pre_time:.1f} s")
        print(f"Test duration    : {total_time:.1f} s")
        print(f"Post-test duration: {post_time:.1f} s")
        print("=================================")

    selected = selected or ["All"]

    def _include(name):
        return "All" in selected or name in selected

    def _series_stats(series):
        series = pd.to_numeric(series, errors="coerce").dropna()
        if series.empty:
            return None
        nonzero = series[series.abs() > 0]
        if nonzero.empty:
            return None
        rms = (nonzero.pow(2).mean()) ** 0.5
        return {
            "avg": series.mean(),
            "rms": rms,
            "max": series.max(),
        }

    # ---- Optional time filter ----
    cutoff_time = getattr(analyze_csv, "cutoff_time", None)
    cutoff_side = getattr(analyze_csv, "cutoff_side", None)
    if cutoff_time is not None and TIME_COLUMN in df.columns:
        t_test_dt = pd.to_datetime(t_test, errors="coerce")
        if cutoff_side == "before":
            mask = t_test_dt <= cutoff_time
        else:
            mask = t_test_dt >= cutoff_time
        df_test = df_test.loc[mask]
        t_test = t_test.loc[mask]

    # ---- Stats ----
    stats = {}
    if _include("AC line") and AC_COLUMN in df_test.columns:
        ac_stats = _series_stats(df_test[AC_COLUMN])
        if ac_stats:
            stats[AC_COLUMN] = ac_stats
            if print_summary:
                print(
                    f"AC Line: Avg = {ac_stats['avg']:.2f} W | "
                    f"RMS = {ac_stats['rms']:.2f} W | Max = {ac_stats['max']:.2f} W"
                )

    # ---- Channel stats ----
    for ch in CHANNELS:
        for suffix, label, unit in [
            ("power", "Power", "W"),
            ("voltage", "Voltage", "V"),
            ("current", "Current", "A"),
            ("impedance", "Impedance", "Ω"),
        ]:
            if not _include(label):
                continue
            col = f"ch{ch}_{suffix}"
            if col not in df_test.columns:
                continue
            c_stats = _series_stats(df_test[col])
            if not c_stats:
                continue
            stats[col] = c_stats
            if print_summary:
                print(
                    f"{col}: Avg = {c_stats['avg']:.2f} {unit} | "
                    f"RMS = {c_stats['rms']:.2f} {unit} | Max = {c_stats['max']:.2f} {unit}"
                )

    if print_summary:
        print("===========================================\n")
    return stats


# -------- Main Loop --------
if __name__ == "__main__":
    print("\n📂 Drop a CSV file or a folder of CSVs to analyze (Enter to quit)\n")

    while True:
        try:
            user_input = input("Path: ").strip()
        except KeyboardInterrupt:
            print("\n👋 Exiting")
            break

        if not user_input:
            print("👋 Exiting")
            break

        # Support a single file or folder path (with escaped spaces).
        raw_parts = shlex.split(user_input.strip())
        if not raw_parts:
            print("❌ Please drop a CSV file or a folder")
            continue
        if len(raw_parts) > 1:
            print("❌ Please provide a single file or folder path")
            continue

        target = Path(raw_parts[0])
        paths = []

        if target.is_dir():
            paths = sorted(p for p in target.rglob("*.csv") if p.is_file())
            if not paths:
                print(f"❌ No CSV files found in folder: {target}")
                continue
            print(f"📁 Found {len(paths)} CSV file(s) in: {target}")
        elif target.is_file() and target.suffix.lower() == ".csv":
            paths = [target]
        else:
            print(f"❌ Not a CSV file or folder: {target}")
            continue

        # Optional time split
        if TIME_COLUMN in pd.read_csv(paths[0], nrows=1).columns:
            split_raw = input("Optional split timestamp (YYYY-MM-DD HH:MM:SS or HH:MM:SS, Enter to skip): ").strip()
            if split_raw:
                cutoff_time = None
                try:
                    # Time-only input (HH:MM or HH:MM:SS)
                    if (":" in split_raw) and ("-" not in split_raw) and ("T" not in split_raw):
                        first_ts = pd.read_csv(paths[0], usecols=[TIME_COLUMN], nrows=1)[TIME_COLUMN].iloc[0]
                        first_dt = pd.to_datetime(
                            first_ts,
                            errors="coerce",
                            format="%Y-%m-%dT%H:%M:%S.%f",
                        )
                        if pd.isna(first_dt):
                            first_dt = pd.to_datetime(first_ts, errors="coerce")
                        if pd.isna(first_dt):
                            raise ValueError("Could not parse first timestamp")
                        try:
                            t = datetime.strptime(split_raw, "%H:%M:%S").time()
                        except ValueError:
                            t = datetime.strptime(split_raw, "%H:%M").time()
                        cutoff_time = pd.Timestamp.combine(first_dt.date(), t)
                    else:
                        cutoff_time = pd.to_datetime(split_raw, errors="coerce")
                except Exception:
                    cutoff_time = None

                if cutoff_time is None or pd.isna(cutoff_time):
                    print("❌ Invalid timestamp; skipping time filter.")
                    analyze_csv.cutoff_time = None
                    analyze_csv.cutoff_side = None
                else:
                    side = prompt_choice("Average which side?", ["Before", "After"], allow_blank=False)
                    analyze_csv.cutoff_time = cutoff_time
                    analyze_csv.cutoff_side = side.lower()
            else:
                analyze_csv.cutoff_time = None
                analyze_csv.cutoff_side = None
        else:
            analyze_csv.cutoff_time = None
            analyze_csv.cutoff_side = None

        selected = prompt_metrics()
        per_file = []
        for path in paths:
            stats = analyze_csv(path, print_summary=(len(paths) == 1), selected=selected)
            if stats is not None:
                per_file.append(stats)

        if not per_file:
            continue

        if len(per_file) > 1:
            # ---- Combined report across all files ----
            rms_lists = {}
            max_lists = {}
            avg_lists = {}
            for stats in per_file:
                for col, vals in stats.items():
                    rms_lists.setdefault(col, []).append(vals["rms"])
                    max_lists.setdefault(col, []).append(vals["max"])
                    avg_lists.setdefault(col, []).append(vals["avg"])

            print("\n========= COMBINED SUMMARY =========")

            if AC_COLUMN in rms_lists:
                rms_avg = sum(rms_lists[AC_COLUMN]) / len(rms_lists[AC_COLUMN])
                avg_avg = sum(avg_lists[AC_COLUMN]) / len(avg_lists[AC_COLUMN])
                max_of_max = max(max_lists[AC_COLUMN])
                print(
                    f"AC Line (all files): Avg = {avg_avg:.2f} W | "
                    f"RMS = {rms_avg:.2f} W | Max = {max_of_max:.2f} W"
                )

            for ch in CHANNELS:
                for suffix, unit in [
                    ("power", "W"),
                    ("voltage", "V"),
                    ("current", "A"),
                    ("impedance", "Ω"),
                ]:
                    col = f"ch{ch}_{suffix}"
                    if col not in rms_lists:
                        continue
                    rms_avg = sum(rms_lists[col]) / len(rms_lists[col])
                    avg_avg = sum(avg_lists[col]) / len(avg_lists[col])
                    max_of_max = max(max_lists[col])
                    print(
                        f"{col} (all files): Avg = {avg_avg:.2f} {unit} | "
                        f"RMS = {rms_avg:.2f} {unit} | Max = {max_of_max:.2f} {unit}"
                    )

            print("==========================================\n")
