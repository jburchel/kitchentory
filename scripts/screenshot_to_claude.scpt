-- AppleScript for Screenshot to Claude Keyboard Shortcut
-- Save this as an Application and assign a keyboard shortcut

tell application "Terminal"
    activate
    do script "/Users/macbookair/dev/kitchentory/scripts/latest_screenshot.sh"
end tell