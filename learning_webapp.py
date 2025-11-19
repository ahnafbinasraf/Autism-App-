#!/usr/bin/env python3
"""
Autism Learning WebApp
Converts AutismApp.py into a kid-friendly webapp for children with ASD Level 1
Maintains all original logic while providing a web-based interface
"""

from flask import Flask, render_template, request, jsonify, session, Response, send_file
import os
import sys
import csv
import time
import random
import pandas as pd
import cv2
import threading
import webbrowser
from datetime import datetime
import json

# Import emotion tracking modules with fallback
try:
    import emotion_tracker_webapp as emotion_tracker
    EMOTION_TRACKER_AVAILABLE = True
    print("Advanced emotion tracking loaded")
except Exception as e:
    try:
        import emotion_tracker_simple as emotion_tracker
        EMOTION_TRACKER_AVAILABLE = True
        print("Simple emotion tracking loaded")
    except Exception as e2:
        print(f"Warning: Using mock emotion tracking: {e2}")
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
except Exception as e:
    print(f"Warning: Frustration analysis not available: {e}")
    frustration_webapp = None

# Flask app setup
app = Flask(__name__)
app.secret_key = 'autism_learning_webapp_secret_key_2024'

# --- Original logic constants (unchanged) ---
PREFERRED_MODE_FILE = "preferred_modes.csv"
MODES = ["visual", "auditory", "kinesthetic"]

