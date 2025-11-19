from flask import Flask, render_template, request, jsonify, session, send_file, Response
import os
import pandas as pd
import csv
import time
import random
import threading
from datetime import datetime

# Import emotion tracking modules with fallback (same as autism webapp)
try:
    import emotion_tracker_webapp as emotion_tracker
    EMOTION_TRACKER_AVAILABLE = True
    print("Advanced emotion tracking loaded for addition app")
except Exception as e:
    try:
        import emotion_tracker_simple as emotion_tracker
        EMOTION_TRACKER_AVAILABLE = True
        print("Simple emotion tracking loaded for addition app")
    except Exception as e2:
        print(f"Warning: Using mock emotion tracking for addition app: {e2}")
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
    print("Frustration analysis loaded for addition app")
except Exception as e:
    print(f"Warning: Frustration analysis not available for addition app: {e}")
    FRUSTRATION_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'addition_learning_secret_key'

# Session management for practice tracking
current_sessions = {}

# Load preferred modes
def load_preferred_modes():
    try:
        df = pd.read_csv('preferred_modes.csv')
        modes_dict = df.set_index('learner_id')['preferred_mode'].to_dict()
        
        # Only return the modes that exist in the CSV
        return modes_dict
    except Exception as e:
        print(f"Warning: Could not load preferred modes: {e}")
        # Return empty dict if CSV can't be loaded
        return {}

# Addition learning data
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
            'visual_elements': ['⭐⭐⭐⭐⭐', '⭐⭐', '⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐']
        },
        {
            'question': 'There are 2 balloons 🎈🎈. Then 4 more 🎈🎈🎈🎈. How many balloons in total?',
            'answer': 6,
            'visual_elements': ['🎈🎈', '🎈🎈🎈🎈', '🎈🎈🎈🎈🎈🎈']
        },
        {
            'question': 'You see 3 fish 🐟🐟🐟. I add 5 more 🐟🐟🐟🐟🐟. How many fish now?',
            'answer': 8,
            'visual_elements': ['🐟🐟🐟', '🐟🐟🐟🐟🐟', '🐟🐟🐟🐟🐟🐟🐟🐟']
        }
    ],
    'auditory': [
        {
            'question': 'I say: 2… then 3 more. What number do you get?',
            'answer': 5,
            'audio_text': 'I say: 2… then 3 more. What number do you get?'
        },
        {
            'question': 'I clap 4 times 👏👏👏👏, then 1 more 👏. How many claps total?',
            'answer': 5,
            'audio_text': 'I clap 4 times, then 1 more. How many claps total?'
        },
        {
            'question': 'I say: 5 birds… then 2 more birds join. How many birds now?',
            'answer': 7,
            'audio_text': 'I say: 5 birds… then 2 more birds join. How many birds now?'
        },
        {
            'question': 'I knock 3 times 🔔🔔🔔, then 3 more 🔔🔔🔔. How many knocks total?',
            'answer': 6,
            'audio_text': 'I knock 3 times, then 3 more. How many knocks total?'
        },
        {
            'question': 'I say: 6 candies… then I add 1 candy. How many candies now?',
            'answer': 7,
            'audio_text': 'I say: 6 candies… then I add 1 candy. How many candies now?'
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
    """Homepage - automatically redirects to learning for first available learner or shows selection"""
    from flask import redirect
    
    # Check if learner_id is specified in URL
    learner_id = request.args.get('learner_id', type=int)
    
    # If no specific learner_id, get the first available one from CSV
    if learner_id is None:
        preferred_modes = load_preferred_modes()
        if preferred_modes:
            # Get the first learner_id from the CSV
            first_learner_id = list(preferred_modes.keys())[0]
            # Redirect directly to the learning page
            return redirect(f'/addition_learning?learner_id={first_learner_id}')
        else:
            # If no CSV data, show error
            return "Error: No learner data found in preferred_modes.csv", 404
    
    # If learner_id is specified, show the selection page
    return render_template('index.html', learner_id=learner_id)

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
    """Addition learning main page - determines mode and shows examples"""
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
    """Practice questions page with emotion tracking session"""
    learner_id = request.args.get('learner_id', 1, type=int)
    mode = request.args.get('mode', 'kinesthetic')
    
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
    
    return render_template('addition_practice.html',
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

@app.route('/start_practice_emotion_tracking/<session_id>', methods=['POST'])
def start_practice_emotion_tracking(session_id):
    """Start emotion tracking for the current practice question"""
    if session_id not in current_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    success = emotion_tracker.start_emotion_tracking()
    return jsonify({'success': success})

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

def save_addition_practice_session(session_info):
    """No-op: CSV logging removed."""
    return

def save_addition_frustration_report(session_info):
    """No-op: CSV logging removed."""
    return

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files for auditory mode"""
    try:
        # Look for audio files in static/audio directory
        audio_path = os.path.join('static', 'audio', filename)
        if os.path.exists(audio_path):
            return send_file(audio_path)
        
        # Fallback: look in current directory
        if os.path.exists(filename):
            return send_file(filename)
        
        # If file doesn't exist, return 404
        return "Audio file not found", 404
    except Exception as e:
        return f"Error serving audio: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)
