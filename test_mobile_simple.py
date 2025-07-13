#!/usr/bin/env python3
"""
Simple mobile testing helper - opens browser with mobile viewport
"""
import webbrowser
import time


def test_mobile():
    print("🚀 Opening mobile-friendly browser...")

    # Open browser with mobile viewport simulation
    url = "http://localhost:8000"

    print(f"📱 Opening: {url}")
    print("💡 Instructions:")
    print("   1. Press F12 to open DevTools")
    print("   2. Click the mobile device icon (📱)")
    print("   3. Select 'iPhone 12 Pro' or 'Galaxy S20'")
    print("   4. Test your app!")

    webbrowser.open(url)


if __name__ == "__main__":
    test_mobile()
