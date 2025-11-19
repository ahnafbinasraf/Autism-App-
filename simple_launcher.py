#!/usr/bin/env python3
"""
Simple GUI Launcher for Autism Learning App
Provides a user-friendly interface to start the complete learning session
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import threading
import time

class SimpleLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Autism Learning App Launcher")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Title
        title_label = ttk.Label(main_frame, text="🎓 Autism Learning App", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Description
        desc_text = """
Welcome to the Autism Learning App!

This app will guide you through a complete learning session:

1. 🧠 Autism WebApp - Complete questions in Visual, Auditory, and Kinesthetic modes
2. 🔍 Analysis - The app analyzes your preferred learning style
3. ➕ Addition Practice - Practice addition in your preferred mode
4. ➖ Subtraction Practice - Practice subtraction in your preferred mode

The entire session runs automatically - just click Start and follow the instructions!
        """
        
        desc_label = ttk.Label(main_frame, text=desc_text, 
                              font=('Arial', 10), justify=tk.LEFT)
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky=tk.W)
        
        # Requirements check
        self.check_requirements()
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Status labels
        self.status_labels = {}
        status_items = [
            ("Python", "Checking..."),
            ("Dependencies", "Checking..."),
            ("Camera", "Checking..."),
            ("Files", "Checking...")
        ]
        
        for i, (item, status) in enumerate(status_items):
            ttk.Label(status_frame, text=f"{item}:").grid(row=i, column=0, sticky=tk.W, padx=(0, 10))
            self.status_labels[item] = ttk.Label(status_frame, text=status)
            self.status_labels[item].grid(row=i, column=1, sticky=tk.W)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        # Start button
        self.start_button = ttk.Button(button_frame, text="🚀 Start Learning Session", 
                                      command=self.start_session, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Exit button
        exit_button = ttk.Button(button_frame, text="❌ Exit", command=self.root.quit)
        exit_button.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        
        # Status text
        self.status_text = tk.StringVar(value="Ready to start")
        status_label = ttk.Label(main_frame, textvariable=self.status_text, 
                               font=('Arial', 9))
        status_label.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
    def check_requirements(self):
        """Check system requirements"""
        def check():
            # Check Python version
            try:
                python_version = sys.version_info
                if python_version.major >= 3 and python_version.minor >= 7:
                    self.status_labels["Python"].config(text="✅ Python 3.7+")
                else:
                    self.status_labels["Python"].config(text="❌ Python 3.7+ required")
                    return
            except:
                self.status_labels["Python"].config(text="❌ Python not found")
                return
            
            # Check dependencies
            try:
                import flask
                import pandas
                import cv2
                self.status_labels["Dependencies"].config(text="✅ All dependencies installed")
            except ImportError as e:
                self.status_labels["Dependencies"].config(text=f"❌ Missing: {e.name}")
                return
            
            # Check camera
            try:
                import cv2
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    cap.release()
                    self.status_labels["Camera"].config(text="✅ Camera available")
                else:
                    self.status_labels["Camera"].config(text="❌ Camera not accessible")
            except:
                self.status_labels["Camera"].config(text="❌ Camera check failed")
            
            # Check required files
            required_files = [
                "run_autism_webapp.py",
                "run_addition_app.py", 
                "run_subtraction_app.py",
                "preferred_mode_analyzer.py",
                "requirements.txt"
            ]
            
            missing_files = []
            for file in required_files:
                if not os.path.exists(file):
                    missing_files.append(file)
            
            if missing_files:
                self.status_labels["Files"].config(text=f"❌ Missing: {', '.join(missing_files)}")
            else:
                self.status_labels["Files"].config(text="✅ All files present")
        
        # Run check in background
        threading.Thread(target=check, daemon=True).start()
    
    def start_session(self):
        """Start the learning session"""
        # Disable start button
        self.start_button.config(state='disabled')
        self.progress.start()
        self.status_text.set("Starting learning session...")
        
        # Run the main launcher in background
        def run_launcher():
            try:
                # Run the main launcher
                process = subprocess.Popen([
                    sys.executable, "main_app_launcher.py"
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                # Monitor the process
                while process.poll() is None:
                    time.sleep(1)
                
                # Get output
                stdout, stderr = process.communicate()
                
                # Update UI
                self.root.after(0, self.session_completed, process.returncode, stdout, stderr)
                
            except Exception as e:
                self.root.after(0, self.session_error, str(e))
        
        threading.Thread(target=run_launcher, daemon=True).start()
    
    def session_completed(self, return_code, stdout, stderr):
        """Handle session completion"""
        self.progress.stop()
        self.start_button.config(state='normal')
        
        if return_code == 0:
            self.status_text.set("✅ Learning session completed successfully!")
            messagebox.showinfo("Success", 
                              "Learning session completed successfully!\n\n"
                              "Thank you for using the Autism Learning App!")
        else:
            self.status_text.set("❌ Session completed with errors")
            messagebox.showerror("Error", 
                               f"Learning session completed with errors:\n\n{stderr}")
    
    def session_error(self, error_msg):
        """Handle session error"""
        self.progress.stop()
        self.start_button.config(state='normal')
        self.status_text.set("❌ Failed to start session")
        messagebox.showerror("Error", f"Failed to start learning session:\n\n{error_msg}")
    
    def run(self):
        """Run the launcher"""
        self.root.mainloop()

def main():
    """Main entry point"""
    launcher = SimpleLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
