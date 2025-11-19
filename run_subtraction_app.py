#!/usr/bin/env python3
"""
Subtraction Learning App with Emotion Tracking
Following AutismApp.py logic for practice questions with camera initialization and emotion tracking
"""

import os
import sys
import webbrowser
import subprocess
import socket
import threading
import time
import csv
import random
import json
import argparse
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file, Response

# Import emotion tracking modules with fallback (same as autism webapp)
try:
    import emotion_tracker_webapp as emotion_tracker
    EMOTION_TRACKER_AVAILABLE = True
    print("Advanced emotion tracking loaded for subtraction practice")
except Exception as e:
    try:
        import emotion_tracker_simple as emotion_tracker
        EMOTION_TRACKER_AVAILABLE = True
        print("Simple emotion tracking loaded for subtraction practice")
    except Exception as e2:
        print(f"Using mock emotion tracking for subtraction practice: {e2}")
        EMOTION_TRACKER_AVAILABLE = False
        # Create mock emotion tracker
        class MockEmotionTracker:
            @staticmethod
            def start_emotion_tracking():
                return True
            @staticmethod
            def stop_emotion_tracking():
                emotions = ["neutral", "happy", "focused", "calm", "engaged", "sad", "frustrated"]
                return random.choice(emotions)
            @staticmethod
            def is_camera_ready():
                return True
        emotion_tracker = MockEmotionTracker()

try:
    import frustration_webapp
    FRUSTRATION_AVAILABLE = True
    print("Frustration analysis loaded for subtraction practice")
except Exception as e:
    print(f"Frustration analysis not available for subtraction practice: {e}")
    FRUSTRATION_AVAILABLE = False
    frustration_webapp = None  # Set to None if import fails

# Flask app setup
app = Flask(__name__)
app.secret_key = 'subtraction_practice_emotion_tracking_key'

# Session management for practice tracking
current_sessions = {}

# Inactivity tracking
_last_interaction_ts = {}
_monitor_threads = {}
_launched_addition = set()

