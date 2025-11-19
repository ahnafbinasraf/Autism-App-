# Frustraiton.py  — per-test frustration scoring
# - Reads learner_log{learner_id}.csv produced by AutismApp
# - Partitions rows by test_number
# - Writes one frustration score row per test into frustration_report{learner_id}.csv

import csv
import os
from collections import defaultdict
from datetime import datetime
import statistics

NEGATIVE_EMOTIONS = {"angry", "disgust", "fear", "sad"}
NEUTRAL_EMOTION = "neutral"

# -------------------------------
# Helpers
# -------------------------------

def _to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"true", "1", "yes", "y"}

def _read_log_grouped_by_test(log_file):
    """
    Returns:
      learner_id (str),
      tests (dict[int, list[dict]]) where each item has parsed fields.
    """
    if not os.path.exists(log_file):
        return None, {}

    tests = defaultdict(list)
    learner_id_found = None

    with open(log_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                learner_id = str(row["learner_id"])
                test_number = int(row["test_number"])
                mode = row.get("mode", "")
                question = row.get("question", "")
                rt = float(row.get("response_time_sec", 0.0))
                correct = _to_bool(row.get("correct", "false"))
                skipped = _to_bool(row.get("skipped", "false"))
                emotion = str(row.get("emotion", "Unknown")).strip().lower()
            except Exception:
                # Skip malformed rows quietly
                continue

            learner_id_found = learner_id or learner_id_found

            tests[test_number].append({
                "mode": mode,
                "question": question,
                "response_time": rt,
                "correct": correct,
                "skipped": skipped,
                "emotion": emotion,
            })

    return learner_id_found, dict(tests)

def _existing_tests_in_report(output_file, learner_id):
    """
    Read existing report and return the set of test_numbers already written
    for this learner_id, so we don't duplicate when re-running.
    """
    existing = set()
    if not os.path.exists(output_file):
        return existing

    with open(output_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("learner_id", "")) == str(learner_id):
                try:
                    existing.add(int(row["test_number"]))
                except Exception:
                    pass
    return existing

def _ensure_report_header(output_file):
    file_exists = os.path.exists(output_file)
    if not file_exists:
        with open(output_file, "w", newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["learner_id", "test_number", "timestamp", "mode", "frustration_score", "notes"])

# -------------------------------
# Improved scoring (per test)
# -------------------------------

def _compute_test_frustration(entries):
    """
    A smoother, research-aligned score in [0,1]:

    Components (averaged over entries):
      - Error rate (incorrect or skipped) -> err_rate
      - Response-time pressure relative to per-test baseline -> rt_norm
      - Negative valence prevalence (emotion) -> valence

    Final score = smoothstep( 0.45*err_rate + 0.25*rt_norm + 0.30*valence )
    where smoothstep(x) = 3x^2 - 2x^3 to emphasize high-frustration tails.
    """

    if not entries:
        return 0.0, "Low frustration"

    # Per-test baseline RT = median of correct & non-skipped RTs; if unavailable, use overall median or 10s
    rts_correct = [e["response_time"] for e in entries if e["correct"] and not e["skipped"]]
    rts_all = [e["response_time"] for e in entries if not e["skipped"]]
    if len(rts_correct) >= 2:
        baseline = statistics.median(rts_correct)
    elif rts_all:
        baseline = statistics.median(rts_all)
    else:
        baseline = 10.0  # fallback like the original script

    n = len(entries)
    # Error/skip component
    err_count = sum(1 for e in entries if (e["skipped"] or not e["correct"]))
    err_rate = err_count / n

    # RT component: values > baseline map to (0..1) with cap at +150% over baseline
    rt_excess = []
    for e in entries:
        if e["skipped"]:
            continue
        rt = e["response_time"]
        if baseline <= 0:
            rt_excess.append(0.0)
        elif rt <= baseline:
            rt_excess.append(0.0)
        else:
            # how far above baseline; 0 -> on/below baseline, 1 -> +150% or more
            rt_excess.append(min((rt - baseline) / (baseline * 1.5), 1.0))
    rt_norm = sum(rt_excess) / max(1, len(rt_excess))

    # Emotion component: negative=1.0, neutral=0.4, positive/other=0.0 (average across entries)
    emo_vals = []
    for e in entries:
        emo = (e["emotion"] or "").lower()
        if emo in NEGATIVE_EMOTIONS:
            emo_vals.append(1.0)
        elif emo == NEUTRAL_EMOTION:
            emo_vals.append(0.4)
        else:
            emo_vals.append(0.0)
    valence = sum(emo_vals) / n

    # Weighted combination + smoothstep
    s = 0.45 * err_rate + 0.25 * rt_norm + 0.30 * valence
    score = 3 * s * s - 2 * s * s * s  # smoothstep in [0,1]

    # Notes (same thresholds as before)
    if score > 0.75:
        note = "High frustration"
    elif score > 0.4:
        note = "Moderate frustration"
    else:
        note = "Low frustration"

    return round(score, 2), note

# -------------------------------
# Public entry point
# -------------------------------

def compute_frustration_per_test(log_file, output_file):
    """
    For each test_number found in the learner log, write ONE row per test to the report.
    Avoids duplicates by skipping tests that are already in the report for that learner.
    """
    learner_id, tests = _read_log_grouped_by_test(log_file)
    if learner_id is None or not tests:
        print(f"No data in {log_file}.")
        return

    _ensure_report_header(output_file)
    already = _existing_tests_in_report(output_file, learner_id)

    rows = []
    for test_number in sorted(tests):
        if test_number in already:
            continue  # skip previously scored tests
        entries = tests[test_number]
        score, note = _compute_test_frustration(entries)
        
        # Get mode from first entry (all entries in a test should have same mode)
        mode = entries[0]["mode"] if entries else "unknown"
        
        rows.append([learner_id, test_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mode, score, note])

    if not rows:
        print(f"No new tests to score for learner {learner_id}.")
        return

    with open(output_file, "a", newline="", encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Wrote {len(rows)} test score(s) to {output_file}")

# -------------------------------
# CLI-style batch runner (kept)
# -------------------------------

if __name__ == "__main__":
    # Keep your original batch idea: iterate learner ids 1..99 as filenames.
    # Example files: learner_log1.csv -> frustration_report1.csv, etc.
    for i in range(1, 100):
        learner = str(i)
        log_file = f"learner_log{learner}.csv"
        out_file = f"frustration_report{learner}.csv"
        if os.path.exists(log_file):
            compute_frustration_per_test(log_file, out_file)
