#!/usr/bin/env python3
"""
Screenshot Monitor for Claude Code
Monitors screenshot directories and automatically copies paths to clipboard
"""

import os
import time
import subprocess
import glob
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_screenshot = None

    def on_created(self, event):
        if event.is_directory:
            return

        # Check if it's a screenshot file
        filename = os.path.basename(event.src_path)
        if self.is_screenshot_file(filename):
            print(f"New screenshot detected: {event.src_path}")
            self.copy_to_clipboard(event.src_path)
            self.show_notification(event.src_path)

    def is_screenshot_file(self, filename):
        """Check if file is likely a screenshot"""
        screenshot_patterns = [
            "Screenshot",
            "Screen Shot",
            "CleanShot",
            "SCR_",
            "screenshot",
        ]

        extensions = [".png", ".jpg", ".jpeg"]

        return any(pattern in filename for pattern in screenshot_patterns) and any(
            filename.lower().endswith(ext) for ext in extensions
        )

    def copy_to_clipboard(self, filepath):
        """Copy file path to clipboard"""
        try:
            # Use pbcopy on macOS
            subprocess.run(["pbcopy"], input=filepath.encode(), check=True)
            print(f"Copied to clipboard: {filepath}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to copy to clipboard: {e}")

    def show_notification(self, filepath):
        """Show macOS notification"""
        filename = os.path.basename(filepath)
        message = f"Screenshot path copied: {filename}"

        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "Claude Code Screenshot"',
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            print("Could not show notification")


def monitor_screenshots():
    """Monitor common screenshot directories"""
    # Common screenshot locations on macOS
    directories_to_monitor = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        "/tmp",
        "/var/folders",  # Temporary screenshot location
    ]

    # Add any additional directories that exist
    temp_screenshot_dirs = glob.glob(
        "/var/folders/*/T/TemporaryItems/NSIRD_screencaptureui_*"
    )
    directories_to_monitor.extend(temp_screenshot_dirs)

    event_handler = ScreenshotHandler()
    observer = Observer()

    for directory in directories_to_monitor:
        if os.path.exists(directory):
            observer.schedule(event_handler, directory, recursive=True)
            print(f"Monitoring: {directory}")

    observer.start()
    print("Screenshot monitor started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping screenshot monitor...")

    observer.join()


if __name__ == "__main__":
    # Install requirements if needed
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("Installing required package: watchdog")
        subprocess.run(["pip", "install", "watchdog"], check=True)
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

    monitor_screenshots()
