from flask import Flask, render_template, request, jsonify, session, send_file
import os
import csv

app = Flask(__name__)
app.secret_key = 'subtraction_learning_secret_key'

# Load preferred modes
def load_preferred_modes():
    try:
        modes_dict = {}
        with open('preferred_modes.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                learner_id = int(row['learner_id'])
                preferred_mode = row['preferred_mode'].strip()
                modes_dict[learner_id] = preferred_mode
        
        return modes_dict
    except Exception as e:
        print(f"Warning: Could not load preferred modes: {e}")
        # Return empty dict if CSV can't be loaded
        return {}

# Subtraction learning data
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

SUBTRACTION_PRACTICE = {
    'visual': [
        {
            'question': 'You see 3 cats 🐱🐱🐱. 1 cat runs away. How many cats are left?',
            'answer': 2,
            'visual_elements': ['🐱🐱🐱', '🐱', '🐱🐱']
        },
        {
            'question': 'There are 6 stars ⭐⭐⭐⭐⭐⭐. Take away 2 stars. How many now?',
            'answer': 4,
            'visual_elements': ['⭐⭐⭐⭐⭐⭐', '⭐⭐', '⭐⭐⭐⭐']
        },
        {
            'question': 'You see 5 balloons 🎈🎈🎈🎈🎈. 3 fly away. How many left?',
            'answer': 2,
            'visual_elements': ['🎈🎈🎈🎈🎈', '🎈🎈🎈', '🎈🎈']
        },
        {
            'question': 'You see 8 fish 🐟🐟🐟🐟🐟🐟🐟🐟. 5 swim away. How many left?',
            'answer': 3,
            'visual_elements': ['🐟🐟🐟🐟🐟🐟🐟🐟', '🐟🐟🐟🐟🐟', '🐟🐟🐟']
        },
        {
            'question': 'There are 7 apples 🍎🍎🍎🍎🍎🍎🍎. You eat 4. How many apples left?',
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
            'question': 'Box has 5 hearts 💖💖💖💖💖. Remove 2 hearts. How many hearts are left?',
            'answer': 3,
            'task': 'Box has 5 hearts 💖💖💖💖💖. Drag 2 hearts to the drop box. Count how many hearts remain.'
        },
        {
            'question': 'Box has 6 stars ⭐⭐⭐⭐⭐⭐. Remove 3 stars. How many stars are left?',
            'answer': 3,
            'task': 'Box has 6 stars ⭐⭐⭐⭐⭐⭐. Drag 3 stars to the drop box. Count how many stars remain.'
        },
        {
            'question': 'Box has 7 apples 🍎🍎🍎🍎🍎🍎🍎. Remove 4 apples. How many apples are left?',
            'answer': 3,
            'task': 'Box has 7 apples 🍎🍎🍎🍎🍎🍎🍎. Drag 4 apples to the drop box. Count how many apples remain.'
        },
        {
            'question': 'Box has 4 blocks 🟥🟥🟥🟥. Remove 1 block. How many blocks are left?',
            'answer': 3,
            'task': 'Box has 4 blocks 🟥🟥🟥🟥. Drag 1 block to the drop box. Count how many blocks remain.'
        },
        {
            'question': 'Box has 8 balloons 🎈🎈🎈🎈🎈🎈🎈🎈. Remove 5 balloons. How many balloons are left?',
            'answer': 3,
            'task': 'Box has 8 balloons 🎈🎈🎈🎈🎈🎈🎈🎈. Drag 5 balloons to the drop box. Count how many balloons remain.'
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
            return redirect(f'/subtraction_learning?learner_id={first_learner_id}')
        else:
            # If no CSV data, show error
            return "Error: No learner data found in preferred_modes.csv", 404
    
    # If learner_id is specified, show the selection page
    return render_template('subtraction_index.html', learner_id=learner_id)

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
            'description': 'You learn best through listening and sound. You\'ll hear subtraction stories and learn through audio instructions.'
        }
    }
    
    return jsonify({
        'mode': preferred_mode,
        'title': mode_info[preferred_mode]['title'],
        'description': mode_info[preferred_mode]['description']
    })

@app.route('/subtraction_learning')
def subtraction_learning():
    """Subtraction learning main page - determines mode and shows examples"""
    learner_id = request.args.get('learner_id', 1, type=int)
    
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
    """Practice questions page"""
    learner_id = request.args.get('learner_id', 1, type=int)
    mode = request.args.get('mode', 'kinesthetic')
    
    practice_questions = SUBTRACTION_PRACTICE.get(mode, [])
    
    return render_template('subtraction_practice.html',
                         mode=mode,
                         practice_questions=practice_questions,
                         learner_id=learner_id)

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
    app.run(debug=False, host='0.0.0.0', port=5003, use_reloader=False)
