# PhoneFlash — Installation Guide

## Overview

PhoneFlash consists of two parts:
- **Android app** — runs on your phone as a file server
- **PC app** — connects to the phone via USB and manages files

Both parts are required for the system to work.

---

## Part 1: Android App (Phone)

### Requirements
- Android 7.0+ (API 24+)
- USB cable (data cable, not charge-only)
- USB Debugging enabled

### Step 1: Enable Developer Options
1. Open **Settings** on your phone
2. Go to **About Phone**
3. Tap **Build Number** 7 times
4. You'll see "You are now a developer!"

### Step 2: Enable USB Debugging
1. Open **Settings** → **Developer Options**
2. Enable **USB Debugging**
3. When you connect the phone to PC, a dialog will appear — tap **Allow**

### Step 3: Install PhoneFlash Android App
1. Download `PhoneFlash.apk` from [Releases](https://github.com/ren10-14/PhoneFlash/releases)
2. Transfer it to your phone and install
3. If prompted, allow installation from unknown sources

### Step 4: Grant Permissions
When you first open the app:
1. **All Files Access** — Required. The app will show a dialog. Tap "Open Settings" and enable "Allow access to manage all files"
2. **Notifications** — Required for foreground service. Tap "Allow"

### Step 5: Start the Server
1. Open PhoneFlash on your phone
2. Tap **Start Server**
3. You should see: "Server running on port 8888"
4. Keep the app open (it runs as a foreground service)

### Verify
Check the system status on the main screen:
- ✅ File access: Granted
- ✅ Notifications: Granted
- ✅ Server: Running

---

## Part 2: PC App (Windows)

### Requirements
- Windows 10 / 11
- USB cable connected to phone

### Installation
1. Download `PhoneFlash-Windows.zip` from [Releases](https://github.com/ren10-14/PhoneFlash/releases)
2. Extract the ZIP to any folder (e.g. Desktop, Documents, etc.)
3. Run `PhoneFlash.exe`

That's it. No installation, no setup. Everything is included.

---

## Connecting Phone to PC

### Step 1: Physical Connection
1. Connect your phone to PC with a USB cable
2. On your phone, select **File Transfer / MTP** mode (not charging only)
3. If a "Allow USB debugging?" dialog appears — tap **Allow** and check "Always allow"

### Step 2: Start Server on Phone
1. Open PhoneFlash app on phone
2. Tap **Start Server**
3. Confirm it says "Server running on port 8888"

### Step 3: Connect from PC
1. Open `PhoneFlash.exe` on PC
2. Click **Connect**
3. The app will automatically:
   - Find your device via ADB
   - Set up port forwarding
   - Connect to the server
   - Show your phone's storage

### Successful Connection
You should see:
- 📱 **Device detected** (green)
- 🖥 **Server connected** (green)
- Phone storage listed in the file browser

---

## Troubleshooting

### "No device found"
- Check USB cable is connected
- Enable USB Debugging in Developer Options
- Try a different USB port
- Install USB drivers for your phone model
- On the phone, change USB mode to "File Transfer"

### "Device detected" but "Server not running"
- Open PhoneFlash app on phone
- Make sure server is started (tap "Start Server")
- Check that "Server running on port 8888" is displayed

### "Connection refused"
- The phone's server is not running
- Restart the server on the phone (Stop → Start)

### Empty file list (0 files)
- The app doesn't have "All Files Access" permission
- Go to phone Settings → Apps → PhoneFlash → Permissions → Files and media → Allow management of all files
- Restart the server after granting permission

---

## How to Use

| Feature | How |
|---|---|
| Browse files | Double-click folders to navigate |
| Download file | Select file → click Download |
| Download multiple | Hold Ctrl + click files → click Download |
| Upload file | Open a folder → click Upload |
| Image preview | Click on an image file |
| Play video | Select video → click Play Media (or double-click) |
| Play audio | Select audio → click Play Media (or double-click) |
| Go back | Click Back |
| Go to root | Click Home |

---

## Uninstall

### PC
Delete the PhoneFlash folder. No registry entries are created.

### Android
Uninstall PhoneFlash like any other app.
