import sys
import os
import platform

print("Python version:")
print(sys.version)

print("\nPython executable:")
print(sys.executable)

print("\nEnvironment prefix:")
print(sys.prefix)

print("\nBase prefix:")
print(sys.base_prefix)

print("\nPlatform:")
print(platform.platform())

# Cek apakah sedang di virtual environment
is_venv = sys.prefix != sys.base_prefix
print("\nIs virtual environment?")
print(is_venv)

# Cek nama environment dari environment variable
print("\nConda environment:")
print(os.environ.get("CONDA_DEFAULT_ENV"))

print("\nVirtualenv:")
print(os.environ.get("VIRTUAL_ENV"))