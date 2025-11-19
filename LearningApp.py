import tkinter as tk
from tkinter import ttk, messagebox
import time
import csv
import os
import random
import pygame
import pandas as pd
import webbrowser

# Handle Emoitiontracker import with TensorFlow compatibility issues
def import_emotion_tracker():
    """Import emotion tracker with fallback to mock if TensorFlow issues occur"""
    try:
        # Suppress TensorFlow warnings during import
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        
        import warnings
        warnings.filterwarnings('ignore')
        
        import Emoitiontracker
        print("Emotion tracking available")
        return Emoitiontracker, True
        
    except (ImportError, KeyboardInterrupt, TimeoutError, Exception) as e:
        print(f"Warning: Emotion tracking not available ({type(e).__name__}): using simulation mode")
        print("    The application will work with simulated emotion tracking.")
        
        # Create a mock Emoitiontracker module for compatibility
        class MockEmotionTracker:
            @staticmethod
            def start_emotion_tracking():
                print("Mock: Starting emotion tracking simulation")
                return True
                
            @staticmethod
            def stop_emotion_tracking():
                print("Mock: Stopping emotion tracking simulation")
                emotions = ["neutral", "happy", "focused", "calm", "engaged", "sad", "frustrated"]
                return random.choice(emotions)
                
            @staticmethod
            def is_camera_ready():
                return True
        
        return MockEmotionTracker(), False

# Import emotion tracker with better error handling
try:
    Emoitiontracker, EMOTION_TRACKER_AVAILABLE = import_emotion_tracker()
except Exception as e:
    print(f"Warning: Critical error loading emotion tracker: {e}")
    # Create emergency fallback
    class EmergencyMockTracker:
        @staticmethod
        def start_emotion_tracking():
            return True
        @staticmethod 
        def stop_emotion_tracking():
            return "neutral"
        @staticmethod
        def is_camera_ready():
            return True
    Emoitiontracker = EmergencyMockTracker()
    EMOTION_TRACKER_AVAILABLE = False

pygame.mixer.init()

# --- Files/paths (unchanged logic) ---
html_file_path = os.path.abspath('drag_task.html')
test_number = 1
PREFERRED_MODE_FILE = "preferred_mode.csv"
MODES = ["visual", "auditory", "kinesthetic"]

# --- Load questions with UTF-8 encoding and visual elements support ---
QUESTION_BANK = {}
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

# --- App state (unchanged logic) ---
current_question = None
question_start_time = None
learner_id = None
current_mode = "visual"
question_index = 0
session_data = []

# =========================
#  Aesthetic UI: styles only
# =========================
BG = "#FFF7F2"          # warm paper
CARD = "#FFFFFF"        # white card
PRIMARY = "#6C8EF3"     # soft blue
PRIMARY_DARK = "#4B6EE8"
ACCENT = "#72D7A7"      # minty success
TEXT = "#2E2E2E"
SUBTLE = "#6B6B6B"

root = tk.Tk()
root.title("⭐ Super Learning Quiz")
root.geometry("720x520")
root.minsize(620, 420)
root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")

style.configure("TLabel", background=BG, foreground=TEXT, font=("Helvetica", 13), padding=4)
style.configure("Small.TLabel", background=BG, foreground=SUBTLE, font=("Helvetica", 11), padding=2)
style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Helvetica", 20, "bold"))
style.configure("Card.TFrame", background=CARD)
style.configure("TEntry", padding=6, font=("Helvetica", 13))
style.configure("TButton",
    padding=10,
    font=("Helvetica", 13, "bold"),
    background=PRIMARY,
    foreground="white",
    borderwidth=0
)
style.map("TButton",
    background=[('active', PRIMARY_DARK), ('pressed', PRIMARY_DARK)],
    foreground=[('active', 'white')]
)
style.configure("TProgressbar", troughcolor="#EAEAEA")

def make_card(parent):
    wrapper = ttk.Frame(parent, padding=14, style="Card.TFrame")
    inner = tk.Frame(wrapper, bg=CARD, bd=0, highlightthickness=0)
    inner.pack(fill="both", expand=True)
    return wrapper, inner

# --- Root layout
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
app_frame = ttk.Frame(root, padding=18)
app_frame.grid(row=0, column=0, sticky="nsew")
app_frame.columnconfigure(0, weight=1)
app_frame.rowconfigure(3, weight=1)

