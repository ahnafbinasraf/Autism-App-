#!/usr/bin/env python3
"""
Autism Learning WebApp Launcher
Launches the Flask webapp version of AutismApp with all original logic preserved
"""

import os
import sys
import webbrowser
import threading
import time
import subprocess
import csv

try:
	import requests
except Exception:
	requests = None

def open_browser():
	"""Open the browser after a short delay to ensure the server has started"""
	time.sleep(2.0)  # Wait for server to start
	webbrowser.open('http://localhost:5002')


def _wait_for_server(port: int, timeout: int = 60) -> bool:
	"""Wait until an HTTP server responds on the given port."""
	if requests is None:
		# Fallback: sleep a few seconds if requests isn't available
		time.sleep(3)
		return True
	start = time.time()
	url = f"http://localhost:{port}"
	while time.time() - start < timeout:
		try:
			resp = requests.get(url, timeout=2)
			if resp.status_code < 500:
				return True
		except Exception:
			time.sleep(1)
	return False


def _webapp_completed() -> bool:
	"""Check if the webapp has completed all three modes by examining learner logs."""
	# Look for learner_log*.csv files and check if they contain all three modes
	for filename in os.listdir('.'):
		if filename.startswith('learner_log') and filename.endswith('.csv'):
			try:
				with open(filename, 'r', encoding='utf-8') as f:
					reader = csv.DictReader(f)
					modes_found = set()
					for row in reader:
						if 'mode' in row and row['mode']:
							modes_found.add(row['mode'])
					# Check if all three modes are present
					if len(modes_found) >= 3 and 'visual' in modes_found and 'auditory' in modes_found and 'kinesthetic' in modes_found:
						return True
			except Exception:
				continue
	return False

def main():
	print("Autism Learning WebApp")
	print("========================")
	print("Starting the web application...")
	print("Features included:")
	print("   • Real-time emotion tracking")
	print("   • Frustration analysis and mode switching")
	print("   • Visual learning mode")
	print("   • Auditory learning mode") 
	print("   • Kinesthetic learning mode")
	print("   • CSV data logging")
	print("   • Accessible, learner-friendly UI")
	print()
	processes = []
	
	# Change to the current directory to ensure proper imports
	os.chdir(os.path.dirname(os.path.abspath(__file__)))
	try:
		# Start Learning WebApp in a background thread so we can orchestrate the rest
		print("Loading webapp modules...")
		import learning_webapp as autism_webapp
		print("WebApp loaded successfully.")
		print("Starting Flask server on http://localhost:5002")
		server_thread = threading.Thread(target=lambda: autism_webapp.app.run(debug=False, host='0.0.0.0', port=5002, use_reloader=False))
		server_thread.daemon = True
		server_thread.start()
		
		# Open browser
		print("Browser will open automatically...")
		browser_thread = threading.Thread(target=open_browser)
		browser_thread.daemon = True
		browser_thread.start()
		
		# Wait for server readiness (best-effort)
		_wait_for_server(5002, timeout=60)
		print("Learning WebApp is running on http://localhost:5002")
		print("Complete the webapp session in your browser. This script will proceed automatically when data is available.")
		print()
		
		# Monitor for webapp completion, then run analyzer
		print("Waiting for webapp completion (all three modes: visual, auditory, kinesthetic)...")
		deadline = time.time() + 3600  # wait up to 1 hour passively
		while time.time() < deadline:
			if _webapp_completed():
				break
			time.sleep(5)
		
		print("Running Preferred Mode Analyzer...")
		try:
			proc = subprocess.run([sys.executable, "preferred_mode_analyzer.py"], check=False, capture_output=True, text=True)
			if proc.returncode == 0:
				print("Preferred Mode Analysis completed.")
			else:
				print("Preferred Mode Analyzer reported non-zero exit code.")
				if proc.stderr:
					print(proc.stderr.strip())
		except Exception as e:
			print(f"Error running Preferred Mode Analyzer: {e}")
		
		# Start Addition App (gated)
		print()
		print("Starting Addition Practice app on http://localhost:5001 ...")
		try:
			p_add = subprocess.Popen([sys.executable, "run_addition_app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			processes.append(p_add)
			# Give it a moment and open browser
			threading.Thread(target=lambda: (time.sleep(3), webbrowser.open('http://localhost:5001')), daemon=True).start()
			print("\nComplete the Addition practice in your browser.")
			print("When finished, return here and press Enter to continue to Subtraction...")
			try:
				input()
			except Exception:
				pass
			# Attempt to stop the Addition server before starting Subtraction
			try:
				if p_add.poll() is None:
					p_add.terminate()
					# Give it a moment to exit
					for _ in range(10):
						if p_add.poll() is not None:
							break
						time.sleep(0.3)
					if p_add.poll() is None:
						p_add.kill()
			except Exception:
				pass
		except Exception as e:
			print(f"Error starting Addition App: {e}")
		
		# Start Subtraction App after Addition is completed
		print("Starting Subtraction Practice app on http://localhost:5003 ...")
		try:
			p_sub = subprocess.Popen([sys.executable, "run_subtraction_app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			processes.append(p_sub)
			threading.Thread(target=lambda: (time.sleep(3), webbrowser.open('http://localhost:5003')), daemon=True).start()
		except Exception as e:
			print(f"Error starting Subtraction App: {e}")
		
		print()
		print("All components have been started.")
		print("You can interact with the apps in your browser:")
		print(" - Learning WebApp:      http://localhost:5002")
		print(" - Addition Practice:    http://localhost:5001")
		print(" - Subtraction Practice: http://localhost:5003")
		print()
		print("Press Ctrl+C in this terminal to stop the orchestrator. Individual apps can be closed by closing the terminal or stopping the processes.")
		
		# Keep the orchestrator alive while child processes run
		while True:
			alive = any(p.poll() is None for p in processes)
			if not alive:
				break
			time.sleep(5)
		
	except Exception as e:
		print(f"Error starting the webapp: {e}")
		print()
		print("Troubleshooting tips:")
		print("   1. Make sure you have installed the requirements:")
		print("      pip install -r requirements.txt")
		print("   2. Check that your camera is not being used by another app")
		print("   3. Make sure Python has camera permissions")
		print("   4. Try running: python learning_webapp.py directly")
		print()
		sys.exit(1)

if __name__ == "__main__":
	main()
