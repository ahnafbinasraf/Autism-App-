#!/usr/bin/env python3
"""
Simple Autism Learning App Starter
Just run this file to start the complete learning session!
"""

import subprocess
import time
import os
import sys
import webbrowser

def print_step(step_num, title, description):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*60}")
    print(description)
    print()

def main():
    print("Autism Learning App - Complete Session")
    print("=" * 60)
    print("This will guide you through the complete learning experience!")
    print()
    
    # Step 1: Autism WebApp
    print_step(1, "Autism WebApp", 
              "Starting the main autism learning interface...\n"
              "Complete all Visual, Auditory, and Kinesthetic questions.\n"
              "When you're done, press Ctrl+C in this terminal to continue.")
    
    process = None
    try:
        # Start Autism WebApp
        process = subprocess.Popen([sys.executable, "run_autism_webapp.py"])
        
        # Open browser
        time.sleep(3)
        webbrowser.open('http://localhost:5002')
        
        print("Autism WebApp started. Browser should open automatically.")
        print("Please complete all questions in the browser.")
        print("Waiting briefly for app to initialize...")
        time.sleep(3)
        print("Autism WebApp started.")
        
    except Exception as e:
        print(f"Error: Autism WebApp failed: {e}")
        if process is not None:
            process.terminate()
    
    # Step 2: Preferred Mode Analyzer
    print_step(2, "Analyzing Preferred Learning Mode",
              "Analyzing your performance to determine your preferred learning style...")
    
    try:
        subprocess.run([sys.executable, "preferred_mode_analyzer.py"], check=True)
        print("Analysis completed.")
    except subprocess.CalledProcessError:
        print("Error: Analysis failed, but continuing...")
    
    # Step 3: Addition Practice
    print_step(3, "Addition Practice",
              "Starting addition practice with your preferred learning mode...\n"
              "Complete all addition questions in the browser.")
    
    process = None
    try:
        # Start Addition App
        process = subprocess.Popen([sys.executable, "run_addition_app.py"])
        
        # Open browser
        time.sleep(3)
        webbrowser.open('http://localhost:5001')
        
        print("Addition App started. Browser should open automatically.")
        print("Please complete all addition questions in the browser.")
        print("Waiting briefly for app to initialize...")
        time.sleep(3)
        print("Addition App started.")
        
    except Exception as e:
        print(f"Error: Addition practice failed: {e}")
        if process is not None:
            process.terminate()
    
    # Step 4: Subtraction Practice
    print_step(4, "Subtraction Practice",
              "Starting subtraction practice with your preferred learning mode...\n"
              "Complete all subtraction questions in the browser.")
    
    process = None
    try:
        # Start Subtraction App
        process = subprocess.Popen([sys.executable, "run_subtraction_app.py"])
        
        # Open browser
        time.sleep(3)
        webbrowser.open('http://localhost:5003')
        
        print("Subtraction App started. Browser should open automatically.")
        print("Please complete all subtraction questions in the browser.")
        print("Waiting briefly for app to initialize...")
        time.sleep(3)
        print("Subtraction App started.")
        
    except Exception as e:
        print(f"Error: Subtraction practice failed: {e}")
        if process is not None:
            process.terminate()
    
    # Final Step
    print_step(5, "Session Complete!",
              "Congratulations! You've started all modules!\n"
              "Note: CSV logging for practice sessions has been disabled per request.")
    
    print("\nSession Summary:")
    print("   • Autism WebApp: Completed")
    print("   • Learning Mode Analysis: Started") 
    print("   • Addition Practice: Started (no CSV logging)")
    print("   • Subtraction Practice: Started (no CSV logging)")
    print("\nGreat job! Keep practicing!")

if __name__ == "__main__":
    main()
