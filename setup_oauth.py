#!/usr/bin/env python3
"""
Quick setup script for TestTrack Pro OAuth
Run this to set up environment variables for Google and GitHub OAuth
"""

import os
import sys
from pathlib import Path

def setup_oauth():
    print("\n" + "="*60)
    print("🔐 TestTrack Pro - OAuth Configuration Setup")
    print("="*60 + "\n")
    
    backend_dir = Path(__file__).parent / "backend"
    env_file = backend_dir / ".env"
    
    # Check if .env exists
    if env_file.exists():
        print(f"✓ .env file found at {env_file}")
    else:
        print(f"⚠ .env file not found. Creating from .env.example...")
        env_example = backend_dir / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print(f"✓ Created .env from .env.example")
        else:
            print("❌ .env.example not found!")
            return False
    
    print("\n" + "-"*60)
    print("STEP 1: Google OAuth Setup")
    print("-"*60)
    print("""
    1. Go to: https://console.cloud.google.com/
    2. Create a new project named 'TestTrack Pro'
    3. Enable Google+ API
    4. Go to Credentials and create OAuth 2.0 Client ID (Web)
    5. Add Authorized Redirect URI: http://localhost:3000/auth/oauth-callback
    6. Copy your Client ID and Secret
    """)
    
    google_id = input("Paste your Google Client ID: ").strip()
    google_secret = input("Paste your Google Client Secret: ").strip()
    
    print("\n" + "-"*60)
    print("STEP 2: GitHub OAuth Setup")
    print("-"*60)
    print("""
    1. Go to: https://github.com/settings/developers
    2. Click 'OAuth Apps' → 'New OAuth App'
    3. Fill in:
       - Application name: TestTrack Pro
       - Homepage URL: http://localhost:3000
       - Authorization callback: http://localhost:3000/auth/oauth-callback
    4. Copy your Client ID and Secret
    """)
    
    github_id = input("Paste your GitHub Client ID: ").strip()
    github_secret = input("Paste your GitHub Client Secret: ").strip()
    
    # Update .env file
    print("\n" + "-"*60)
    print("Updating .env file...")
    print("-"*60)
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Update Google OAuth
    content = content.replace(
        "GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com",
        f"GOOGLE_CLIENT_ID={google_id}"
    )
    content = content.replace(
        "GOOGLE_CLIENT_SECRET=your_google_client_secret_here",
        f"GOOGLE_CLIENT_SECRET={google_secret}"
    )
    
    # Update GitHub OAuth
    content = content.replace(
        "GITHUB_CLIENT_ID=your_github_client_id_here",
        f"GITHUB_CLIENT_ID={github_id}"
    )
    content = content.replace(
        "GITHUB_CLIENT_SECRET=your_github_client_secret_here",
        f"GITHUB_CLIENT_SECRET={github_secret}"
    )
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated {env_file}")
    
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    print("""
Next steps:
1. Restart the backend server
2. Go to http://localhost:3000/auth/login.html
3. Click 'Google' or 'GitHub' button to test
4. You should be redirected and logged in automatically

Troubleshooting:
- If you get 'Redirect URI mismatch': Check your callback URL in Google/GitHub settings
- If buttons don't work: Clear browser cache and restart backend
- For more info: See OAUTH_SETUP_GUIDE.md
    """)
    
    return True

if __name__ == "__main__":
    try:
        success = setup_oauth()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
