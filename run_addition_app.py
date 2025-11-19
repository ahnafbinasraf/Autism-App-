#!/usr/bin/env python3
"""
Addition Learning App with Emotion Tracking
Following AutismApp.py logic for practice questions with camera initialization and emotion tracking
"""

import os
import sys
import webbrowser
import threading
import time
import csv
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file, Response
import json
import subprocess
import webbrowser
import urllib.request

# Import emotion tracking modules with fallback (same as autism webapp)
try:
    import emotion_tracker_webapp as emotion_tracker
    EMOTION_TRACKER_AVAILABLE = True
    print("Advanced emotion tracking loaded for addition practice")
except Exception as e:
    try:
        import emotion_tracker_simple as emotion_tracker
        EMOTION_TRACKER_AVAILABLE = True
        print("Simple emotion tracking loaded for addition practice")
    except Exception as e2:
        print(f"Using mock emotion tracking for addition practice: {e2}")
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
    print("Frustration analysis loaded for addition practice")
except Exception as e:
    print(f"Frustration analysis not available for addition practice: {e}")
    FRUSTRATION_AVAILABLE = False
    frustration_webapp = None  # Set to None if import fails

# Flask app setup
app = Flask(__name__)
app.secret_key = 'addition_practice_emotion_tracking_key'

# Session management for practice tracking
current_sessions = {}

# Inactivity timer
_last_interaction_ts = {}
_monitor_threads = {}
_launched_subtraction = set()

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

def _mark_interaction(learner_id: int):
    _last_interaction_ts[learner_id] = time.time()

def _check_inactivity_and_launch(learner_id: int):
    threshold = _load_inactivity_threshold(learner_id)
    last_ts = _last_interaction_ts.get(learner_id, time.time())
    elapsed = time.time() - last_ts
    remaining = threshold - elapsed
    if remaining <= 0:
        # Only cycle mode once per learner when threshold is exceeded
        if learner_id not in _launched_subtraction:
            print(f"[Inactivity] Threshold exceeded for learner {learner_id}. Cycling learning mode...")
            
            # Cycle through modes: visual -> kinesthetic -> auditory -> visual
            mode_cycle = {'visual': 'kinesthetic', 'kinesthetic': 'auditory', 'auditory': 'visual'}
            
            try:
                # Read current preferred modes
                preferred_modes = load_preferred_modes()
                current_mode = preferred_modes.get(learner_id, 'visual')
                new_mode = mode_cycle.get(current_mode, 'visual')
                
                # Update preferred_modes.csv
                preferred_modes[learner_id] = new_mode
                
                # Write back to CSV
                with open('preferred_modes.csv', 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['learner_id', 'preferred_mode'])
                    for lid, mode in preferred_modes.items():
                        writer.writerow([lid, mode])
                
                print(f"[Inactivity] Changed learner {learner_id} mode from {current_mode} to {new_mode}")
                
                # Relaunch via a detached helper so current process can be killed safely
                print(f"[Inactivity] Scheduling safe restart of addition app...")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                helper_code = (
                    "import time,subprocess,sys,os,signal,platform,webbrowser;"
                    "def signal_handler(sig, frame): sys.exit(0);"
                    "signal.signal(signal.SIGINT, signal_handler);"
                    "signal.signal(signal.SIGTERM, signal_handler);"
                    "time.sleep(1);"
                    "plat=platform.system().lower();"
                    "if 'windows' in plat:"
                    "\n    ps=\"$p=(Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue).OwningProcess; if($p){taskkill /F /PID $p}\";"
                    "\n    subprocess.run(['powershell','-NoProfile','-Command', ps], check=False);"
                    "else:"
                    "\n    res=subprocess.run(['lsof','-ti:5001'],capture_output=True,text=True);"
                    "\n    pids=[p for p in res.stdout.strip().split('\\n') if p.strip()];"
                    "\n    [subprocess.run(['kill','-9',pid],check=False) for pid in pids];"
                    "time.sleep(2);"
                    f"proc=subprocess.Popen([sys.executable,'run_addition_app.py'], cwd=r'{base_dir}');"
                    "time.sleep(3);"
                    f"webbrowser.open('http://localhost:5001?learner_id={learner_id}');"
                    "proc.wait()"
                )
                try:
                    subprocess.Popen([sys.executable, "-c", helper_code])
                    print("[Inactivity] Helper spawned to restart and open browser.")
                except Exception as e:
                    print(f"[Inactivity] Failed to spawn helper: {e}")
                
            except Exception as e:
                print(f"[Inactivity] Error cycling mode: {e}")
            
            _launched_subtraction.add(learner_id)
    else:
        # Occasional heartbeat for visibility
        if int(remaining) % 30 == 0:
            print(f"[Inactivity] Learner {learner_id}: {int(remaining)}s until launch (threshold {int(threshold)}s)")

