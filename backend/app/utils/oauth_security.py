from cryptography.fernet import Fernet
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

class OAuthTokenEncryption:
    """Encrypt and decrypt OAuth tokens for secure storage"""
    
    _key = None
    
    @classmethod
    def _get_key(cls):
        """Get or create encryption key"""
        if cls._key is None:
            # Try to get from environment
            key_str = os.getenv("ENCRYPTION_KEY")
            if key_str:
                cls._key = key_str.encode()
            else:
                # Generate new key in development
                cls._key = Fernet.generate_key()
                print(f"⚠️ Generated new encryption key. Add this to .env: ENCRYPTION_KEY={cls._key.decode()}")
        return cls._key
    
    @classmethod
    def encrypt_token(cls, token: str) -> str:
        """Encrypt an OAuth token"""
        try:
            f = Fernet(cls._get_key())
            encrypted = f.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            raise Exception(f"Token encryption failed: {str(e)}")
    
    @classmethod
    def decrypt_token(cls, encrypted_token: str) -> str:
        """Decrypt an OAuth token"""
        try:
            f = Fernet(cls._get_key())
            decrypted = f.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            raise Exception(f"Token decryption failed: {str(e)}")

class OAuthSecurityValidator:
    """Validate OAuth security parameters"""
    
    @staticmethod
    def validate_redirect_uri(redirect_uri: str, allowed_uris: list = None) -> bool:
        """Validate redirect URI against whitelist"""
        if allowed_uris is None:
            allowed_uris = [
                "http://localhost:3000",
                "http://localhost:3000/auth/oauth-callback",
                os.getenv("FRONTEND_URL", "http://localhost:3000")
            ]
        
        return any(redirect_uri.startswith(uri) for uri in allowed_uris)
    
    @staticmethod
    def validate_state_format(state: str) -> bool:
        """Validate state token format"""
        # State should be a valid URL-safe base64 string or similar
        if not state or len(state) < 30:
            return False
        
        # Check if it's URL-safe
        try:
            base64.urlsafe_b64decode(state + "==")
            return True
        except:
            return len(state) >= 32  # Fallback to length check
    
    @staticmethod
    def validate_pkce_code_challenge(code_challenge: str) -> bool:
        """Validate PKCE code challenge format"""
        if not code_challenge or len(code_challenge) < 43 or len(code_challenge) > 128:
            return False
        
        # Check for URL-safe characters only
        import string
        valid_chars = set(string.ascii_letters + string.digits + '-._~')
        return all(c in valid_chars for c in code_challenge)

class OAuthRateLimiter:
    """Rate limit OAuth callback attempts"""
    
    _attempts = {}
    _limit_window = 300  # 5 minutes
    _max_attempts = 10
    
    @classmethod
    def check_rate_limit(cls, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        key = f"oauth_callback_{user_id}"
        
        if key not in cls._attempts:
            cls._attempts[key] = {"count": 0, "first_attempt": None}
        
        attempt_data = cls._attempts[key]
        now = __import__('datetime').datetime.utcnow()
        
        if attempt_data["first_attempt"] is None:
            attempt_data["first_attempt"] = now
            attempt_data["count"] = 1
            return True
        
        # Reset if window expired
        if (now - attempt_data["first_attempt"]).total_seconds() > cls._limit_window:
            attempt_data["first_attempt"] = now
            attempt_data["count"] = 1
            return True
        
        # Check if exceeded limit
        if attempt_data["count"] >= cls._max_attempts:
            return False
        
        attempt_data["count"] += 1
        return True
    
    @classmethod
    def get_remaining_attempts(cls, user_id: int) -> int:
        """Get remaining attempts for user"""
        key = f"oauth_callback_{user_id}"
        
        if key not in cls._attempts:
            return cls._max_attempts
        
        return max(0, cls._max_attempts - cls._attempts[key]["count"])
