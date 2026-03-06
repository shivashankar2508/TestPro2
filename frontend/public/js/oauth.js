// OAuth Integration - Google and GitHub login

const API_URL = 'http://localhost:8001/api';
const FRONTEND_URL = 'http://localhost:3000';

// ============ OAuth Button Handlers ============

// Google OAuth
document.querySelectorAll('.google-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await initiateGoogleOAuth();
    });
});

// GitHub OAuth
document.querySelectorAll('.github-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.preventDefault();
        await initiateGitHubOAuth();
    });
});

// ============ Google OAuth ============

async function initiateGoogleOAuth() {
    try {
        // Get authorization URL
        const response = await fetch(`${API_URL}/auth/oauth/google/authorize?redirect_uri=${encodeURIComponent(FRONTEND_URL + '/auth/oauth-callback')}`);
        const data = await response.json();

        if (data.authorization_url) {
            // Redirect to Google
            window.location.href = data.authorization_url;
        } else {
            alert('Failed to initiate Google login');
        }
    } catch (error) {
        console.error('Google OAuth error:', error);
        alert('Failed to initiate Google login. Please try again.');
    }
}

// ============ GitHub OAuth ============

async function initiateGitHubOAuth() {
    try {
        // Get authorization URL
        const response = await fetch(`${API_URL}/auth/oauth/github/authorize?redirect_uri=${encodeURIComponent(FRONTEND_URL + '/auth/oauth-callback')}`);
        const data = await response.json();

        if (data.authorization_url) {
            // Redirect to GitHub
            window.location.href = data.authorization_url;
        } else {
            alert('Failed to initiate GitHub login');
        }
    } catch (error) {
        console.error('GitHub OAuth error:', error);
        alert('Failed to initiate GitHub login. Please try again.');
    }
}

// ============ OAuth Callback Handler ============

async function handleOAuthCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const provider = sessionStorage.getItem('oauth_provider');

    if (!code || !state) {
        console.error('Missing OAuth parameters');
        window.location.href = '/auth/login.html?error=invalid_callback';
        return;
    }

    try {
        let response;

        if (provider === 'google') {
            response = await fetch(`${API_URL}/auth/oauth/google/callback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code,
                    state,
                    redirect_uri: window.location.origin + '/auth/oauth-callback'
                })
            });
        } else if (provider === 'github') {
            response = await fetch(`${API_URL}/auth/oauth/github/callback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code,
                    state,
                    redirect_uri: window.location.origin + '/auth/oauth-callback'
                })
            });
        }

        const data = await response.json();

        if (response.ok) {
            // Store tokens
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);

            // Clear session
            sessionStorage.removeItem('oauth_provider');

            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            console.error('OAuth callback error:', data);
            window.location.href = `/auth/login.html?error=${encodeURIComponent(data.detail || 'Authentication failed')}`;
        }
    } catch (error) {
        console.error('OAuth callback error:', error);
        window.location.href = '/auth/login.html?error=callback_failed';
    }
}

// ============ Link Account (for existing users) ============

async function linkOAuthAccount(provider) {
    try {
        const response = await fetch(`${API_URL}/auth/oauth/link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                provider: provider,
                provider_id: 'user_id_from_oauth',
                email: 'email_from_oauth'
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`${provider.charAt(0).toUpperCase() + provider.slice(1)} account linked successfully!`);
            location.reload();
        } else {
            alert(data.detail || 'Failed to link account');
        }
    } catch (error) {
        console.error('Link account error:', error);
        alert('Failed to link account');
    }
}

// ============ Get Linked Accounts ============

async function getLinkedAccounts() {
    try {
        const response = await fetch(`${API_URL}/auth/oauth/linked-accounts`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            return data.linked_accounts;
        }
    } catch (error) {
        console.error('Get linked accounts error:', error);
    }
}

// ============ Unlink Account ============

async function unlinkOAuthAccount(provider) {
    if (confirm(`Are you sure you want to unlink your ${provider} account?`)) {
        try {
            const response = await fetch(`${API_URL}/auth/oauth/unlink`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    provider: provider
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert(`${provider.charAt(0).toUpperCase() + provider.slice(1)} account unlinked successfully!`);
                location.reload();
            } else {
                alert(data.detail || 'Failed to unlink account');
            }
        } catch (error) {
            console.error('Unlink account error:', error);
            alert('Failed to unlink account');
        }
    }
}

// ============ Check if page is OAuth callback ============

if (window.location.pathname === '/auth/oauth-callback') {
    handleOAuthCallback();
}