# --- Header
header = ttk.Label(app_frame, text="⭐ Super Learning Quiz", style="Title.TLabel")
header.grid(row=0, column=0, pady=(6, 8), sticky="n")
subheader = ttk.Label(app_frame, text="Let’s learn in a fun way! Pick your answer and do your best. 🌈", style="Small.TLabel")
subheader.grid(row=1, column=0, pady=(0, 10), sticky="n")

# --- Learner card
id_card, id_inner = make_card(app_frame)
id_card.grid(row=2, column=0, sticky="ew", pady=(4, 16))
for i in range(3):
    id_inner.grid_columnconfigure(i, weight=1)

id_title = tk.Label(id_inner, text="👤 Who’s playing today?", bg=CARD, fg=TEXT, font=("Helvetica", 16, "bold"))
id_title.grid(row=0, column=0, columnspan=3, pady=(8, 12))

question_label = tk.Label(id_inner, text="Type your Learner ID:", bg=CARD, fg=TEXT, font=("Helvetica", 13))
question_label.grid(row=1, column=0, sticky="e", padx=(6, 6), pady=4)

entry = ttk.Entry(id_inner, width=24, font=("Helvetica", 13))
entry.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=4)

submit_button = ttk.Button(id_inner, text="Let’s Start!", command=lambda: start_quiz(entry.get()))
submit_button.grid(row=1, column=2, sticky="w", padx=(6, 6), pady=4)

tip = tk.Label(id_inner, text="Tip: Ask a grown-up if you’re not sure about your ID. 😊", bg=CARD, fg=SUBTLE, font=("Helvetica", 11))
tip.grid(row=2, column=0, columnspan=3, pady=(4, 10))

# --- Quiz card (hidden until start)
quiz_card, quiz_inner = make_card(app_frame)
quiz_card.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
quiz_card.grid_remove()

quiz_inner.grid_columnconfigure(0, weight=1)
quiz_inner.grid_rowconfigure(1, weight=1)

mode_label = tk.Label(quiz_inner, text="", bg=CARD, fg=TEXT, font=("Helvetica", 16, "bold"))
mode_label.grid(row=0, column=0, sticky="w", pady=(8, 2), padx=8)

# Progress bar + label
progress_frame = tk.Frame(quiz_inner, bg=CARD)
progress_frame.grid(row=0, column=0, sticky="e", pady=(8, 2), padx=8)
progress_var = tk.DoubleVar(value=0.0)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=220, mode="determinate", variable=progress_var)
progress_label = tk.Label(progress_frame, text="", bg=CARD, fg=SUBTLE, font=("Helvetica", 11))
progress_bar.grid(row=0, column=0, padx=(0, 8))
progress_label.grid(row=0, column=1)

# Question text
question_box = tk.Label(quiz_inner, text="", bg=CARD, fg=TEXT, wraplength=640, justify="left", font=("Helvetica", 15))
question_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 8))

# Visual elements display area (for counting questions)
visual_elements_frame = tk.Frame(quiz_inner, bg=CARD)
visual_elements_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 8))
visual_elements_frame.grid_remove()  # Hidden by default

# Answer row
answer_row = tk.Frame(quiz_inner, bg=CARD)
answer_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 10))
answer_row.grid_columnconfigure(0, weight=1)

response_entry = ttk.Entry(answer_row, width=40, font=("Helvetica", 13))
response_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

submit_answer_button = ttk.Button(answer_row, text="✅ Submit", command=lambda: submit_answer(response_entry.get()))
submit_answer_button.grid(row=0, column=1, padx=(0, 4))

skip_button = ttk.Button(answer_row, text="⏭️ Skip for now", command=lambda: submit_answer("SKIP"))
skip_button.grid(row=0, column=2)

footer = ttk.Label(app_frame, text="If you need a break, you can skip and come back later. 💛", style="Small.TLabel")
footer.grid(row=4, column=0, pady=(6, 0))

# --- Friendly progress helpers (visual only, logic unchanged)
def _set_progress(curr_index):
    total_q = len(QUESTION_BANK[current_mode])
    progress_label.config(text=f"Question {curr_index} of {total_q}")
    progress_bar['maximum'] = max(1, total_q)
    progress_var.set(curr_index - 1)

