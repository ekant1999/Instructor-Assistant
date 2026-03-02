# Port Conflict Fix

## Issue
Port 5000 was blocked by Apple AirPlay service (AirTunes), causing 403 Forbidden errors.

## Solution
Changed the Vite dev server port from 5000 to 5173 (Vite's default port).

## Updated Configuration

### package.json
- `dev:client` now uses port 5173 instead of 5000

## Access the Application

The application should now be accessible at:
- **http://localhost:5173** (Vite dev server)
- **http://localhost:8010** (FastAPI server - if running)

## Alternative Solutions

If you still encounter port conflicts:

1. **Disable AirPlay Receiver** (macOS):
   - System Settings → General → AirDrop & Handoff
   - Turn off "AirPlay Receiver"

2. **Use a different port**:
   - Edit `package.json` and change the port in `dev:client` script
   - Or set `PORT` environment variable

3. **Kill AirPlay process** (not recommended):
   ```bash
   sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.AirPlayXPCHelper.plist
   ```

## Testing

After the fix, test the application at:
- http://localhost:5173/library
- http://localhost:5173/notes
- http://localhost:5173/questions
- http://localhost:5173/rag
