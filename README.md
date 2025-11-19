# Creator

This project was created for research purposes, which includes the following members: Ahnaf Bin Asraf, Iwrsiya Nawar and Syed Quafshat Taiyush Hamd

# Adaptive Learning App with Emotion Tracking

This repository contains a complete, privacy-first learning system designed to support diverse learning preferences. It includes a browser-based learning app, practice modules for addition and subtraction, emotion tracking, frustration analysis, and local analytics. The system adapts presentation (visual, auditory, kinesthetic) based on performance and affect.

## Key Features
- Adaptive learning across visual, auditory, and kinesthetic modes
- Real-time emotion tracking with local processing and mock fallbacks
- Frustration analysis for mode switching and research use
- Modular practice apps (addition and subtraction)
- Transparent, local data logging in CSV (optional in practice apps)
- Professional, accessible UI and templates

## System Requirements
- Python 3.7+
- Webcam (for emotion tracking; optional with mock fallback)
- OS with permissions to access camera (if using advanced tracking)

## Installation
1. Create and activate a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure (selected)
```
.
├── learning_webapp.py              # Main Flask web application
├── learning_webapp_core.py         # Core logic/utilities for webapp
├── run_learning_webapp.py          # Launcher for the learning webapp
├── app.py                          # Addition practice app (Flask)
├── run_addition_app.py             # Launcher for addition practice
├── subtraction_app.py              # Subtraction learning app (Flask)
├── run_subtraction_app.py          # Launcher for subtraction practice
├── preferred_mode_analyzer.py      # Determines preferred mode from reports
├── emotion_tracker_webapp.py       # Advanced emotion tracking (DeepFace + MediaPipe)
├── emotion_tracker_simple.py       # Lightweight tracker (simulation)
├── Frustraiton.py                  # Legacy: frustration scoring (batch)
├── frustration_webapp.py           # Frustration analysis for the webapp
├── LearningApp.py                  # Legacy: original app ported to Python file
├── templates/                      # HTML templates (learning and practice)
├── questions.csv                   # Sample questions for the learning app
├── preferred_modes.csv             # Output: inferred preferred modes
├── outputs/                        # Generated ITS plots
└── requirements.txt                # Python dependencies
```

## Components

### Learning WebApp (`learning_webapp.py`, `run_learning_webapp.py`)
A Flask-based web application providing learning activities in visual, auditory, and kinesthetic modes. Integrates emotion tracking and frustration analysis to adapt mode selection.

- Default port: 5002
- Launch:
  ```bash
  python run_learning_webapp.py
  # Open http://localhost:5002
  ```

### Preferred Mode Analyzer (`preferred_mode_analyzer.py`)
Analyzes frustration reports to identify each learner’s lowest-frustration mode.

- Inputs: `frustration_report{learner_id}.csv`
- Output: `preferred_modes.csv`
- Run:
  ```bash
  python preferred_mode_analyzer.py
  # or: python preferred_mode_analyzer.py <input_csv> <output_csv>
  ```

### Addition Practice (`app.py`, `run_addition_app.py`)
Addition practice delivered in the learner’s preferred mode with emotion tracking during questions. Practice CSV logging is disabled by default for privacy.

- Default port: 5001
- Launch:
  ```bash
  python run_addition_app.py
  # Open http://localhost:5001
  ```

### Subtraction Practice (`subtraction_app.py`, `run_subtraction_app.py`)
Subtraction learning and practice following the same pattern as addition, with support for emotion tracking and frustration-aware adaptation.

- Default port: 5003
- Launch:
  ```bash
  python run_subtraction_app.py
  # Open http://localhost:5003
  ```

### Emotion Tracking
- Advanced: `emotion_tracker_webapp.py` (DeepFace + MediaPipe via OpenCV)
- Simple: `emotion_tracker_simple.py` (simulation, no camera required)
- The apps automatically fall back to the simple tracker if advanced libraries are unavailable.

### Frustration Analysis
- Web integration: `frustration_webapp.py`
- Legacy batch tool: `Frustraiton.py` (per-test scoring)

## Data and Analytics
- Preferred mode: `preferred_modes.csv`
- Learning logs: `learner_log{learner_id}.csv`
- Practice logs (optional): `addition_practice_log{learner_id}.csv`, `subtraction_practice_log{learner_id}.csv`
- Frustration reports: `frustration_report{learner_id}.csv`
- ITS plots (if generated): `outputs/its_addition_{learner_id}.png`, `outputs/its_subtraction_{learner_id}.png`

## Running the Complete Flow (manual)
1. Start the learning webapp:
   ```bash
   python run_learning_webapp.py
   ```
2. After a session, run the preferred mode analyzer:
   ```bash
   python preferred_mode_analyzer.py
   ```
3. Start the addition practice app:
   ```bash
   python run_addition_app.py
   ```
4. Start the subtraction practice app:
   ```bash
   python run_subtraction_app.py
   ```

## Privacy and Security
- All processing is local; no data is transmitted externally.
- Emotion tracking uses your device’s camera only during active sessions.
- CSV outputs are stored locally and can be deleted at any time.

## Troubleshooting
- Camera issues: ensure permissions and that no other app is using the camera.
- Ports in use: close other processes using ports 5001, 5002, or 5003.
- Dependencies: reinstall with `pip install -r requirements.txt`.
- Python version: verify with `python --version` (3.7+ required).

## Notes on Accessibility and Design
- Calm, professional UI with accessible typography and color contrast
- Clear navigation and consistent layout
- Immediate, unambiguous feedback for actions

## License
This project is provided for research and educational use. Add an explicit license file if you intend to distribute or use beyond personal/research contexts.



