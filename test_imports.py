#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print()

# Test basic imports
print("Testing basic imports...")
try:
    import argparse
    print("argparse OK")
except ImportError as e:
    print(f"Error: argparse: {e}")

try:
    import os
    print("os OK")
except ImportError as e:
    print(f"Error: os: {e}")

try:
    import logging
    print("logging OK")
except ImportError as e:
    print(f"Error: logging: {e}")

try:
    from datetime import datetime
    print("datetime OK")
except ImportError as e:
    print(f"Error: datetime: {e}")

print()

# Test scientific imports
print("Testing scientific imports...")
try:
    import pandas as pd
    print(f"pandas OK {pd.__version__}")
except ImportError as e:
    print(f"Error: pandas: {e}")

try:
    import numpy as np
    print(f"numpy OK {np.__version__}")
except ImportError as e:
    print(f"Error: numpy: {e}")

try:
    import matplotlib.pyplot as plt
    print(f"matplotlib OK {plt.matplotlib.__version__}")
except ImportError as e:
    print(f"Error: matplotlib: {e}")

try:
    import seaborn as sns
    print(f"seaborn OK {sns.__version__}")
except ImportError as e:
    print(f"Error: seaborn: {e}")

try:
    from scipy import stats
    import scipy
    print(f"scipy OK {scipy.__version__}")
except ImportError as e:
    print(f"Error: scipy: {e}")

try:
    import flask
    print(f"flask OK {flask.__version__}")
except ImportError as e:
    print(f"Error: flask: {e}")

print()
print("Import test completed!")