def _start_inactivity_monitor(learner_id: int):
    if learner_id in _monitor_threads:
        return
    def _loop():
        while True:
            try:
                _check_inactivity_and_launch(learner_id)
            except Exception:
                pass
            # Stop if subtraction already launched
            if learner_id in _launched_subtraction:
                break
            time.sleep(5)
    t = threading.Thread(target=_loop, daemon=True)
    _monitor_threads[learner_id] = t
    t.start()

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

# Addition learning examples (before practice)
ADDITION_EXAMPLES = {
    'visual': [
        {
            'title': 'Example 1: Visual Addition',
            'description': 'Show picture: 🍎🍎 (2 apples). Add another 🍎.',
            'teacher_text': '2 apples plus 1 apple makes 3 apples.',
            'equation': '2 + 1 = 3',
            'visual_elements': ['🍎🍎', '🍎', '🍎🍎🍎']
        },
        {
            'title': 'Example 2: Visual Addition',
            'description': 'Show picture: 🐶🐶🐶 (3 dogs). Add 2 more 🐶🐶.',
            'teacher_text': '3 dogs plus 2 dogs makes 5 dogs.',
            'equation': '3 + 2 = 5',
            'visual_elements': ['🐶🐶🐶', '🐶🐶', '🐶🐶🐶🐶🐶']
        },
        {
            'title': 'Example 3: Visual Addition',
            'description': 'Show picture: ⭐⭐⭐⭐⭐ (5 stars). Add 3 more ⭐⭐⭐.',
            'teacher_text': '5 stars plus 3 stars makes 8 stars.',
            'equation': '5 + 3 = 8',
            'visual_elements': ['⭐⭐⭐⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐⭐⭐⭐⭐']
        },
        {
            'title': 'Example 4: Visual Addition',
            'description': 'Show picture: 🎈🎈 (2 balloons). Add 4 more 🎈🎈🎈🎈.',
            'teacher_text': '2 balloons plus 4 balloons makes 6 balloons.',
            'equation': '2 + 4 = 6',
            'visual_elements': ['🎈🎈', '🎈🎈🎈🎈', '🎈🎈🎈🎈🎈🎈']
        },
        {
            'title': 'Example 5: Visual Addition',
            'description': 'Show picture: 🐟🐟🐟 (3 fish). Add 5 more 🐟🐟🐟🐟🐟.',
            'teacher_text': '3 fish plus 5 fish makes 8 fish.',
            'equation': '3 + 5 = 8',
            'visual_elements': ['🐟🐟🐟', '🐟🐟🐟🐟🐟', '🐟🐟🐟🐟🐟🐟🐟🐟']
        }
    ],
    'auditory': [
        {
            'title': 'Example 1: Auditory Addition',
            'description': 'Listen carefully: You have 2 candies. Then I give you 1 more candy.',
            'teacher_text': '2 plus 1 equals 3.',
            'equation': '2 + 1 = 3',
            'audio_text': 'You have 2 candies. Then I give you 1 more candy. Altogether, you have 3.'
        },
        {
            'title': 'Example 2: Auditory Addition',
            'description': 'Listen carefully: You have 3 candies. Then I give you 2 more candies.',
            'teacher_text': '3 plus 2 equals 5.',
            'equation': '3 + 2 = 5',
            'audio_text': 'You have 3 candies. Then I give you 2 more candies. Altogether, you have 5.'
        },
        {
            'title': 'Example 3: Auditory Addition',
            'description': 'Listen carefully: You have 4 candies. Then I give you 3 more candies.',
            'teacher_text': '4 plus 3 equals 7.',
            'equation': '4 + 3 = 7',
            'audio_text': 'You have 4 candies. Then I give you 3 more candies. Altogether, you have 7.'
        },
        {
            'title': 'Example 4: Auditory Addition',
            'description': 'Listen carefully: You have 5 candies. Then I give you 2 more candies.',
            'teacher_text': '5 plus 2 equals 7.',
            'equation': '5 + 2 = 7',
            'audio_text': 'You have 5 candies. Then I give you 2 more candies. Altogether, you have 7.'
        },
        {
            'title': 'Example 5: Auditory Addition',
            'description': 'Listen carefully: You have 6 candies. Then I give you 1 more candy.',
            'teacher_text': '6 plus 1 equals 7.',
            'equation': '6 + 1 = 7',
            'audio_text': 'You have 6 candies. Then I give you 1 more candy. Altogether, you have 7.'
        }
    ],
    'kinesthetic': [
        {
            'title': 'Example 1: Kinesthetic Addition',
            'description': 'Drag 2 stars ⭐⭐ into the box. Now drag 1 more ⭐.',
            'teacher_text': '2 plus 1 equals 3.',
            'equation': '2 + 1 = 3',
            'task': 'Drag 2 stars ⭐⭐ into the box. Then drag 1 more ⭐. Count them all.',
            'counts': [2, 1, 3],
            'elements': ['⭐⭐', '⭐', '⭐⭐⭐']
        },
        {
            'title': 'Example 2: Kinesthetic Addition',
            'description': 'Drag 3 apples 🍎🍎🍎 into the basket. Now drag 2 more 🍎🍎.',
            'teacher_text': '3 plus 2 equals 5.',
            'equation': '3 + 2 = 5',
            'task': 'Move 3 apples 🍎🍎🍎 into the basket. Then add 2 more 🍎🍎. Count them.',
            'counts': [3, 2, 5],
            'elements': ['🍎🍎🍎', '🍎🍎', '🍎🍎🍎🍎🍎']
        },
        {
            'title': 'Example 3: Kinesthetic Addition',
            'description': 'Tap the screen 4 times. Now tap 3 more times.',
            'teacher_text': '4 plus 3 equals 7.',
            'equation': '4 + 3 = 7',
            'task': 'Tap the screen 4 times. Now tap 3 more times. How many taps total?',
            'counts': [4, 3, 7],
            'elements': ['👆👆👆👆', '👆👆👆', '👆👆👆👆👆👆👆']
        },
        {
            'title': 'Example 4: Kinesthetic Addition',
            'description': 'Put 5 blocks 🟥🟥🟥🟥🟥 together. Then add 3 more 🟥🟥🟥.',
            'teacher_text': '5 plus 3 equals 8.',
            'equation': '5 + 3 = 8',
            'task': 'Put 5 blocks 🟥🟥🟥🟥🟥 together. Then add 3 more 🟥🟥🟥. How many now?',
            'counts': [5, 3, 8],
            'elements': ['🟥🟥🟥🟥🟥', '🟥🟥🟥', '🟥🟥🟥🟥🟥🟥🟥🟥']
        },
        {
            'title': 'Example 5: Kinesthetic Addition',
            'description': 'Drag 1 balloon 🎈, then drag 6 more 🎈🎈🎈🎈🎈🎈.',
            'teacher_text': '1 plus 6 equals 7.',
            'equation': '1 + 6 = 7',
            'task': 'Drag 1 balloon 🎈, then drag 6 more 🎈🎈🎈🎈🎈🎈. How many balloons total?',
            'counts': [1, 6, 7],
            'elements': ['🎈', '🎈🎈🎈🎈🎈🎈', '🎈🎈🎈🎈🎈🎈🎈']
        }
    ]
}

