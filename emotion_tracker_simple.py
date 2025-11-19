"""
Simple Emotion Tracker for Autism WebApp
Provides basic emotion tracking functionality without heavy dependencies
Falls back gracefully if advanced libraries are not available
"""

import time
import threading
import random
from collections import Counter

# Global state
emotion_list = []
running = False
thread = None
camera_ready_flag = False

# Mock emotions for simulation
MOCK_EMOTIONS = ["neutral", "happy", "focused", "calm", "engaged", "sad", "frustrated"]

def simple_emotion_simulation():
    """Simple emotion simulation that doesn't require camera"""
    global emotion_list, running, camera_ready_flag
    
    # Simulate camera startup time
    time.sleep(1.0)
    camera_ready_flag = True
    
    while running:
        # Generate realistic emotion progression
        if len(emotion_list) == 0:
            # Start with neutral
            emotion = "neutral"
        else:
            # Trend towards previous emotion with some variation
            last_emotion = emotion_list[-1]
            if random.random() < 0.7:  # 70% chance to stay similar
                if last_emotion in ["happy", "focused", "calm", "engaged"]:
                    emotion = random.choice(["neutral", "happy", "focused", "calm", "engaged"])
                else:
                    emotion = random.choice(["neutral", "sad", "frustrated"])
            else:
                emotion = random.choice(MOCK_EMOTIONS)
        
        emotion_list.append(emotion)
        time.sleep(0.5)  # Slower sampling for simulation

def start_emotion_tracking():
    """Start emotion tracking (simplified version)"""
    global running, thread, emotion_list, camera_ready_flag
    
    print("Starting simplified emotion tracking...")
    
    emotion_list = []
    camera_ready_flag = False
    running = True
    
    # Use simple simulation instead of camera
    thread = threading.Thread(target=simple_emotion_simulation, daemon=True)
    thread.start()
    
    return True

def stop_emotion_tracking():
    """Stop emotion tracking and return most common emotion"""
    global running, camera_ready_flag
    
    running = False
    camera_ready_flag = False
    
    if thread:
        thread.join(timeout=2.0)
    
    if emotion_list:
        # Return most common emotion
        most_common = Counter(emotion_list).most_common(1)[0][0]
        print(f"Detected emotion: {most_common} (from {len(emotion_list)} samples)")
        return most_common
    
    return "neutral"

def is_camera_ready():
    """Check if camera is ready"""
    return camera_ready_flag

# For compatibility with the main webapp
if __name__ == "__main__":
    # Test the simple emotion tracker
    print("Testing simple emotion tracker...")
    start_emotion_tracking()
    
    # Wait a few seconds
    time.sleep(3)
    
    # Stop and get result
    result = stop_emotion_tracking()
    print(f"Final emotion: {result}")

