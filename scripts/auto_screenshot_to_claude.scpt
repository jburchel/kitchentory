-- AppleScript to automatically send screenshots to Claude Code
-- This script monitors for new screenshots and copies the path to clipboard

on run
    -- Get the most recent screenshot from Desktop
    set desktopPath to (path to desktop as string)
    tell application "Finder"
        set allFiles to every file of desktop whose name starts with "Screenshot"
        if (count of allFiles) > 0 then
            set newestFile to item 1 of allFiles
            set newestDate to creation date of newestFile
            
            repeat with currentFile in allFiles
                if creation date of currentFile > newestDate then
                    set newestFile to currentFile
                    set newestDate to creation date of currentFile
                end if
            end repeat
            
            -- Get the full path
            set filePath to (newestFile as string)
            set posixPath to POSIX path of filePath
            
            -- Copy path to clipboard for easy pasting
            set the clipboard to posixPath
            
            -- Show notification
            display notification "Screenshot path copied to clipboard: " & posixPath with title "Claude Code Screenshot Helper"
        else
            display notification "No screenshots found on desktop" with title "Claude Code Screenshot Helper"
        end if
    end tell
end run