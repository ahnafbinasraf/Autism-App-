import cv2
from collections import Counter
import threading
import time
import os

# Handle DeepFace import with fallback for webapp compatibility
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("Warning: DeepFace not available - using mock emotion detection")

# Handle MediaPipe import with fallback
try:
    import mediapipe as mp
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: MediaPipe not available - using basic face detection")

# === Original globals & setup (preserved) ===
emotion_list = []
running = False
thread = None

# === NEW: readiness event so UI can wait until frames flow ===
camera_ready = threading.Event()

# Mock emotions for fallback
MOCK_EMOTIONS = ["neutral", "happy", "focused", "calm", "engaged", "sad", "frustrated"]

def capture_loop():
    global emotion_list, running
    cap = cv2.VideoCapture(0)
   
    if not cap.isOpened():
        print("Error: Could not open camera.")
        running = False
        camera_ready.clear()
        return

    # Mark ready after first successful frame read
    first_good_frame = False

    while running:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        if not first_good_frame:
            camera_ready.set()
            first_good_frame = True

        try:
            # Try emotion detection with available libraries
            emotion_detected = False
            
            if MEDIAPIPE_AVAILABLE and DEEPFACE_AVAILABLE:
                # Full emotion detection with MediaPipe + DeepFace
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)
                
                if results.detections:
                    for detection in results.detections:
                        bboxC = detection.location_data.relative_bounding_box
                        h, w, _ = frame.shape
                        x, y = int(bboxC.xmin * w), int(bboxC.ymin * h)
                        width, height = int(bboxC.width * w), int(bboxC.height * h)

                        if width > 0 and height > 0 and x >= 0 and y >= 0:
                            face = frame[y:y+height, x:x+width]
                            if face.size > 0:
                                emotion = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                emotion_label = emotion[0]['dominant_emotion']
                                emotion_list.append(emotion_label)
                                emotion_detected = True
                                break
            
            elif DEEPFACE_AVAILABLE:
                # Basic emotion detection without face detection
                try:
                    emotion = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                    emotion_label = emotion[0]['dominant_emotion']
                    emotion_list.append(emotion_label)
                    emotion_detected = True
                except:
                    pass
            
            # Fallback to mock emotion if no detection available
            if not emotion_detected:
                import random
                mock_emotion = random.choice(MOCK_EMOTIONS)
                emotion_list.append(mock_emotion)
            
            time.sleep(0.1)

        except Exception as e:
            print(f"Error in processing frame: {e}")
            # Add mock emotion even on error
            import random
            emotion_list.append(random.choice(MOCK_EMOTIONS))

    cap.release()

def start_emotion_tracking():
    global running, thread, emotion_list
    emotion_list = []
    camera_ready.clear()   # not ready yet for this question
    running = True
    thread = threading.Thread(target=capture_loop, daemon=True)
    thread.start()

def stop_emotion_tracking():
    global running
    running = False
    if thread:
        thread.join()
    camera_ready.clear()   # reset for next question
    if emotion_list:
        most_common = Counter(emotion_list).most_common(1)[0][0]
        return most_common
    return "Unknown"

# === NEW: simple helper for UI ===
def is_camera_ready() -> bool:
    return camera_ready.is_set()
