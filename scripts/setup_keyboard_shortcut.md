# Setting Up Keyboard Shortcut for Screenshot-to-Claude

## Method 1: Automator Quick Action (Recommended)

1. **Open Automator**
   - Press `Cmd+Space` and type "Automator"
   - Click "New Document"
   - Select "Quick Action"

2. **Configure the Quick Action**
   - Set "Workflow receives" to "no input"
   - Set "in" to "any application"

3. **Add Run Shell Script Action**
   - In the left sidebar, search for "Run Shell Script"
   - Drag it to the workflow area
   - Set Shell to `/bin/zsh`
   - Paste this code:
   ```bash
   /Users/macbookair/dev/kitchentory/scripts/latest_screenshot.sh
   ```

4. **Save the Quick Action**
   - Press `Cmd+S`
   - Name it "Screenshot to Claude"

5. **Assign Keyboard Shortcut**
   - Open System Preferences → Keyboard → Shortcuts
   - Click "Services" in the left sidebar
   - Find "Screenshot to Claude" under "General"
   - Click "add shortcut" and press your desired key combo (e.g., `Cmd+Shift+V`)

## Method 2: Using Raycast (If you have it)

1. Create a new script command in Raycast
2. Set the script to run the screenshot command
3. Assign a keyboard shortcut

## Method 3: Using Alfred (If you have it)

1. Create a new workflow
2. Add a hotkey trigger
3. Connect it to a script action that runs the command

## Method 4: System-wide Shell Command

Create a simple AppleScript application:

1. Open Script Editor
2. Paste the AppleScript code (see below)
3. Save as Application
4. Use System Preferences to assign shortcut

## Recommended Key Combinations

- `Cmd+Shift+V` - Paste screenshot path
- `Cmd+Option+S` - Screenshot to Claude  
- `Ctrl+Shift+C` - Copy screenshot path
- `F13` or `F14` - If you have function keys available

Choose a combination that doesn't conflict with existing shortcuts!