# Addition practice questions (with emotion tracking)
ADDITION_PRACTICE = {
    'visual': [
        {
            'question': 'You see 1 dog 🐶. Then I bring 2 more 🐶🐶. How many dogs in total?',
            'answer': 3,
            'visual_elements': ['🐶', '🐶🐶', '🐶🐶🐶']
        },
        {
            'question': 'Look at these 3 apples 🍎🍎🍎. Then I add 1 more 🍎. How many now?',
            'answer': 4,
            'visual_elements': ['🍎🍎🍎', '🍎', '🍎🍎🍎🍎']
        },
        {
            'question': 'You see 5 stars ⭐⭐⭐⭐⭐. Add 2 more ⭐⭐. How many stars?',
            'answer': 7,
            'visual_elements': ['⭐⭐⭐⭐⭐', '⭐⭐', '⭐⭐⭐⭐⭐⭐⭐']
        },
        {
            'question': 'There are 2 balloons 🎈🎈. Then 4 more 🎈🎈🎈🎈. How many balloons in total?',
            'answer': 6,
            'visual_elements': ['🎈🎈', '🎈🎈🎈🎈', '🎈🎈🎈🎈🎈🎈']
        },
        {
            'question': 'I have 4 cars 🚗🚗🚗🚗. My friend gives me 3 more 🚗🚗🚗. How many cars do I have?',
            'answer': 7,
            'visual_elements': ['🚗🚗🚗🚗', '🚗🚗🚗', '🚗🚗🚗🚗🚗🚗🚗']
        }
    ],
    'auditory': [
        {
            'question': 'You had 2 toys. Your friend gave you 3 more toys. How many toys do you have now?',
            'answer': 5,
            'audio_text': 'You had 2 toys. Your friend gave you 3 more toys. How many toys do you have now?'
        },
        {
            'question': 'There were 4 birds in a tree. 1 more bird came. How many birds are in the tree?',
            'answer': 5,
            'audio_text': 'There were 4 birds in a tree. 1 more bird came. How many birds are in the tree?'
        },
        {
            'question': 'You have 3 cookies. Mom gives you 4 more cookies. How many cookies in total?',
            'answer': 7,
            'audio_text': 'You have 3 cookies. Mom gives you 4 more cookies. How many cookies do you have in total?'
        },
        {
            'question': 'I saw 5 cats. Then I saw 2 more cats. How many cats did I see altogether?',
            'answer': 7,
            'audio_text': 'I saw 5 cats. Then I saw 2 more cats. How many cats did I see altogether?'
        },
        {
            'question': 'You collected 6 shells. You found 1 more shell. How many shells do you have?',
            'answer': 7,
            'audio_text': 'You collected 6 shells. You found 1 more shell. How many shells do you have?'
        }
    ],
    'kinesthetic': [
        {
            'question': 'Drag 2 stars ⭐⭐ into the box. Then drag 1 more ⭐. How many stars total?',
            'answer': 3,
            'task': 'Drag 2 stars ⭐⭐ into the box. Then drag 1 more ⭐. Count them all.'
        },
        {
            'question': 'Move 3 apples 🍎🍎🍎 into the basket. Then add 2 more 🍎🍎. Count them.',
            'answer': 5,
            'task': 'Move 3 apples 🍎🍎🍎 into the basket. Then add 2 more 🍎🍎. Count them.'
        },
        {
            'question': 'Tap the screen 4 times. Now tap 2 more times. How many taps total?',
            'answer': 6,
            'task': 'Tap the screen 4 times. Now tap 2 more times. How many taps total?'
        },
        {
            'question': 'Put 5 blocks 🟥🟥🟥🟥🟥 together. Then add 3 more 🟥🟥🟥. How many now?',
            'answer': 8,
            'task': 'Put 5 blocks 🟥🟥🟥🟥🟥 together. Then add 3 more 🟥🟥🟥. How many now?'
        },
        {
            'question': 'Drag 1 balloon 🎈, then drag 6 more 🎈🎈🎈🎈🎈🎈. How many balloons total?',
            'answer': 7,
            'task': 'Drag 1 balloon 🎈, then drag 6 more 🎈🎈🎈🎈🎈🎈. How many balloons total?'
        }
    ]
}

