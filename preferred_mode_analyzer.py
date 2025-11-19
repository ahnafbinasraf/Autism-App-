#!/usr/bin/env python3
"""
Preferred Mode Analyzer

This script analyzes frustration reports to determine which learning mode
(visual, auditory, kinesthetic) produces the lowest frustration scores for each learner.
It then saves the preferred mode for each learner to a CSV file.

Usage:
    python preferred_mode_analyzer.py [frustration_report_file] [output_file]
    
    If no arguments provided, it will process all frustration_report*.csv files
    and save to preferred_modes.csv
"""

import csv
import os
import sys
from collections import defaultdict
import glob


def _normalize_mode_name(raw_mode: str) -> str:
    """Normalize mode labels and collapse synonyms.
    Internal computation uses 'visual', 'auditory', 'kinesthetic'.
    """
    m = (raw_mode or "").strip().lower()
    if m in {"interactive", "kinaesthetic", "hands-on", "hands on", "kinesthetics"}:
        return "kinesthetic"
    if m in {"visual", "auditory", "kinesthetic"}:
        return m
    # Fallback: return as-is so we can see unexpected labels during printing
    return m


def analyze_frustration_by_mode(frustration_file):
    """
    Analyze frustration scores by mode for each learner.
    
    Args:
        frustration_file (str): Path to frustration report CSV file
        
    Returns:
        dict: Nested dict {learner_id: {mode: [scores]}}
    """
    learner_mode_scores = defaultdict(lambda: defaultdict(list))
    
    if not os.path.exists(frustration_file):
        print(f"Warning: Frustration file not found: {frustration_file}")
        return learner_mode_scores
    
    try:
        with open(frustration_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check if the file has the new format with mode column
            if reader.fieldnames is None or 'mode' not in reader.fieldnames:
                print(f"Warning: File {frustration_file} doesn't have 'mode' column. Skipping.")
                return learner_mode_scores
            
            for row in reader:
                learner_id = row['learner_id']
                mode_raw = row['mode']
                mode = _normalize_mode_name(mode_raw)
                try:
                    frustration_score = float(row['frustration_score'])
                except Exception:
                    # skip bad values
                    continue
                learner_mode_scores[learner_id][mode].append(frustration_score)
                
    except Exception as e:
        print(f"Error reading {frustration_file}: {e}")
        
    return learner_mode_scores


def find_preferred_modes(learner_mode_scores):
    """
    Find the preferred mode (lowest average frustration) for each learner.
    
    Args:
        learner_mode_scores (dict): Nested dict {learner_id: {mode: [scores]}}
        
    Returns:
        dict: {learner_id: preferred_mode}
    """
    preferred_modes = {}
    
    for learner_id, mode_scores in learner_mode_scores.items():
        if not mode_scores:
            continue
            
        mode_averages = {}
        for mode, scores in mode_scores.items():
            if scores:
                mode_averages[mode] = sum(scores) / len(scores)
        
        if mode_averages:
            # Find mode with lowest average frustration
            preferred_mode = min(mode_averages.keys(), key=lambda k: mode_averages[k])
            preferred_modes[learner_id] = {
                'preferred_mode': preferred_mode,
                'avg_frustration': mode_averages[preferred_mode],
                'mode_scores': mode_averages
            }
            
            print(f"Learner {learner_id}:")
            for mode, avg_score in sorted(mode_averages.items()):
                marker = "*" if mode == preferred_mode else " "
                print(f"  {marker} {mode}: {avg_score:.3f}")
            print(f"  Preferred: {preferred_mode} (frustration: {mode_averages[preferred_mode]:.3f})")
            print()
    
    return preferred_modes


def save_preferred_modes(preferred_modes, output_file):
    """
    Save preferred modes to CSV file.
    
    Args:
        preferred_modes (dict): {learner_id: {preferred_mode, avg_frustration, ...}}
        output_file (str): Path to output CSV file
    """
    if not preferred_modes:
        print("Warning: No preferred modes to save.")
        return
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['learner_id', 'preferred_mode', 'avg_frustration'])
            
            # Write data using canonical labels expected by apps
            for learner_id, data in preferred_modes.items():
                out_label = data['preferred_mode']  # keep 'kinesthetic' as 'kinesthetic'
                writer.writerow([
                    learner_id, 
                    out_label, 
                    f"{data['avg_frustration']:.3f}"
                ])
        
        print(f"Saved preferred modes for {len(preferred_modes)} learner(s) to {output_file}")
        
    except Exception as e:
        print(f"Error saving to {output_file}: {e}")


def process_single_file(frustration_file, output_file):
    """Process a single frustration report file."""
    print(f"Analyzing frustration report: {frustration_file}")
    
    # Analyze frustration by mode
    learner_mode_scores = analyze_frustration_by_mode(frustration_file)
    
    if not learner_mode_scores:
        print("Warning: No data found to analyze.")
        return
    
    # Find preferred modes
    preferred_modes = find_preferred_modes(learner_mode_scores)
    
    # Save results
    save_preferred_modes(preferred_modes, output_file)


def process_all_files():
    """Process all frustration_report*.csv files in current directory."""
    frustration_files = glob.glob("frustration_report*.csv")
    
    if not frustration_files:
        print("Warning: No frustration_report*.csv files found in current directory.")
        return
    
    all_learner_mode_scores = defaultdict(lambda: defaultdict(list))
    
    print(f"Found {len(frustration_files)} frustration report file(s)")
    
    # Combine data from all files
    for file in frustration_files:
        print(f"  Processing {file}")
        learner_mode_scores = analyze_frustration_by_mode(file)
        
        # Merge data
        for learner_id, mode_scores in learner_mode_scores.items():
            for mode, scores in mode_scores.items():
                all_learner_mode_scores[learner_id][mode].extend(scores)
    
    if not all_learner_mode_scores:
        print("Warning: No data found to analyze.")
        return
    
    # Find preferred modes
    preferred_modes = find_preferred_modes(all_learner_mode_scores)
    
    # Save results
    save_preferred_modes(preferred_modes, "preferred_modes.csv")


def main():
    """Main function."""
    print("Preferred Mode Analyzer")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        # No arguments - process all files
        process_all_files()
    elif len(sys.argv) == 3:
        # Two arguments - specific input and output files
        frustration_file = sys.argv[1]
        output_file = sys.argv[2]
        process_single_file(frustration_file, output_file)
    else:
        print("Usage:")
        print("  python preferred_mode_analyzer.py                    # Process all frustration_report*.csv")
        print("  python preferred_mode_analyzer.py <input> <output>   # Process specific file")
        sys.exit(1)


if __name__ == "__main__":
    main()
