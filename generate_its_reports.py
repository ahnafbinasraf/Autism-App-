#!/usr/bin/env python3
"""
Generate Interrupted Time Series (ITS) plots showing frustration over time
with an intervention at the adaptive mode switch to the learner's preferred mode.

Inputs (already produced by the app):
  - learner_log{learner_id}.csv                    (main autism webapp per-question rows)
  - addition_practice_log{learner_id}.csv         (addition practice per-question rows)
  - subtraction_practice_log{learner_id}.csv      (subtraction practice per-question rows)
  - preferred_modes.csv                           (learner_id, preferred_mode)

Output:
  - outputs/its_learner_{learner_id}.png          (main autism webapp)
  - outputs/its_addition_{learner_id}.png          (addition practice)
  - outputs/its_subtraction_{learner_id}.png      (subtraction practice)

Notes:
  - This script is non-invasive. It only reads existing CSVs and writes plots.
  - Per-question frustration is computed from existing columns to approximate
    moment-to-moment affect (error/skip, response time, emotion valence).
"""

from __future__ import annotations

import os
import glob
import math
import csv
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


OUTPUT_DIR = os.path.join("outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


NEGATIVE_EMOTIONS = {"angry", "disgust", "fear", "sad", "frustrated"}
NEUTRAL_LABELS = {"neutral"}


def load_preferred_modes(path: str = "preferred_modes.csv") -> Dict[str, str]:
    modes: Dict[str, str] = {}
    if not os.path.exists(path):
        return modes
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lid = str(row.get("learner_id", "")).strip()
                mode = str(row.get("preferred_mode", "")).strip().lower()
                if mode == "interactive":
                    mode = "kinesthetic"
                if lid:
                    modes[lid] = mode
    except Exception:
        pass
    return modes


def compute_question_frustration(df: pd.DataFrame) -> pd.Series:
    """Compute a per-question frustration score in [0, 1].

    Components (weighted):
      - Error/skip: 1.0 if incorrect or skipped else 0.0
      - RT pressure: response time relative to the session median (on/under = 0,
        +150% or more over = 1)
      - Emotion valence: 1.0 for negative, 0.4 for neutral, 0.0 for positive/other

    Final score = 0.5*error + 0.2*rt_norm + 0.3*valence (clamped to [0,1])
    """
    # Error/skip
    incorrect_or_skipped = []
    for _, row in df.iterrows():
        correct = str(row.get("correct", "")).strip().lower() in {"true", "1", "yes"}
        skipped = str(row.get("skipped", "")).strip().lower() in {"true", "1", "yes"}
        incorrect_or_skipped.append(1.0 if (skipped or not correct) else 0.0)
    err = pd.Series(incorrect_or_skipped, index=df.index, dtype=float)

    # Response-time pressure - use plain Python to avoid pandas type issues
    rt_values = []
    for _, row in df.iterrows():
        rt_val = row.get("response_time_sec", None)
        try:
            rt_values.append(float(rt_val) if rt_val is not None else 0.0)
        except (ValueError, TypeError):
            rt_values.append(0.0)
    
    # Calculate median using numpy
    rt_array = np.array(rt_values)
    rt_med = float(np.nanmedian(rt_array)) if len(rt_array) > 0 else 0.0
    
    rt_norm_list: List[float] = []
    for val in rt_values:
        if isinstance(val, (int, float)) and not math.isnan(val) and rt_med > 0:
            if val <= rt_med:
                rt_norm_list.append(0.0)
            else:
                rt_norm_list.append(min((val - rt_med) / (rt_med * 1.5), 1.0))
        else:
            rt_norm_list.append(0.0)
    rt_norm = pd.Series(rt_norm_list, index=df.index, dtype=float)

    # Emotion valence
    emo_vals: List[float] = []
    for _, row in df.iterrows():
        emo = str(row.get("emotion", "")).strip().lower()
        if emo in NEGATIVE_EMOTIONS:
            emo_vals.append(1.0)
        elif emo in NEUTRAL_LABELS:
            emo_vals.append(0.4)
        else:
            emo_vals.append(0.0)
    valence = pd.Series(emo_vals, index=df.index, dtype=float)

    scores = 0.5 * err + 0.2 * rt_norm + 0.3 * valence
    return scores.clip(0.0, 1.0)


def find_intervention_index(df: pd.DataFrame, preferred_mode: str | None) -> int:
    """Return the 1-based index of the first question in the preferred mode.
    Fallback: the first detected mode switch; else midpoint of the series.
    """
    modes = []
    for _, row in df.iterrows():
        mode_val = row.get("mode", "")
        modes.append(str(mode_val).strip().lower())

    if preferred_mode:
        for i, m in enumerate(modes, start=1):
            if m == preferred_mode:
                return i

    # Fallback: first switch
    for i in range(1, len(modes)):
        if modes[i] != modes[i - 1]:
            return i + 1

    return max(1, len(modes) // 2)


def find_all_mode_switches(df: pd.DataFrame) -> List[Tuple[int, str, str]]:
    """Find all mode switches in the data.
    Returns list of (question_index, from_mode, to_mode) tuples.
    """
    modes = []
    for _, row in df.iterrows():
        mode_val = row.get("mode", "")
        modes.append(str(mode_val).strip().lower())
    
    switches = []
    for i in range(1, len(modes)):
        if modes[i] != modes[i - 1]:
            switches.append((i + 1, modes[i - 1], modes[i]))  # 1-based indexing
    
    return switches


def segmented_fit(x: np.ndarray, y: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit two lines (pre/post) split at index k (1-based). Return:
      y_fit (piecewise), y_pre_only (counterfactual extension), (b_pre, m_pre, b_post, m_post)
    """
    k = max(1, min(int(k), len(x)))
    # Pre segment includes the split point
    x_pre, y_pre = x[:k], y[:k]
    x_post, y_post = x[k-1:], y[k-1:]

    # Fit lines (degree 1)
    m_pre, b_pre = np.polyfit(x_pre, y_pre, 1)
    m_post, b_post = np.polyfit(x_post, y_post, 1)

    y_fit = np.empty_like(y)
    y_fit[:k] = m_pre * x_pre + b_pre
    y_fit[k:] = m_post * x[k:] + b_post

    # Counterfactual: extend pre trend across entire range
    y_pre_only = m_pre * x + b_pre

    return y_fit, y_pre_only, np.array([b_pre, m_pre, b_post, m_post])


def plot_its(learner_id: str, x: np.ndarray, y: np.ndarray, y_fit: np.ndarray, y_cf: np.ndarray,
             k: int, preferred_mode: str | None, path: str, session_type: str = "Main", 
             mode_switches: List[Tuple[int, str, str]] | None = None) -> None:
    plt.figure(figsize=(12, 8))
    # Observed
    plt.scatter(x, y, color="gray", alpha=0.6, label="Observed Frustration")
    # Fitted ITS
    plt.plot(x, y_fit, color="blue", linewidth=2.0, label="Fitted ITS")
    # Counterfactual
    plt.plot(x, y_cf, color="red", linewidth=2.0, linestyle="--", label="Counterfactual")
    
    # Main intervention line (preferred mode switch)
    plt.axvline(x[k-1], color="black", linewidth=3, alpha=0.8, label="Preferred Mode Switch")
    
    # Mode switch bars
    if mode_switches:
        colors = ['orange', 'green', 'purple', 'brown', 'pink']
        for i, (switch_idx, from_mode, to_mode) in enumerate(mode_switches):
            if switch_idx <= len(x):
                color = colors[i % len(colors)]
                plt.axvline(x[switch_idx-1], color=color, linewidth=2, alpha=0.7, 
                           linestyle=':', label=f"Mode Switch: {from_mode} → {to_mode}")

    title_mode = f" (preferred: {preferred_mode})" if preferred_mode else ""
    plt.title(f"ITS: Frustration vs Time - Learner {learner_id} - {session_type}{title_mode}")
    plt.xlabel("Question Index (time)")
    plt.ylabel("Frustration (0-1)")
    plt.legend(loc="upper left", fontsize=9)
    plt.ylim(0, 1.05)
    plt.grid(alpha=0.15)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def process_learner_log(log_path: str, preferred_mode: str | None, session_type: str = "Main") -> str | None:
    df = pd.read_csv(log_path, encoding="utf-8")
    if len(df) == 0:
        return None

    # Compute per-question frustration
    frustration = compute_question_frustration(df)
    # Time index
    x = np.arange(1, len(df) + 1, dtype=float)
    y = frustration.to_numpy(dtype=float)

    # Find all mode switches
    mode_switches = find_all_mode_switches(df)
    
    # Intervention index
    k = find_intervention_index(df, preferred_mode)

    # Fit segmented
    try:
        y_fit, y_cf, _params = segmented_fit(x, y, k)
    except Exception:
        # Fallback: flat fits if polyfit fails due to degenerate segments
        y_fit = np.full_like(y, float(np.nan))
        y_cf = np.full_like(y, float(np.nan))
        return None

    # Extract learner_id and determine output filename based on session type
    filename = os.path.basename(log_path)
    if "addition_practice_log" in filename:
        learner_id = filename.replace("addition_practice_log", "").replace(".csv", "")
        out_path = os.path.join(OUTPUT_DIR, f"its_addition_{learner_id}.png")
    elif "subtraction_practice_log" in filename:
        learner_id = filename.replace("subtraction_practice_log", "").replace(".csv", "")
        out_path = os.path.join(OUTPUT_DIR, f"its_subtraction_{learner_id}.png")
    else:
        learner_id = "unknown"
        out_path = os.path.join(OUTPUT_DIR, f"its_{session_type.lower()}_{learner_id}.png")
    
    plot_its(learner_id, x, y, y_fit, y_cf, k, preferred_mode, out_path, session_type, mode_switches)
    return out_path


def main() -> None:
    print("Starting ITS report generation...")
    modes = load_preferred_modes()
    print(f"Loaded preferred modes: {modes}")
    
    # Process only addition and subtraction practice logs
    all_log_files = []
    
    # Addition practice logs
    addition_logs = sorted(glob.glob("addition_practice_log*.csv"))
    print(f"Found addition logs: {addition_logs}")
    for log in addition_logs:
        all_log_files.append((log, "Addition Practice"))
    
    # Subtraction practice logs
    subtraction_logs = sorted(glob.glob("subtraction_practice_log*.csv"))
    print(f"Found subtraction logs: {subtraction_logs}")
    for log in subtraction_logs:
        all_log_files.append((log, "Subtraction Practice"))
    
    print(f"Total log files to process: {len(all_log_files)}")
    
    if not all_log_files:
        print("No practice log files found (addition_practice_log*.csv, subtraction_practice_log*.csv).")
        return

    generated: List[str] = []
    for log_path, session_type in all_log_files:
        print(f"Processing: {log_path} ({session_type})")
        # Extract learner_id from filename
        filename = os.path.basename(log_path)
        if "addition_practice_log" in filename:
            lid = filename.replace("addition_practice_log", "").replace(".csv", "")
        elif "subtraction_practice_log" in filename:
            lid = filename.replace("subtraction_practice_log", "").replace(".csv", "")
        else:
            lid = "unknown"
        
        print(f"Learner ID: {lid}")
        pref = modes.get(lid)
        print(f"Preferred mode: {pref}")
        out = process_learner_log(log_path, pref, session_type)
        if out:
            generated.append(out)
            print(f"Generated: {out}")
        else:
            print(f"Failed to generate plot for {log_path}")

    if generated:
        print("Generated ITS plots:")
        for p in generated:
            print(" - ", p)
    else:
        print("No plots generated (check CSV contents).")


if __name__ == "__main__":
    main()