@app.route('/')
def index():
    """Homepage - automatically start addition learning (then practice with emotion tracking)"""
    from flask import redirect
    
    # Get learner_id from URL or use first available one from CSV
    learner_id = request.args.get('learner_id', type=int)
    
    if learner_id is None:
        preferred_modes = load_preferred_modes()
        if preferred_modes:
            first_learner_id = list(preferred_modes.keys())[0]
            return redirect(f'/addition_learning?learner_id={first_learner_id}')
        else:
            return "Error: No learner data found in preferred_modes.csv", 404
    
    return redirect(f'/addition_learning?learner_id={learner_id}')

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
            'description': 'You learn best through movement, touch, and hands-on activities. You\'ll drag objects, tap the screen, and interact physically with math concepts.'
        },
        'visual': {
            'title': 'Visual Learning', 
            'description': 'You learn best through pictures, diagrams, and visual representations. You\'ll see objects, count them visually, and learn through observation.'
        },
        'auditory': {
            'title': 'Auditory Learning',
            'description': 'You learn best through listening and sound. You\'ll hear numbers, count sounds, and learn through audio instructions.'
        }
    }
    
    return jsonify({
        'mode': preferred_mode,
        'title': mode_info[preferred_mode]['title'],
        'description': mode_info[preferred_mode]['description']
    })

