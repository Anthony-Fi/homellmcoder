#!/usr/bin/env python3
"""
Build script for HomeLLMCoder v0.02
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list, cwd: str = None) -> bool:
    """Run a shell command and return True if successful."""
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        return False

def clean_build():
    """Clean up build artifacts."""
    print("Cleaning build artifacts...")
    for path in ['build', 'dist', 'HomeLLMCoder-v0.02.spec', 'HomeLLMCoder-v0.02']:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

def build_windows():
    """Build Windows executable using PyInstaller."""
    print("Building Windows executable...")
    
    # Install required packages
    if not run_command([sys.executable, '-m', 'pip', 'install', 'pyinstaller', 'pywin32']):
        return False
    
    # Run PyInstaller
    if not run_command([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', 'HomeLLMCoder-v0.02.spec']):
        return False
    
    # Create a zip archive of the distribution
    print("Creating distribution archive...")
    shutil.make_archive(f'HomeLLMCoder-v0.02-windows', 'zip', 'dist')
    
    return True

def main():
    """Main build function."""
    print("Starting build process for HomeLLMCoder v0.02")
    
    # Clean previous builds
    clean_build()
    
    # Build for current platform
    if sys.platform == 'win32':
        success = build_windows()
    else:
        print(f"Unsupported platform: {sys.platform}")
        success = False
    
    if success:
        print("\nBuild completed successfully!")
        print(f"Distributable package: HomeLLMCoder-v0.02-windows.zip")
        return 0
    else:
        print("\nBuild failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
