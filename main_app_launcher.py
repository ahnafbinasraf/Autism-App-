#!/usr/bin/env python3
"""
Main Autism Learning App Launcher
Automatically runs all components in sequence:
1. Autism WebApp (run_autism_webapp.py)
2. Preferred Mode Analyzer (preferred_mode_analyzer.py)
3. Addition App (run_addition_app.py) with preferred mode
4. Subtraction App (run_subtraction_app.py) with preferred mode
"""

import subprocess
import time
import os
import sys
import signal
import csv
import threading
import requests
from pathlib import Path

class AppLauncher:
    def __init__(self):
        self.processes = []
        self.current_process = None
        self.autism_webapp_port = 5000
        self.addition_app_port = 5001
        self.subtraction_app_port = 5003  # Changed to match subtraction app
        
    def signal_handler(self, signum, frame):
        """Handle cleanup on exit"""
        print("\nShutting down all applications...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up all running processes"""
        for process in self.processes:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def wait_for_server(self, port, timeout=30):
        """Wait for server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{port}", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                time.sleep(1)
        return False
    
    def run_autism_webapp(self):
        """Run the autism webapp and wait for completion"""
        print("Starting Autism WebApp...")
        print("Please complete all questions in the browser window that opens.")
        print("The app will automatically proceed to the next step when you're done.")
        
        # Start autism webapp
        self.current_process = subprocess.Popen([
            sys.executable, "run_autism_webapp.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(self.current_process)
        
        # Wait for server to start
        if not self.wait_for_server(self.autism_webapp_port):
            print("Error: Failed to start Autism WebApp")
            return False
        
        print(f"Autism WebApp is running on http://localhost:{self.autism_webapp_port}")
        print("Please complete all questions (Visual, Auditory, Kinesthetic) to proceed...")
        
        # Monitor for completion by checking if the process is still running
        # and if the preferred_modes.csv file has been updated
        while self.current_process.poll() is None:
            time.sleep(5)
            # Check if preferred_modes.csv has been updated (indicating completion)
            if os.path.exists("preferred_modes.csv"):
                try:
                    with open("preferred_modes.csv", 'r') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        if len(rows) > 1:  # Has data beyond header
                            print("Autism WebApp questions completed.")
                            return True
                except:
                    pass
        
        print("Autism WebApp completed.")
        return True
    
    def run_preferred_mode_analyzer(self):
        """Run the preferred mode analyzer"""
        print("\nRunning Preferred Mode Analyzer...")
        
        self.current_process = subprocess.Popen([
            sys.executable, "preferred_mode_analyzer.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(self.current_process)
        
        # Wait for completion
        stdout, stderr = self.current_process.communicate()
        
        if self.current_process.returncode == 0:
            print("Preferred Mode Analysis completed.")
            return True
        else:
            print(f"Error: Preferred Mode Analyzer failed: {stderr}")
            return False
    
    def get_preferred_mode(self):
        """Read the preferred mode from CSV"""
        try:
            with open("preferred_modes.csv", 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    return row.get('preferred_mode', 'visual').lower()
        except:
            return 'visual'  # Default fallback
    
    def run_addition_app(self, preferred_mode):
        """Run the addition app with the preferred mode"""
        print(f"\nStarting Addition App with {preferred_mode} mode...")
        
        # Create a temporary script to run addition app with preferred mode
        addition_script = f"""
import os
import sys
sys.path.append('.')

# Set the preferred mode as environment variable
os.environ['PREFERRED_MODE'] = '{preferred_mode}'

# Import and run the addition app
from run_addition_app import *

if __name__ == '__main__':
    # The addition app will read the preferred mode from environment
    print(f"Running Addition App in {{preferred_mode}} mode...")
    # Add your addition app startup code here
"""
        
        with open("temp_addition_runner.py", 'w') as f:
            f.write(addition_script)
        
        self.current_process = subprocess.Popen([
            sys.executable, "temp_addition_runner.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(self.current_process)
        
        # Wait for server to start
        if not self.wait_for_server(self.addition_app_port):
            print("Error: Failed to start Addition App")
            return False
        
        print(f"Addition App is running on http://localhost:{self.addition_app_port}")
        print("Please complete all addition questions to proceed...")
        
        # Monitor for completion
        while self.current_process.poll() is None:
            time.sleep(5)
        
        print("Addition App completed.")
        
        # Clean up temporary file
        if os.path.exists("temp_addition_runner.py"):
            os.remove("temp_addition_runner.py")
        
        return True
    
    def run_subtraction_app(self, preferred_mode):
        """Run the subtraction app with the preferred mode"""
        print(f"\nStarting Subtraction App with {preferred_mode} mode...")
        
        # Create a temporary script to run subtraction app with preferred mode
        subtraction_script = f"""
import os
import sys
sys.path.append('.')

# Set the preferred mode as environment variable
os.environ['PREFERRED_MODE'] = '{preferred_mode}'

# Import and run the subtraction app
from run_subtraction_app import *

if __name__ == '__main__':
    # The subtraction app will read the preferred mode from environment
    print(f"Running Subtraction App in {{preferred_mode}} mode...")
    # Add your subtraction app startup code here
"""
        
        with open("temp_subtraction_runner.py", 'w') as f:
            f.write(subtraction_script)
        
        self.current_process = subprocess.Popen([
            sys.executable, "temp_subtraction_runner.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(self.current_process)
        
        # Wait for server to start
        if not self.wait_for_server(self.subtraction_app_port):
            print("Error: Failed to start Subtraction App")
            return False
        
        print(f"Subtraction App is running on http://localhost:{self.subtraction_app_port}")
        print("Please complete all subtraction questions to finish the learning session...")
        
        # Monitor for completion
        while self.current_process.poll() is None:
            time.sleep(5)
        
        print("Subtraction App completed.")
        
        # Clean up temporary file
        if os.path.exists("temp_subtraction_runner.py"):
            os.remove("temp_subtraction_runner.py")
        
        return True
    
    def run(self):
        """Main execution flow"""
        try:
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            print("Welcome to the Autism Learning App!")
            print("=" * 50)
            
            # Step 1: Run Autism WebApp
            if not self.run_autism_webapp():
                print("Error: Failed to complete Autism WebApp")
                return
            
            # Step 2: Run Preferred Mode Analyzer
            if not self.run_preferred_mode_analyzer():
                print("Error: Failed to complete Preferred Mode Analysis")
                return
            
            # Step 3: Get preferred mode
            preferred_mode = self.get_preferred_mode()
            print(f"Detected preferred mode: {preferred_mode}")
            
            # Step 4: Run Addition App
            if not self.run_addition_app(preferred_mode):
                print("Error: Failed to complete Addition App")
                return
            
            # Step 5: Run Subtraction App
            if not self.run_subtraction_app(preferred_mode):
                print("Error: Failed to complete Subtraction App")
                return
            
            print("\nLearning session completed successfully!")
            print("Thank you for using the Autism Learning App!")
            
        except Exception as e:
            print(f"Error: An error occurred: {e}")
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    launcher = AppLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