@app.route('/addition_learning')
def addition_learning():
    """Addition learning main page - shows examples before practice with emotion tracking"""
    learner_id = request.args.get('learner_id', 1, type=int)
    
    # Load preferred mode for this learner
    preferred_modes = load_preferred_modes()
    
    # Check if learner_id exists in preferred modes
    if learner_id not in preferred_modes:
        return f"Error: Learner ID {learner_id} not found in preferred modes. Please check your CSV file.", 404
    
    preferred_mode = preferred_modes[learner_id]
    
    # Get examples and practice questions for this mode
    examples = ADDITION_EXAMPLES.get(preferred_mode, [])
    practice_questions = ADDITION_PRACTICE.get(preferred_mode, [])
    
    return render_template('addition_learning.html', 
                         mode=preferred_mode,
                         examples=examples,
                         practice_questions=practice_questions,
                         learner_id=learner_id)

@app.route('/addition_practice')
def addition_practice():
    """Addition practice page with emotion tracking session (after learning)"""
    learner_id = request.args.get('learner_id', 1, type=int)
    
    # Get preferred mode from CSV
    preferred_modes = load_preferred_modes()
    mode = preferred_modes.get(learner_id, 'kinesthetic')
    
    # Create practice session (following autism webapp pattern)
    session_id = f"addition_practice_{learner_id}_{int(time.time())}"
    practice_questions = ADDITION_PRACTICE.get(mode, [])
    
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
    
    # Initialize last interaction timestamp and start inactivity monitor
    _mark_interaction(learner_id)
    _start_inactivity_monitor(learner_id)

    return render_template('addition_practice_emotion.html',
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
    mode = session_info['current_mode']
    question_index = session_info['question_index']
    
    questions = session_info['practice_questions']
    if question_index >= len(questions):
        return jsonify({'completed': True})
    
    question = questions[question_index]
    _mark_interaction(session_info['learner_id'])
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
    
    data = request.get_json()
    answer = data.get('answer', '').strip()
    
    # Check answer (unchanged logic)
    correct = (str(answer) == str(current_question["answer"]))
    skipped = (answer.upper() == "SKIP" or answer == "")
    
    # Stop emotion tracking and get result
    current_emotion = emotion_tracker.stop_emotion_tracking()
    
    # Print detected emotion to terminal (for monitoring)
    print(f"Addition Practice - Detected Emotion: {current_emotion}")
    
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
    
    # Mark interaction
    _mark_interaction(session_info['learner_id'])

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
    
    # Periodically check inactivity after responses
    try:
        _check_inactivity_and_launch(session_info['learner_id'])
    except Exception:
        pass

    return jsonify({
        'correct': correct,
        'emotion': current_emotion,
        'completed': False
    })

@app.route('/check_practice_camera_ready')
def check_practice_camera_ready():
    """Check if camera is ready for emotion tracking in practice"""
    ready = emotion_tracker.is_camera_ready()
    # Background inactivity check (non-blocking)
    try:
        # Attempt to read learner_id from referring session if available is not straightforward here
        # so we skip explicit learner_id check in this ping
        pass
    except Exception:
        pass
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

def save_addition_practice_session(session_info):
    """No-op: CSV logging removed."""
    return

def save_addition_frustration_report(session_info):
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

# Browser opening disabled to prevent duplicate windows
# def open_browser():
#     """Open the browser after a short delay to ensure the server has started"""
#     time.sleep(2.0)  # Wait for server to start
#     webbrowser.open('http://localhost:5001')

def main():
    # Check for command line arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--learner-id', type=int, help='Learner ID')
    parser.add_argument('--auto-open', action='store_true', help='Automatically open browser')
    args = parser.parse_args()
    
    # Check for preferred mode from environment variable
    preferred_mode = os.environ.get('PREFERRED_MODE', 'visual').lower()
    
    print("Addition Learning App with Emotion Tracking")
    print("================================================")
    print(f"Starting the application in {preferred_mode} mode...")
    print("Features included:")
    print("   • Real-time emotion tracking during practice")
    print("   • Frustration analysis (no CSV logging)")
    print("   • Visual learning mode")
    print("   • Auditory learning mode") 
    print("   • Kinesthetic learning mode")
    print("   • Practice session (no CSV logging)")
    print("   • Camera initialization before each question")
    print()
    
    # Change to the current directory to ensure proper imports
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print(f"Addition practice with emotion tracking loaded in {preferred_mode} mode!")
        print("Starting Flask server on http://localhost:5001")
        print("Ready for practice! Open your browser and go to: http://localhost:5001")
        print()
        print("Note: Camera initializes before each question for emotion tracking.")
        print("Privacy: All emotion data stays on your computer - nothing is sent anywhere!")
        print()
        
        # Auto-open browser if requested
        if args.auto_open:
            def open_browser_when_ready():
                learner_id = args.learner_id or 1
                base_url = f"http://localhost:5001"
                url = f"{base_url}?learner_id={learner_id}"
                # Poll readiness up to 60 seconds
                deadline = time.time() + 60
                import urllib.request
                while time.time() < deadline:
                    try:
                        with urllib.request.urlopen(base_url, timeout=1.5) as resp:
                            if resp.status < 500:
                                break
                    except Exception:
                        time.sleep(0.8)
                        continue
                try:
                    ok = webbrowser.open(url)
                    if not ok and sys.platform == 'darwin':
                        subprocess.Popen(['open', url])
                    print(f"Browser open attempted to {url}")
                except Exception as e:
                    print(f"Browser open failed: {e}")
            
            threading.Thread(target=open_browser_when_ready, daemon=True).start()
        
        # Run the Flask app (debug disabled to prevent file descriptor issues)
        app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)
        
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