# ======================
#  Original logic below
# ======================
def get_frustration(learner_id):
    if not os.path.exists(f"frustration_report{learner_id}.csv"):
        return None
    with open(f"frustration_report{learner_id}.csv", newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["learner_id"] == learner_id:
                return float(row["frustration_score"])
    return None

def get_preferred_mode(learner_id):
    if not os.path.exists(PREFERRED_MODE_FILE):
        return None
    with open(PREFERRED_MODE_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["learner_id"] == learner_id:
                return row["preferred_mode"]
    return None

def get_last_used_mode(learner_id):
    """Get the mode used in the most recent session for this learner"""
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
    file_exists = os.path.exists(PREFERRED_MODE_FILE)
    with open(PREFERRED_MODE_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["learner_id", "preferred_mode"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({"learner_id": learner_id, "preferred_mode": mode})

def get_next_mode(current):
    idx = MODES.index(current)
    return MODES[(idx + 1) % len(MODES)]



def get_test_count(learner_id):
    """Get the highest test number for a learner ID, return 0 if no previous tests"""
    log_file = f"learner_log{learner_id}.csv"
    if not os.path.exists(log_file):
        return 0
    
    try:
        df = pd.read_csv(log_file, encoding='utf-8')
        if "test_number" in df.columns and len(df) > 0:
            # Filter out NaN values and get the maximum
            valid_test_numbers = df["test_number"].dropna()
            if len(valid_test_numbers) > 0:
                return int(valid_test_numbers.max())
        return 0
    except Exception as e:
        print(f"Error reading test count for learner {learner_id}: {e}")
        return 0

def start_quiz(id_input):
    global learner_id, current_mode, question_index, session_data, test_number
    learner_id = id_input.strip()
    if not learner_id:
        messagebox.showerror("Oops!", "Please type your Learner ID so we know it’s you. 😊")
        return

    preferred_mode = get_preferred_mode(learner_id)
    frustration_score = get_frustration(learner_id)
    last_used_mode = get_last_used_mode(learner_id)
    
    # Determine mode based on frustration and mode history
    if frustration_score is None:
        # No previous data - start with visual mode
        current_mode = "visual"
        print(f"🆕 New learner - starting with visual mode")
    elif frustration_score >= 0.4:
        # High frustration - switch to next mode based on last used mode
        if last_used_mode:
            current_mode = get_next_mode(last_used_mode)
            print(f"🔄 High frustration detected ({frustration_score:.2f})! Switching from {last_used_mode} to {current_mode}")
        else:
            # Fallback if no mode history
            current_mode = "auditory"
            print(f"🔄 High frustration detected ({frustration_score:.2f})! Switching to {current_mode} mode")
        
        messagebox.showinfo("Mode Switch!", f"Let's try {current_mode.capitalize()} mode this time! 💡")
    else:
        # Low frustration - keep preferred mode or use last used mode
        if preferred_mode:
            current_mode = preferred_mode
        elif last_used_mode:
            current_mode = last_used_mode
        else:
            current_mode = "visual"
        save_preferred_mode(learner_id, current_mode)
        print(f"😌 Continuing with {current_mode} mode (frustration: {frustration_score:.2f})")

    test_number = get_test_count(learner_id) + 1
    question_index = 0
    session_data = []
    
    # Display test information to user
    print(f"Starting Test #{test_number} for Learner {learner_id}")
    messagebox.showinfo("Quiz Started!", f"Welcome back, Learner {learner_id}!\nThis is your Test #{test_number}. Good luck! 🍀")

    id_card.grid_remove()
    quiz_card.grid()
    mode_label.config(text=f"Mode: {current_mode.capitalize()}")
    _set_progress(1)
    display_question()

# --- Camera loader overlay (NEW UI only; logic of flow preserved)
loading_win = None
def show_camera_loading():
    global loading_win
    if loading_win is not None:
        return
    loading_win = tk.Toplevel(root)
    loading_win.title("Starting camera")
    loading_win.geometry("360x130")
    loading_win.transient(root)
    loading_win.grab_set()
    frm = ttk.Frame(loading_win, padding=16)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="🎥 Starting the camera… one moment please.", font=("Helvetica", 12)).pack(pady=(4,8))
    bar = ttk.Progressbar(frm, mode="indeterminate", length=280)
    bar.pack()
    bar.start(10)

def hide_camera_loading():
    global loading_win
    if loading_win is not None:
        try:
            loading_win.grab_release()
        except Exception:
            pass
        loading_win.destroy()
        loading_win = None

def display_question():
    """Gate each question behind camera readiness; render UI after ready."""
    global current_question
    total_q = len(QUESTION_BANK[current_mode])
    if question_index >= total_q:
        save_session()
        messagebox.showinfo("Great job!", f"All done with {current_mode.capitalize()} mode! Time for a little break. 🌟")
        root.quit()
        return

    # Prepare but do NOT show contents yet
    current_question = QUESTION_BANK[current_mode][question_index]
    question_text = current_question["question"]

    # Clear & hide inputs while waiting
    question_box.config(text="")
    response_entry.delete(0, tk.END)
    submit_answer_button.configure(text="✅ Submit")
    progress_curr = question_index + 1
    _set_progress(progress_curr)

    # Start camera first, then show loader + poll
    Emoitiontracker.start_emotion_tracking()
    show_camera_loading()

    start_ts = time.time()
    def wait_for_camera():
        ready = getattr(Emoitiontracker, "is_camera_ready", lambda: False)()
        if ready or (time.time() - start_ts) > 6.0:  # safe timeout
            hide_camera_loading()
            render_question_contents(question_text)
        else:
            root.after(120, wait_for_camera)
    root.after(120, wait_for_camera)

def render_question_contents(question_text: str):
    """Show the actual question once camera is ready; start the timer now."""
    global question_start_time
    question_start_time = time.time()

    # Clear visual elements first
    clear_visual_elements()

    if current_mode == "auditory":
        pygame.mixer.music.load(question_text)
        pygame.mixer.music.play()
        question_box.config(text="Listen carefully, then type your answer below:")
    elif current_mode == "kinesthetic":
        # For kinesthetic mode, question_text is the HTML filename
        # Get the task description based on the task number
        task_descriptions = {
            "kinesthetic_task_1.html": "Drag the red circle to the blue square",
            "kinesthetic_task_2.html": "Move all triangles to the top area", 
            "kinesthetic_task_3.html": "Arrange the shapes from smallest to largest",
            "kinesthetic_task_4.html": "Drag the star to match with another star",
            "kinesthetic_task_5.html": "Place all the animals in the zoo area",
            "kinesthetic_task_6.html": "Sort the fruits into the basket",
            "kinesthetic_task_7.html": "Connect the dots to make a line",
            "kinesthetic_task_8.html": "Drag the puzzle pieces to complete the picture",
            "kinesthetic_task_9.html": "Move the blocks to build a tower",
            "kinesthetic_task_10.html": "Place the letters in alphabetical order"
        }
        task_description = task_descriptions.get(question_text, "Complete the kinesthetic task")
        question_box.config(text=f"🖱️ Task: {task_description}\n(When you finish, type 'done' and press Submit.)")
        # Open the specific kinesthetic task file for this question
        kinesthetic_file_path = os.path.abspath(question_text)
        webbrowser.open(f'file://{kinesthetic_file_path}')
    else:
        # Visual mode - display question and elements
        question_box.config(text=f"🧠 Question: {question_text}")
        
        # Display visual elements if available
        if "elements" in current_question and current_question["elements"]:
            display_visual_elements(current_question["elements"])

def clear_visual_elements():
    """Clear all visual elements from the display"""
    for widget in visual_elements_frame.winfo_children():
        widget.destroy()
    visual_elements_frame.grid_remove()

def display_visual_elements(elements):
    """Display visual elements for counting questions"""
    # Clear any existing elements
    clear_visual_elements()
    
    # Show the visual elements frame
    visual_elements_frame.grid()
    
    # Configure grid for flexible layout
    max_columns = 10  # Maximum elements per row
    
    for i, element in enumerate(elements):
        row = i // max_columns
        col = i % max_columns
        
        # Create label for each element with larger font
        element_label = tk.Label(
            visual_elements_frame, 
            text=element.strip(), 
            font=("Helvetica", 28), 
            bg=CARD, 
            fg=TEXT,
            padx=10,
            pady=5
        )
        element_label.grid(row=row, column=col, padx=5, pady=5)
    
    # Configure column weights for centering
    for col in range(max_columns):
        visual_elements_frame.grid_columnconfigure(col, weight=1)

def submit_answer(answer):
    # Original logic preserved
    global question_index
    time_taken = time.time() - question_start_time
    correct = (answer.strip().lower() == current_question["answer"].lower())
    skipped = (answer.strip().upper() == "SKIP")
    if answer == "":
        skipped = True

    current_emotion = Emoitiontracker.stop_emotion_tracking()

    session_data.append({
        "learner_id": learner_id,
        "test_number": test_number,
        "mode": current_mode,
        "question": current_question["question"],
        "response_time_sec": round(time_taken, 2),
        "correct": correct,
        "skipped": skipped,
        "emotion": current_emotion
    })

    question_index += 1
    display_question()

def save_session():
    # Original logic preserved with UTF-8 encoding for emoji support
    log_file = f"learner_log{learner_id}.csv"
    file_exists = os.path.exists(log_file)
    with open(log_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=session_data[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(session_data)

root.mainloop()