# --- Load questions with UTF-8 encoding and visual elements support (unchanged logic) ---
QUESTION_BANK = {}
try:
    with open('questions.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mode = row['mode']
            if mode not in QUESTION_BANK:
                QUESTION_BANK[mode] = []
            
            question_data = {
                "question": row['question'], 
                "answer": row['answer']
            }
            
            # Add elements for visual counting questions
            if 'elements' in row and row['elements']:
                question_data["elements"] = row['elements'].split(',')
            
            QUESTION_BANK[mode].append(question_data)
except Exception as e:
    print(f"Error loading questions: {e}")
    # Create default questions if file not found
    QUESTION_BANK = {
        "visual": [{"question": "How many stars do you see? ⭐⭐⭐", "answer": "3"}],
        "auditory": [{"question": "audio_question_1.wav", "answer": "5"}],
        "kinesthetic": [{"question": "kinesthetic_task_1.html", "answer": "done"}]
    }

# --- Global state (preserved from original) ---
current_sessions = {}  # Store session data per learner

# --- Original helper functions (unchanged logic) ---
def get_frustration(learner_id):
    """Get frustration score for learner (unchanged logic)"""
    if not os.path.exists(f"frustration_report{learner_id}.csv"):
        return None
    with open(f"frustration_report{learner_id}.csv", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["learner_id"] == learner_id:
                return float(row["frustration_score"])
    return None

def get_preferred_mode(learner_id):
    """Get preferred learning mode for learner (unchanged logic)"""
    if not os.path.exists(PREFERRED_MODE_FILE):
        return None
    with open(PREFERRED_MODE_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["learner_id"] == learner_id:
                return row["preferred_mode"]
    return None

def get_last_used_mode(learner_id):
    """Get the mode used in the most recent session for this learner (unchanged logic)"""
    log_file = f"learner_log{learner_id}.csv"
    if not os.path.exists(log_file):
        return None
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            last_mode = None
            max_test_number = 0
            
            for row in reader:
                test_num = int(row.get('test_number', 0))
                if test_num >= max_test_number:
                    max_test_number = test_num
                    last_mode = row.get('mode')
            
            return last_mode
    except Exception as e:
        print(f"Error reading last used mode: {e}")
        return None

def save_preferred_mode(learner_id, mode):
    """Save preferred mode (unchanged logic)"""
    file_exists = os.path.exists(PREFERRED_MODE_FILE)
    with open(PREFERRED_MODE_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["learner_id", "preferred_mode"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"learner_id": learner_id, "preferred_mode": mode})

def get_next_mode(current):
    """Get next mode in sequence (unchanged logic)"""
    idx = MODES.index(current)
    return MODES[(idx + 1) % len(MODES)]

def get_test_count(learner_id):
    """Get the highest test number for a learner ID (unchanged logic)"""
    log_file = f"learner_log{learner_id}.csv"
    if not os.path.exists(log_file):
        return 0
    
    try:
        df = pd.read_csv(log_file, encoding='utf-8')
        if "test_number" in df.columns and len(df) > 0:
            valid_test_numbers = df["test_number"].dropna()
            if len(valid_test_numbers) > 0:
                return int(valid_test_numbers.max())
        return 0
    except Exception as e:
        print(f"Error reading test count for learner {learner_id}: {e}")
        return 0

def save_session(learner_id, session_data):
    """Save session data to CSV (unchanged logic with UTF-8 encoding)"""
    log_file = f"learner_log{learner_id}.csv"
    file_exists = os.path.exists(log_file)
    with open(log_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=session_data[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(session_data)

def _compute_and_store_inactivity_threshold(learner_id: str, test_number: int, output_file: str = "inactivity_thresholds.json") -> float:
    """Compute average response time for the given learner's test and store avg+120s.

    Returns the computed threshold in seconds.
    """
    log_file = f"learner_log{learner_id}.csv"
    try:
        if not os.path.exists(log_file):
            return 120.0

        df = pd.read_csv(log_file, encoding='utf-8')
        # Convert to records and filter by test_number using plain Python
        records = df.to_dict(orient='records')
        filtered = []
        for row in records:
            try:
                tn_raw = row.get('test_number', None)
                tn_val = int(tn_raw) if tn_raw is not None and str(tn_raw).strip() != '' else None
                if tn_val == int(test_number):
                    filtered.append(row)
            except Exception:
                continue
        if not filtered:
            avg = 0.0
        else:
            times_list = []
            for row in filtered:
                try:
                    rt = row.get('response_time_sec', None)
                    if rt is None:
                        continue
                    val = float(rt)
                    if val >= 0:
                        times_list.append(val)
                except Exception:
                    continue
            avg = (sum(times_list) / len(times_list)) if times_list else 0.0

        threshold = max(0.0, avg) + 120.0

        # Persist thresholds per learner
        try:
            existing = {}
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f) or {}
        except Exception:
            existing = {}

        existing[str(learner_id)] = {
            "test_number": int(test_number),
            "avg_response_time_sec": avg,
            "inactivity_threshold_sec": threshold,
            "updated_at": datetime.now().isoformat()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)

        return threshold
    except Exception:
        return 120.0

# --- Flask Routes ---

@app.route('/')
def index():
    """Homepage - learner ID input"""
    return render_template('learning_index.html')

@app.route('/start_learning', methods=['POST'])
def start_learning():
    """Initialize learning session (preserves original logic)"""
    data = request.get_json()
    learner_id = data.get('learner_id', '').strip()
    
    if not learner_id:
        return jsonify({'success': False, 'error': 'Please enter your Learner ID'})
    
    # Force sessions to start in Visual mode and auto-progress through modes
    current_mode = "visual"
    message = "🆕 Welcome! Starting with Visual mode"
    
    test_number = get_test_count(learner_id) + 1
    
    # Initialize session
    session_id = f"{learner_id}_{int(time.time())}"
    current_sessions[session_id] = {
        'learner_id': learner_id,
        'current_mode': current_mode,
        'test_number': test_number,
        'question_index': 0,
        'session_data': [],
        'question_start_time': None,
        'current_question': None,
        'completed_modes': []
    }
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'learner_id': learner_id,
        'mode': current_mode,
        'test_number': test_number,
        'message': message
    })

@app.route('/learning_interface/<session_id>')
def learning_interface(session_id):
    """Main learning interface"""
    if session_id not in current_sessions:
        return "Session not found", 404
    
    session_info = current_sessions[session_id]
    return render_template('learning.html', 
                         session_id=session_id,
                         session_info=session_info)

@app.route('/get_question/<session_id>')
def get_question(session_id):
    """Get current question for the session - Following original AutismApp.py logic"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_info = current_sessions[session_id]
    mode = session_info['current_mode']
    question_index = session_info['question_index']
    
    questions = QUESTION_BANK.get(mode, [])
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
        'camera_initializing': True,  # Signal frontend to show loading and wait
        'completed': False
    })

@app.route('/submit_answer/<session_id>', methods=['POST'])
def submit_answer(session_id):
    """Submit answer and get emotion analysis (preserves original logic)"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.get_json()
    answer = data.get('answer', '').strip()
    
    session_info = current_sessions[session_id]
    current_question = session_info['current_question']
    question_start_time = session_info['question_start_time']
    
    # Calculate response time
    time_taken = time.time() - question_start_time
    
    # Check answer (unchanged logic)
    correct = (answer.lower() == current_question["answer"].lower())
    skipped = (answer.upper() == "SKIP" or answer == "")
    
    # Stop emotion tracking and get result
    current_emotion = emotion_tracker.stop_emotion_tracking()
    
    # Print detected emotion to terminal (for monitoring)
    print(f"Detected Emotion: {current_emotion}")
    
    # Store session data (unchanged logic)
    session_info['session_data'].append({
        "learner_id": session_info['learner_id'],
        "test_number": session_info['test_number'],
        "mode": session_info['current_mode'],
        "question": current_question["question"],
        "response_time_sec": round(time_taken, 2),
        "correct": correct,
        "skipped": skipped,
        "emotion": current_emotion
    })
    
    # Move to next question
    session_info['question_index'] += 1
    
    # Check if quiz is complete for the current mode
    questions = QUESTION_BANK.get(session_info['current_mode'], [])
    if session_info['question_index'] >= len(questions):
        # Save session data for this mode
        save_session(session_info['learner_id'], session_info['session_data'])
        
        # Run frustration analysis for this mode
        try:
            frustration_webapp.compute_frustration_per_test(
                f"learner_log{session_info['learner_id']}.csv",
                f"frustration_report{session_info['learner_id']}.csv"
            ) if frustration_webapp else None
        except Exception as e:
            print(f"Error computing frustration: {e}")

        # Mark this mode as completed
        current_mode_finished = session_info['current_mode']
        if 'completed_modes' not in session_info:
            session_info['completed_modes'] = []
        if current_mode_finished not in session_info['completed_modes']:
            session_info['completed_modes'].append(current_mode_finished)

        # Determine next action: auto-progress Visual -> Auditory -> Kinesthetic
        if len(session_info['completed_modes']) < 3:
            # Switch to next mode
            next_mode = get_next_mode(current_mode_finished)
            # If next_mode already completed (edge case), advance until find remaining
            safety = 0
            while next_mode in session_info['completed_modes'] and safety < 5:
                next_mode = get_next_mode(next_mode)
                safety += 1
            session_info['current_mode'] = next_mode
            session_info['question_index'] = 0
            session_info['current_question'] = None
            session_info['session_data'] = []

            return jsonify({
                'success': True,
                'correct': correct,
                'emotion': current_emotion,
                'completed': False,
                'switched_mode': next_mode,
                'message': f"Great job! Switching to {next_mode.capitalize()} mode."
            })
        else:
            # All modes completed: compute and store inactivity threshold (avg + 120s)
            try:
                _compute_and_store_inactivity_threshold(
                    learner_id=session_info['learner_id'],
                    test_number=session_info['test_number']
                )
            except Exception:
                pass

            return jsonify({
                'success': True,
                'correct': correct,
                'emotion': current_emotion,
                'completed': True,
                'message': "Fantastic! You completed Visual, Auditory, and Kinesthetic modes! 🌟"
            })
    
    return jsonify({
        'success': True,
        'correct': correct,
        'emotion': current_emotion,
        'completed': False
    })

# --- Camera streaming for emotion tracking ---
def generate_camera_frames():
    """Generate camera frames for streaming"""
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()

@app.route('/camera_feed')
def camera_feed():
    """Video streaming route for camera feed"""
    return Response(generate_camera_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_emotion_tracking/<session_id>', methods=['POST'])
def start_emotion_tracking(session_id):
    """Start emotion tracking for the current question"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    success = emotion_tracker.start_emotion_tracking()
    return jsonify({'success': success})

@app.route('/check_camera_ready')
def check_camera_ready():
    """Check if camera is ready for emotion tracking"""
    ready = emotion_tracker.is_camera_ready()
    return jsonify({'ready': ready})

@app.route('/camera_ready/<session_id>', methods=['POST'])
def camera_ready_start_question(session_id):
    """Called when camera is ready - start question timing (following AutismApp.py logic)"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_info = current_sessions[session_id]
    # Following original logic: Set question start time only when camera is ready
    session_info['question_start_time'] = time.time()
    
    return jsonify({'success': True})

# --- Static file serving for audio and kinesthetic tasks ---
@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files for auditory mode"""
    try:
        if os.path.exists(filename):
            return send_file(filename)
        return "Audio file not found", 404
    except Exception as e:
        return f"Error serving audio: {str(e)}", 500

@app.route('/kinesthetic/<filename>')
def serve_kinesthetic(filename):
    """Serve kinesthetic task HTML files"""
    try:
        if os.path.exists(filename):
            resp = send_file(filename)
            # Disable browser/proxy caching so updates show immediately
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp
        return "Task file not found", 404
    except Exception as e:
        return f"Error serving task: {str(e)}", 500

@app.route('/switch_mode/<session_id>/<mode>')
def switch_mode(session_id, mode):
    """Manually switch to a specific learning mode"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    if mode not in ['visual', 'auditory', 'kinesthetic']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    session_info = current_sessions[session_id]
    session_info['current_mode'] = mode
    session_info['question_index'] = 0  # Reset to first question
    
    return jsonify({
        'success': True,
        'mode': mode,
        'message': f'Switched to {mode.capitalize()} mode!'
    })

if __name__ == '__main__':
    print("Autism Learning WebApp")
    print("=========================")
    print("Starting the application...")
    
    # Auto-open browser (only when run directly)
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:5002')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the app
    app.run(debug=False, host='0.0.0.0', port=5002, use_reloader=False)