# Load preferred modes from CSV
def load_preferred_modes():
    try:
        modes_dict = {}
        with open('preferred_modes.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                learner_id = int(row['learner_id'])
                preferred_mode = row['preferred_mode'].strip().lower()
                if preferred_mode == 'interactive':
                    preferred_mode = 'kinesthetic'
                modes_dict[learner_id] = preferred_mode
        return modes_dict
    except Exception as e:
        print(f"Warning: Could not load preferred modes: {e}")
        return {}

# Load inactivity threshold for learner
def _load_inactivity_threshold(learner_id: int, default_seconds: float = 120.0) -> float:
    try:
        # Optional override for testing
        env_override = os.environ.get('INACTIVITY_TEST_SECONDS')
        if env_override:
            try:
                seconds = float(env_override)
                print(f"[Inactivity] Using env override threshold: {seconds}s")
                return seconds
            except Exception:
                pass
        if os.path.exists('inactivity_thresholds.json'):
            with open('inactivity_thresholds.json', 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
                rec = data.get(str(learner_id))
                if rec and isinstance(rec.get('inactivity_threshold_sec'), (int, float)):
                    seconds = float(rec['inactivity_threshold_sec'])
                    print(f"[Inactivity] Loaded threshold for learner {learner_id}: {seconds}s")
                    return seconds
    except Exception:
        pass
    return default_seconds

# Mark user interaction
def _mark_interaction(learner_id: int):
    _last_interaction_ts[learner_id] = time.time()

# Check inactivity and cycle mode if threshold exceeded
def _check_inactivity_and_launch(learner_id: int):
    threshold = _load_inactivity_threshold(learner_id)
    last_ts = _last_interaction_ts.get(learner_id, time.time())
    elapsed = time.time() - last_ts
    remaining = threshold - elapsed
    
    # Debug output every 30 seconds
    if int(elapsed) % 30 == 0 and elapsed > 0:
        print(f"[Inactivity Debug] Learner {learner_id}: {elapsed:.1f}s since last interaction (threshold: {threshold}s, remaining: {remaining:.1f}s)")
    
    if remaining <= 0:
        # Only cycle mode once per learner when threshold is exceeded
        if learner_id not in _launched_addition:
            _launched_addition.add(learner_id)
            print(f"[Inactivity] Threshold exceeded for learner {learner_id} ({elapsed:.1f}s >= {threshold}s)")
            
            # Cycle preferred mode
            try:
                # Read current preferred mode
                preferred_modes = load_preferred_modes()
                current_mode = preferred_modes.get(learner_id, 'visual')
                
                # Cycle: visual -> kinesthetic -> auditory -> visual
                mode_cycle = {'visual': 'kinesthetic', 'kinesthetic': 'auditory', 'auditory': 'visual'}
                new_mode = mode_cycle.get(current_mode, 'visual')
                
                # Update preferred_modes.csv
                rows = []
                with open('preferred_modes.csv', 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if int(row['learner_id']) == learner_id:
                            row['preferred_mode'] = new_mode
                        rows.append(row)
                
                with open('preferred_modes.csv', 'w', encoding='utf-8', newline='') as file:
                    fieldnames = ['learner_id', 'preferred_mode']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                print(f"[Inactivity] Changed preferred mode from {current_mode} to {new_mode}")
                
                # Relaunch via a detached helper so current process can be killed safely
                print(f"[Inactivity] Scheduling safe restart of subtraction app...")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                helper_code = (
                    "import time,subprocess,sys,os,signal,platform,webbrowser;"
                    "def signal_handler(sig, frame): sys.exit(0);"
                    "signal.signal(signal.SIGINT, signal_handler);"
                    "signal.signal(signal.SIGTERM, signal_handler);"
                    "time.sleep(1);"
                    "plat=platform.system().lower();"
                    "if 'windows' in plat:"
                    "\n    ps=\"$p=(Get-NetTCPConnection -LocalPort 5003 -State Listen -ErrorAction SilentlyContinue).OwningProcess; if($p){taskkill /F /PID $p}\";"
                    "\n    subprocess.run(['powershell','-NoProfile','-Command', ps], check=False);"
                    "else:"
                    "\n    res=subprocess.run(['lsof','-ti:5003'],capture_output=True,text=True);"
                    "\n    pids=[p for p in res.stdout.strip().split('\\n') if p.strip()];"
                    "\n    [subprocess.run(['kill','-9',pid],check=False) for pid in pids];"
                    "time.sleep(2);"
                    f"proc=subprocess.Popen([sys.executable,'run_subtraction_app.py'], cwd=r'{base_dir}');"
                    "time.sleep(3);"
                    f"webbrowser.open('http://localhost:5003?learner_id={learner_id}');"
                    "proc.wait()"
                )
                try:
                    subprocess.Popen([sys.executable, "-c", helper_code])
                    print("[Inactivity] Helper spawned to restart and open browser.")
                except Exception as e:
                    print(f"[Inactivity] Failed to spawn helper: {e}")
                    
            except Exception as e:
                print(f"[Inactivity] Error cycling mode: {e}")

# Start inactivity monitoring
def _start_inactivity_monitor(learner_id: int):
    if learner_id in _monitor_threads:
        print(f"[Monitor] Already monitoring learner {learner_id}")
        return
    def _loop():
        print(f"[Monitor] Monitoring thread started for learner {learner_id}")
        check_count = 0
        while True:
            try:
                check_count += 1
                if check_count % 12 == 0:  # Every minute (12 * 5 seconds)
                    print(f"[Monitor] Still monitoring learner {learner_id} (check #{check_count})")
                _check_inactivity_and_launch(learner_id)
            except Exception as e:
                print(f"[Monitor] Error in monitoring loop: {e}")
            # Stop if addition already launched
            if learner_id in _launched_addition:
                print(f"[Monitor] Stopping monitoring for learner {learner_id} - restart launched")
                break
            time.sleep(5)
    t = threading.Thread(target=_loop, daemon=True)
    _monitor_threads[learner_id] = t
    t.start()
    print(f"[Monitor] Started monitoring thread for learner {learner_id}")

# Subtraction learning examples (before practice)
SUBTRACTION_EXAMPLES = {
    'visual': [
        {
            'title': 'Example 1: Visual Subtraction',
            'description': 'Show picture: 🍎🍎🍎 (3 apples). Take 1 away.',
            'teacher_text': '3 apples take away 1 apple leaves 2 apples.',
            'equation': '3 − 1 = 2',
            'visual_elements': ['🍎🍎🍎', '🍎', '🍎🍎']
        },
        {
            'title': 'Example 2: Visual Subtraction',
            'description': 'Show picture: ⭐⭐⭐⭐ (4 stars). Take 2 away.',
            'teacher_text': '4 stars take away 2 stars leaves 2 stars.',
            'equation': '4 − 2 = 2',
            'visual_elements': ['⭐⭐⭐⭐', '⭐⭐', '⭐⭐']
        },
        {
            'title': 'Example 3: Visual Subtraction',
            'description': 'Show picture: 🎈🎈🎈🎈🎈 (5 balloons). Take 3 away.',
            'teacher_text': '5 balloons take away 3 balloons leaves 2 balloons.',
            'equation': '5 − 3 = 2',
            'visual_elements': ['🎈🎈🎈🎈🎈', '🎈🎈🎈', '🎈🎈']
        },
        {
            'title': 'Example 4: Visual Subtraction',
            'description': 'Show picture: 🐟🐟🐟🐟🐟🐟 (6 fish). Take 4 away.',
            'teacher_text': '6 fish take away 4 fish leaves 2 fish.',
            'equation': '6 − 4 = 2',
            'visual_elements': ['🐟🐟🐟🐟🐟🐟', '🐟🐟🐟🐟', '🐟🐟']
        },
        {
            'title': 'Example 5: Visual Subtraction',
            'description': 'Show picture: 🐶🐶🐶🐶🐶🐶🐶 (7 dogs). Take 5 away.',
            'teacher_text': '7 dogs take away 5 dogs leaves 2 dogs.',
            'equation': '7 − 5 = 2',
            'visual_elements': ['🐶🐶🐶🐶🐶🐶🐶', '🐶🐶🐶🐶🐶', '🐶🐶']
        }
    ],
    'auditory': [
        {
            'title': 'Example 1: Auditory Subtraction',
            'description': 'Listen carefully: You have 6 candies. You eat 1. Now you have 5 left.',
            'teacher_text': '6 minus 1 equals 5.',
            'equation': '6 − 1 = 5',
            'audio_text': 'You have 6 candies. You eat 1 candy. Now you have 5 candies left.'
        },
        {
            'title': 'Example 2: Auditory Subtraction',
            'description': 'Listen carefully: You had 7 toys. You gave 2 away. Now 5 toys are left.',
            'teacher_text': '7 minus 2 equals 5.',
            'equation': '7 − 2 = 5',
            'audio_text': 'You had 7 toys. You gave 2 toys away. Now 5 toys are left.'
        },
        {
            'title': 'Example 3: Auditory Subtraction',
            'description': 'Listen carefully: You had 9 marbles. 4 rolled away. Now you have 5 marbles left.',
            'teacher_text': '9 minus 4 equals 5.',
            'equation': '9 − 4 = 5',
            'audio_text': 'You had 9 marbles. 4 marbles rolled away. Now you have 5 marbles left.'
        },
        {
            'title': 'Example 4: Auditory Subtraction',
            'description': 'Listen carefully: You had 8 cookies. You ate 3. Now you have 5 left.',
            'teacher_text': '8 minus 3 equals 5.',
            'equation': '8 − 3 = 5',
            'audio_text': 'You had 8 cookies. You ate 3 cookies. Now you have 5 cookies left.'
        },
        {
            'title': 'Example 5: Auditory Subtraction',
            'description': 'Listen carefully: You had 10 stickers. You gave 5 away. Now you have 5 left.',
            'teacher_text': '10 minus 5 equals 5.',
            'equation': '10 − 5 = 5',
            'audio_text': 'You had 10 stickers. You gave 5 stickers away. Now you have 5 stickers left.'
        }
    ],
    'kinesthetic': [
        {
            'title': 'Example 1: Kinesthetic Subtraction',
            'description': 'Drag 5 blocks 🟥🟥🟥🟥🟥 into the box. Now remove 2 🟥🟥.',
            'teacher_text': '5 minus 2 equals 3.',
            'equation': '5 − 2 = 3',
            'task': 'Drag 5 blocks 🟥🟥🟥🟥🟥 into the box. Now remove 2 blocks 🟥🟥. Count: 3 blocks left.',
            'counts': [5, 2, 3],
            'elements': ['🟥🟥🟥🟥🟥', '🟥🟥', '🟥🟥🟥']
        },
        {
            'title': 'Example 2: Kinesthetic Subtraction',
            'description': 'Move 8 stars ⭐⭐⭐⭐⭐⭐⭐⭐ into the box. Now take out 5 ⭐⭐⭐⭐⭐.',
            'teacher_text': '8 minus 5 equals 3.',
            'equation': '8 − 5 = 3',
            'task': 'Move 8 stars ⭐⭐⭐⭐⭐⭐⭐⭐ into the box. Now take out 5 stars ⭐⭐⭐⭐⭐. Count: 3 stars left.',
            'counts': [8, 5, 3],
            'elements': ['⭐⭐⭐⭐⭐⭐⭐⭐', '⭐⭐⭐⭐⭐', '⭐⭐⭐']
        },
        {
            'title': 'Example 3: Kinesthetic Subtraction',
            'description': 'Put 6 apples 🍎🍎🍎🍎🍎🍎 in the basket. Remove 4 🍎🍎🍎🍎.',
            'teacher_text': '6 minus 4 equals 2.',
            'equation': '6 − 4 = 2',
            'task': 'Put 6 apples 🍎🍎🍎🍎🍎🍎 in the basket. Remove 4 apples 🍎🍎🍎🍎. Count: 2 apples left.',
            'counts': [6, 4, 2],
            'elements': ['🍎🍎🍎🍎🍎🍎', '🍎🍎🍎🍎', '🍎🍎']
        },
        {
            'title': 'Example 4: Kinesthetic Subtraction',
            'description': 'Drag 7 balloons 🎈🎈🎈🎈🎈🎈🎈 into the area. Now pop 3 🎈🎈🎈.',
            'teacher_text': '7 minus 3 equals 4.',
            'equation': '7 − 3 = 4',
            'task': 'Drag 7 balloons 🎈🎈🎈🎈🎈🎈🎈 into the area. Now pop 3 balloons 🎈🎈🎈. Count: 4 balloons left.',
            'counts': [7, 3, 4],
            'elements': ['🎈🎈🎈🎈🎈🎈🎈', '🎈🎈🎈', '🎈🎈🎈🎈']
        },
        {
            'title': 'Example 5: Kinesthetic Subtraction',
            'description': 'Place 9 dots into the box. Now remove 6 dots.',
            'teacher_text': '9 minus 6 equals 3.',
            'equation': '9 − 6 = 3',
            'task': 'Place 9 dots ⚫⚫⚫⚫⚫⚫⚫⚫⚫ into the box. Now remove 6 dots ⚫⚫⚫⚫⚫⚫. Count: 3 dots left.',
            'counts': [9, 6, 3],
            'elements': ['⚫⚫⚫⚫⚫⚫⚫⚫⚫', '⚫⚫⚫⚫⚫⚫', '⚫⚫⚫']
        }
    ]
}

# Subtraction practice questions (with emotion tracking)
SUBTRACTION_PRACTICE = {
    'visual': [
        {
            'question': 'You see 3 cats 🐱🐱🐱. 1 cat 🐱 runs away. How many cats are left?',
            'answer': 2,
            'visual_elements': ['🐱🐱🐱', '🐱', '🐱🐱']
        },
        {
            'question': 'There are 6 stars ⭐⭐⭐⭐⭐⭐. Take away 2 stars ⭐⭐. How many now?',
            'answer': 4,
            'visual_elements': ['⭐⭐⭐⭐⭐⭐', '⭐⭐', '⭐⭐⭐⭐']
        },
        {
            'question': 'You see 5 balloons 🎈🎈🎈🎈🎈. 3 fly away 🎈🎈🎈. How many left?',
            'answer': 2,
            'visual_elements': ['🎈🎈🎈🎈🎈', '🎈🎈🎈', '🎈🎈']
        },
        {
            'question': 'You see 8 fish 🐟🐟🐟🐟🐟🐟🐟🐟. 5 swim away 🐟🐟🐟🐟🐟. How many left?',
            'answer': 3,
            'visual_elements': ['🐟🐟🐟🐟🐟🐟🐟🐟', '🐟🐟🐟🐟🐟', '🐟🐟🐟']
        },
        {
            'question': 'There are 7 apples 🍎🍎🍎🍎🍎🍎🍎. You eat 4 🍎🍎🍎🍎. How many apples left?',
            'answer': 3,
            'visual_elements': ['🍎🍎🍎🍎🍎🍎🍎', '🍎🍎🍎🍎', '🍎🍎🍎']
        }
    ],
    'auditory': [
        {
            'question': 'You had 4 cookies. You ate 1 cookie. How many left?',
            'answer': 3,
            'audio_text': 'You had 4 cookies. You ate 1 cookie. How many cookies are left?'
        },
        {
            'question': 'You had 7 toys. You gave 2 away. How many toys left?',
            'answer': 5,
            'audio_text': 'You had 7 toys. You gave 2 toys away. How many toys are left?'
        },
        {
            'question': 'You had 9 marbles. 3 rolled away. How many now?',
            'answer': 6,
            'audio_text': 'You had 9 marbles. 3 marbles rolled away. How many marbles do you have now?'
        },
        {
            'question': 'You had 6 candies. You ate 5. How many left?',
            'answer': 1,
            'audio_text': 'You had 6 candies. You ate 5 candies. How many candies are left?'
        },
        {
            'question': 'You had 5 pencils. You lost 2. How many pencils now?',
            'answer': 3,
            'audio_text': 'You had 5 pencils. You lost 2 pencils. How many pencils do you have now?'
        }
    ],
    'kinesthetic': [
        {
            'question': 'Main Box has 5 blocks 🟥🟥🟥🟥🟥. Remove 2 blocks 🟥🟥. How many blocks are left?',
            'answer': 3,
            'task': 'Main Box has 5 blocks 🟥🟥🟥🟥🟥. Drag 2 blocks 🟥🟥 to the drop box. Count how many blocks remain, then type your answer.'
        },
        {
            'question': 'Main Box has 6 stars ⭐⭐⭐⭐⭐⭐. Remove 3 stars ⭐⭐⭐. How many stars are left?',
            'answer': 3,
            'task': 'Main Box has 6 stars ⭐⭐⭐⭐⭐⭐. Drag 3 stars ⭐⭐⭐ to the drop box. Count how many stars remain, then type your answer.'
        },
        {
            'question': 'Main Box has 7 apples 🍎🍎🍎🍎🍎🍎🍎. Remove 4 apples 🍎🍎🍎🍎. How many apples are left?',
            'answer': 3,
            'task': 'Main Box has 7 apples 🍎🍎🍎🍎🍎🍎🍎. Drag 4 apples 🍎🍎🍎🍎 to the drop box. Count how many apples remain, then type your answer.'
        },
        {
            'question': 'Main Box has 4 hearts 💖💖💖💖. Remove 1 heart 💖. How many hearts are left?',
            'answer': 3,
            'task': 'Main Box has 4 hearts 💖💖💖💖. Drag 1 heart 💖 to the drop box. Count how many hearts remain, then type your answer.'
        },
        {
            'question': 'Main Box has 8 balloons 🎈🎈🎈🎈🎈🎈🎈🎈. Remove 5 balloons 🎈🎈🎈🎈🎈. How many balloons are left?',
            'answer': 3,
            'task': 'Main Box has 8 balloons 🎈🎈🎈🎈🎈🎈🎈🎈. Drag 5 balloons 🎈🎈🎈🎈🎈 to the drop box. Count how many balloons remain, then type your answer.'
        }
    ]
}

@app.route('/')
def index():
    """Homepage - automatically start subtraction learning (then practice with emotion tracking)"""
    from flask import redirect
    
    print("[DEBUG] Main route '/' accessed")
    
    # Get learner_id from URL or use first available one from CSV
    learner_id = request.args.get('learner_id', type=int)
    
    if learner_id is None:
        preferred_modes = load_preferred_modes()
        if preferred_modes:
            first_learner_id = list(preferred_modes.keys())[0]
            print(f"[DEBUG] Using first learner ID: {first_learner_id}")
            return redirect(f'/subtraction_learning?learner_id={first_learner_id}')
        else:
            return "Error: No learner data found in preferred_modes.csv", 404
    
    print(f"[DEBUG] Using provided learner ID: {learner_id}")
    return redirect(f'/subtraction_learning?learner_id={learner_id}')

@app.route('/api/preferred_mode/<int:learner_id>')
def get_preferred_mode(learner_id):
    """API endpoint to get preferred mode for a specific learner"""
    preferred_modes = load_preferred_modes()
    
    if learner_id not in preferred_modes:
        return jsonify({'error': f'Learner ID {learner_id} not found'}), 404
    
    preferred_mode = preferred_modes[learner_id]
    
    mode_info = {
        'kinesthetic': {
            'title': 'Kinesthetic Learning',
            'description': 'You learn best through movement, touch, and hands-on activities. You\'ll drag objects, remove items, and interact physically with subtraction concepts.'
        },
        'visual': {
            'title': 'Visual Learning', 
            'description': 'You learn best through pictures, diagrams, and visual representations. You\'ll see objects being taken away and learn through observation.'
        },
        'auditory': {
            'title': 'Auditory Learning',
            'description': 'You learn best through listening and sound. You\'ll hear numbers, count sounds, and learn through audio instructions about subtraction.'
        }
    }
    
    return jsonify({
        'mode': preferred_mode,
        'title': mode_info[preferred_mode]['title'],
        'description': mode_info[preferred_mode]['description']
    })

@app.route('/subtraction_learning')
def subtraction_learning():
    """Subtraction learning main page - shows examples before practice with emotion tracking"""
    learner_id = request.args.get('learner_id', 1, type=int)
    
    # Mark interaction for inactivity tracking (no monitoring yet)
    _mark_interaction(learner_id)
    
    # Load preferred mode for this learner
    preferred_modes = load_preferred_modes()
    
    # Check if learner_id exists in preferred modes
    if learner_id not in preferred_modes:
        return f"Error: Learner ID {learner_id} not found in preferred modes. Please check your CSV file.", 404
    
    preferred_mode = preferred_modes[learner_id]
    
    # Get examples and practice questions for this mode
    examples = SUBTRACTION_EXAMPLES.get(preferred_mode, [])
    practice_questions = SUBTRACTION_PRACTICE.get(preferred_mode, [])
    
    return render_template('subtraction_learning.html', 
                         mode=preferred_mode,
                         examples=examples,
                         practice_questions=practice_questions,
                         learner_id=learner_id)

@app.route('/subtraction_practice')
def subtraction_practice():
    """Subtraction practice page with emotion tracking session (after learning)"""
    learner_id = request.args.get('learner_id', 1, type=int)
    
    # Mark interaction and start inactivity monitoring
    _mark_interaction(learner_id)
    _start_inactivity_monitor(learner_id)
    
    # Get preferred mode from CSV
    preferred_modes = load_preferred_modes()
    mode = preferred_modes.get(learner_id, 'kinesthetic')
    
    # Create practice session (following autism webapp pattern)
    session_id = f"subtraction_practice_{learner_id}_{int(time.time())}"
    practice_questions = SUBTRACTION_PRACTICE.get(mode, [])
    
    # Initialize session data
    current_sessions[session_id] = {
        'learner_id': learner_id,
        'current_mode': mode,
        'question_index': 0,
        'session_data': [],
        'test_number': 1,
        'created_at': datetime.now(),
        'practice_questions': practice_questions,
        'current_question': None,
        'question_start_time': None
    }
    
    return render_template('subtraction_practice_emotion.html',
                         mode=mode,
                         practice_questions=practice_questions,
                         learner_id=learner_id,
                         session_id=session_id)

@app.route('/get_practice_question/<session_id>')
def get_practice_question(session_id):
    """Get current practice question for the session - Following AutismApp.py logic"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_info = current_sessions[session_id]
    
    # Mark interaction for inactivity tracking
    _mark_interaction(session_info['learner_id'])
    
    mode = session_info['current_mode']
    question_index = session_info['question_index']
    
    questions = session_info['practice_questions']
    if question_index >= len(questions):
        return jsonify({'completed': True})
    
    question = questions[question_index]
    session_info['current_question'] = question
    
    # Following AutismApp.py logic: Start camera first, don't set start time yet
    emotion_tracker.start_emotion_tracking()
    
    return jsonify({
        'question': question,
        'mode': mode,
        'question_index': question_index,
        'total_questions': len(questions),
        'camera_initializing': True,
        'completed': False
    })

@app.route('/submit_practice_answer/<session_id>', methods=['POST'])
def submit_practice_answer(session_id):
    """Submit practice answer and get emotion analysis (preserves original logic)"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_info = current_sessions[session_id]
    current_question = session_info['current_question']
    
    if not current_question:
        return jsonify({'error': 'No current question'}), 400
    
    # Mark interaction for inactivity tracking
    _mark_interaction(session_info['learner_id'])
    
    data = request.get_json()
    answer = data.get('answer', '').strip()
    
    # Check answer (unchanged logic)
    correct = (str(answer) == str(current_question["answer"]))
    skipped = (answer.upper() == "SKIP" or answer == "")
    
    # Stop emotion tracking and get result
    current_emotion = emotion_tracker.stop_emotion_tracking()
    
    # Print detected emotion to terminal (for monitoring)
    print(f"Subtraction Practice - Detected Emotion: {current_emotion}")
    
    # Calculate response time
    question_start_time = session_info.get('question_start_time', time.time())
    response_time = time.time() - question_start_time
    
    # Store session data (unchanged logic)
    session_info['session_data'].append({
        "learner_id": session_info['learner_id'],
        "test_number": session_info['test_number'],
        "mode": session_info['current_mode'],
        "question": current_question["question"],
        "answer": current_question["answer"],
        "response": answer,
        "correct": correct,
        "skipped": skipped,
        "emotion": current_emotion,
        "response_time": response_time,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Move to next question
    session_info['question_index'] += 1
    
    # Check if test is complete
    if session_info['question_index'] >= len(session_info['practice_questions']):
        # Session completed; CSV logging removed per request
        
        return jsonify({
            'correct': correct,
            'emotion': current_emotion,
            'completed': True,
            'total_score': sum(1 for data in session_info['session_data'] if data['correct'])
        })
    
    return jsonify({
        'correct': correct,
        'emotion': current_emotion,
        'completed': False
    })

@app.route('/check_practice_camera_ready')
def check_practice_camera_ready():
    """Check if camera is ready for emotion tracking in practice"""
    ready = emotion_tracker.is_camera_ready()
    return jsonify({'ready': ready})

@app.route('/practice_camera_ready/<session_id>', methods=['POST'])
def practice_camera_ready_start_question(session_id):
    """Called when camera is ready - start question timing (following AutismApp.py logic)"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_info = current_sessions[session_id]
    # Following original logic: Set question start time only when camera is ready
    session_info['question_start_time'] = time.time()
    
    return jsonify({'success': True})

def save_subtraction_practice_session(session_info):
    """No-op: CSV logging removed."""
    return

def save_subtraction_frustration_report(session_info):
    """No-op: CSV logging removed."""
    return

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files for auditory learning mode"""
    try:
        audio_dir = os.path.join(os.getcwd(), 'audio')
        return send_file(os.path.join(audio_dir, filename))
    except Exception as e:
        return f"Audio file not found: {e}", 404

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    """Convert text to speech for auditory questions"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Return the text for client-side text-to-speech
        return jsonify({
            'text': text,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': f'Text-to-speech error: {e}'}), 500


def _find_free_port(start_port: int = 5003, max_tries: int = 20) -> int:
    port = start_port
    for _ in range(max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                port += 1
    return start_port

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Subtraction Learning App with Emotion Tracking')
    parser.add_argument('--learner-id', type=int, help='Learner ID to use')
    parser.add_argument('--auto-open', action='store_true', help='Auto-open browser')
    args = parser.parse_args()
    
    # Check for preferred mode from environment variable
    preferred_mode = os.environ.get('PREFERRED_MODE', 'visual').lower()
    
    print("Subtraction Learning App with Emotion Tracking")
    print("==================================================")
    print(f"Starting the application in {preferred_mode} mode...")
    print("Features included:")
    print("   • Real-time emotion tracking during practice")
    print("   • Frustration analysis (no CSV logging)")
    print("   • Visual learning mode")
    print("   • Auditory learning mode") 
    print("   • Kinesthetic learning mode")
    print("   • Practice session (no CSV logging)")
    print("   • Camera initialization before each question")
    print("   • Inactivity monitoring with mode cycling")
    print()
    
    # Change to the current directory to ensure proper imports
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Use fixed port 5003 for subtraction app
        selected_port = 5003
        
        # Auto-open browser if requested
        if args.auto_open:
            def open_browser():
                time.sleep(3)  # Wait for server to start
                learner_id = args.learner_id or 1
                url = f"http://localhost:{selected_port}?learner_id={learner_id}"
                subprocess.run(["open", url], check=False)
                print(f"[Auto-open] Browser opened to {url}")
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
        
        print(f"Subtraction practice with emotion tracking loaded in {preferred_mode} mode!")
        print(f"Starting Flask server on http://localhost:{selected_port}")
        print("Ready for practice!")
        print()
        print("Note: Camera initializes before each question for emotion tracking.")
        print("All emotion data stays on your computer - nothing is sent anywhere!")
        print("Inactivity monitoring: Mode cycles after threshold exceeded.")
        print()
        print("DEBUG: Monitoring will start when you first access the app at http://localhost:5003")
        print("DEBUG: Look for '[Monitor] Started monitoring thread for learner 1' messages")
        print()
        
        # Run the Flask app (disable debug and reloader to avoid FD issues in background)
        app.run(debug=False, host='0.0.0.0', port=selected_port, use_reloader=False)
        
    except Exception as e:
        print(f"Error starting the application: {e}")
        print()
        print("Troubleshooting tips:")
        print("   1. Make sure you have installed the requirements:")
        print("      pip install -r requirements.txt")
        print("   2. Check that your camera is not being used by another app")
        print("   3. Make sure Python has camera permissions")
        print("   4. Check that preferred_modes.csv exists")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
