import pytest
from httpx import AsyncClient
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models.user import User, UserStatusEnum, RoleEnum, OAuthProvider
from backend.app.utils.security import hash_password
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
import uuid

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_oauth.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# ============ OAuth Tests ============

class TestOAuthFlow:
    """Test complete OAuth flows"""
    
    @pytest.mark.asyncio
    async def test_google_authorize_url_generation(self):
        """Test Google authorization URL generation"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/oauth/google/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert data["provider"] == "google"
            assert "client_id" in data["authorization_url"]
            assert data["state"]  # State should not be empty
    
    @pytest.mark.asyncio
    async def test_github_authorize_url_generation(self):
        """Test GitHub authorization URL generation"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/oauth/github/authorize?redirect_uri=http://localhost:3000/auth/oauth-callback"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "authorization_url" in data
            assert "state" in data
            assert data["provider"] == "github"
            assert "client_id" in data["authorization_url"]
    
    @pytest.mark.asyncio
    async def test_invalid_state_validation(self):
        """Test that invalid state tokens are rejected"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/oauth/google/callback",
                json={
                    "code": "invalid_code",
                    "state": "invalid_state",
                    "redirect_uri": "http://localhost:3000/auth/oauth-callback"
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "state" in data["detail"].lower()

class TestOAuthLinker:
    """Test OAuth account linking"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        db = TestingSessionLocal()
        user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password=hash_password("Test123!@#"),
            is_active=True,
            is_verified=True,
            verified_at=datetime.utcnow(),
            status=UserStatusEnum.ACTIVE,
            role=RoleEnum.TESTER
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        yield user
        
        db.delete(user)
        db.commit()
        db.close()
    
    @pytest.mark.asyncio
    async def test_link_oauth_account_authenticated(self, test_user):
        """Test linking OAuth account to authenticated user"""
        from backend.app.utils.security import create_access_token
        
        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email, "role": "tester"}
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/oauth/link",
                json={
                    "provider": "google",
                    "provider_id": "google_12345",
                    "email": "test@gmail.com"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "linked successfully" in data["message"].lower()
            assert data["provider"] == "google"
    
    @pytest.mark.asyncio
    async def test_unlink_oauth_account(self, test_user):
        """Test unlinking OAuth account"""
        from backend.app.utils.security import create_access_token
        
        # First link an account
        db = TestingSessionLocal()
        oauth_provider = OAuthProvider(
            user_id=test_user.id,
            provider="github",
            provider_id="github_12345",
            email="test@github.com"
        )
        db.add(oauth_provider)
        db.commit()
        db.close()
        
        # Now unlink it
        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email, "role": "tester"}
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/oauth/unlink",
                json={"provider": "github"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "unlinked successfully" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_linked_accounts(self, test_user):
        """Test retrieving linked accounts"""
        from backend.app.utils.security import create_access_token
        
        # Link multiple accounts
        db = TestingSessionLocal()
        oauth_providers = [
            OAuthProvider(
                user_id=test_user.id,
                provider="google",
                provider_id="google_12345",
                email="test@gmail.com"
            ),
            OAuthProvider(
                user_id=test_user.id,
                provider="github",
                provider_id="github_54321",
                email="test@github.com"
            )
        ]
        db.add_all(oauth_providers)
        db.commit()
        db.close()
        
        # Retrieve linked accounts
        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email, "role": "tester"}
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/oauth/linked-accounts",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["linked_accounts"]) == 2
            providers = [acc["provider"] for acc in data["linked_accounts"]]
            assert "google" in providers
            assert "github" in providers

class TestOAuthSecurity:
    """Test OAuth security features"""
    
    def test_oauth_state_validation(self):
        """Test OAuth state token validation"""
        from backend.app.utils.oauth import OAuthStateManager
        
        state = OAuthStateManager.create_state("google", "http://localhost:3000/callback")
        
        # Should be valid immediately after creation
        assert OAuthStateManager.validate_state(state, "google")
        
        # Should be invalid with wrong provider
        assert not OAuthStateManager.validate_state(state, "github")
        
        # Should be invalid with wrong state
        assert not OAuthStateManager.validate_state("invalid_state", "google")
    
    def test_oauth_state_cleanup(self):
        """Test OAuth state token cleanup"""
        from backend.app.utils.oauth import OAuthStateManager
        
        state = OAuthStateManager.create_state("google", "http://localhost:3000/callback")
        
        # State should be valid
        assert OAuthStateManager.validate_state(state, "google")
        
        # Cleanup state
        OAuthStateManager.cleanup_state(state)
        
        # State should be invalid after cleanup
        assert not OAuthStateManager.validate_state(state, "google")
    
    def test_oauth_redirect_uri_validation(self):
        """Test OAuth redirect URI validation"""
        from backend.app.utils.oauth_security import OAuthSecurityValidator
        
        valid_uris = [
            "http://localhost:3000",
            "http://localhost:3000/auth/oauth-callback"
        ]
        
        # Valid URIs
        assert OAuthSecurityValidator.validate_redirect_uri(
            "http://localhost:3000/auth/oauth-callback",
            valid_uris
        )
        
        # Invalid URI
        assert not OAuthSecurityValidator.validate_redirect_uri(
            "http://malicious.com/callback",
            valid_uris
        )

class TestOAuthErrors:
    """Test OAuth error handling"""
    
    @pytest.mark.asyncio
    async def test_missing_oauth_parameters(self):
        """Test error when OAuth parameters are missing"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/oauth/google/callback",
                json={
                    "code": "",
                    "state": ""
                }
            )
            
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_duplicate_oauth_provider(self):
        """Test error when OAuth provider is already linked to another account"""
        db = TestingSessionLocal()
        
        # Create two users
        user1 = User(
            email="user1@example.com",
            username="user1",
            full_name="User 1",
            hashed_password=hash_password("Test123!@#"),
            is_active=True,
            is_verified=True,
            verified_at=datetime.utcnow(),
            status=UserStatusEnum.ACTIVE,
            role=RoleEnum.TESTER
        )
        user2 = User(
            email="user2@example.com",
            username="user2",
            full_name="User 2",
            hashed_password=hash_password("Test123!@#"),
            is_active=True,
            is_verified=True,
            verified_at=datetime.utcnow(),
            status=UserStatusEnum.ACTIVE,
            role=RoleEnum.TESTER
        )
        
        db.add_all([user1, user2])
        db.commit()
        
        # Link OAuth to user1
        oauth_provider = OAuthProvider(
            user_id=user1.id,
            provider="google",
            provider_id="google_12345",
            email="user1@gmail.com"
        )
        db.add(oauth_provider)
        db.commit()
        
        # Try to link same OAuth to user2 (should fail)
        from backend.app.utils.security import create_access_token
        
        token = create_access_token(
            data={"sub": str(user2.id), "email": user2.email, "role": "tester"}
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/oauth/link",
                json={
                    "provider": "google",
                    "provider_id": "google_12345",
                    "email": "user1@gmail.com"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 409  # Conflict
        
        # Cleanup
        db.delete(user1)
        db.delete(user2)
        db.commit()
        db.close()

# ============ Run Tests ============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
