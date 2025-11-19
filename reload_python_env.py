#!/usr/bin/env python3
"""
Script to reload Python environment and verify interpreter path
"""

import sys
import os

print("=== Python Environment Information ===")
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print(f"Python Path: {sys.path[0]}")
print()

print("=== Site Packages Location ===")
for path in sys.path:
    if 'site-packages' in path:
        print(f"Site packages: {path}")
        if os.path.exists(path):
            print(f"  Directory exists")
            # List some packages
            try:
                packages = os.listdir(path)
                pandas_exists = any('pandas' in pkg for pkg in packages)
                numpy_exists = any('numpy' in pkg for pkg in packages)
                matplotlib_exists = any('matplotlib' in pkg for pkg in packages)
                seaborn_exists = any('seaborn' in pkg for pkg in packages)
                scipy_exists = any('scipy' in pkg for pkg in packages)
                
                print(f"  pandas present: {pandas_exists}")
                print(f"  numpy present: {numpy_exists}")
                print(f"  matplotlib present: {matplotlib_exists}")
                print(f"  seaborn present: {seaborn_exists}")
                print(f"  scipy present: {scipy_exists}")
            except PermissionError:
                print("  Error: Permission denied to list packages")
        else:
            print(f"  Error: Directory does not exist")
print()

print("=== Import Test ===")
try:
    import pandas as pd
    print(f"pandas {pd.__version__}")
except ImportError as e:
    print(f"Error: pandas: {e}")

try:
    import numpy as np
    print(f"numpy {np.__version__}")
except ImportError as e:
    print(f"Error: numpy: {e}")

try:
    import matplotlib
    import matplotlib.pyplot as plt
    version = getattr(matplotlib, '__version__', 'unknown')
    print(f"matplotlib {version}")
except ImportError as e:
    print(f"Error: matplotlib: {e}")

try:
    import seaborn as sns
    print(f"seaborn {sns.__version__}")
except ImportError as e:
    print(f"Error: seaborn: {e}")

try:
    from scipy import stats
    import scipy
    print(f"scipy {scipy.__version__}")
except ImportError as e:
    print(f"Error: scipy: {e}")

print()
print("=== Instructions ===")
print("If you see import errors above, try:")
print("1. Restart your IDE/editor")
print("2. Select Python interpreter: /Users/ahnafbinasraf/.pyenv/versions/3.10.13/bin/python")
print("3. Reload the window (Cmd+Shift+P → 'Developer: Reload Window')")
