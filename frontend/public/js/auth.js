// Auth JavaScript - Handle login and registration

const API_URL = `${window.location.origin}/api`;

// ============ Password Visibility Toggle ============
document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', (e) => {
        e.preventDefault();
        const input = button.previousElementSibling;
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '👁️‍🗨️';
        } else {
            input.type = 'password';
            button.textContent = '👁️';
        }
    });
});

// ============ Password Strength Validation ============
const passwordInput = document.getElementById('password');
if (passwordInput) {
    passwordInput.addEventListener('input', (e) => {
        const password = e.target.value;

        // Show requirements if on register page
        const requirements = document.querySelector('.password-requirements');
        if (requirements) {
            requirements.classList.add('show');

            const checks = {
                'req-length': password.length >= 8,
                'req-uppercase': /[A-Z]/.test(password),
                'req-lowercase': /[a-z]/.test(password),
                'req-number': /\d/.test(password),
                'req-special': /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)
            };

            Object.entries(checks).forEach(([id, met]) => {
                const elem = document.getElementById(id);
                if (elem) {
                    if (met) {
                        elem.classList.add('met');
                    } else {
                        elem.classList.remove('met');
                    }
                }
            });
        }
    });
}

// ============ Login Form Handler ============
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formError = document.getElementById('formError');
        const formSuccess = document.getElementById('formSuccess');

        // Clear messages
        formError.style.display = 'none';
        formSuccess.style.display = 'none';

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const rememberMe = document.getElementById('rememberMe').checked;

        console.log('[Auth] Login form submitted for:', email);

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password,
                    remember_me: rememberMe
                })
            });

            const data = await response.json();

            console.log('[Auth] Login response:', {
                status: response.status,
                hasAccessToken: !!data.access_token,
                tokenLength: data.access_token ? data.access_token.length : 0
            });

            if (response.ok) {
                // Store tokens
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);

                console.log('[Auth] Tokens stored in localStorage:', {
                    accessTokenLength: data.access_token.length,
                    refreshTokenLength: data.refresh_token.length,
                    storedAccessToken: localStorage.getItem('access_token') ? localStorage.getItem('access_token').length : 0
                });

                formSuccess.textContent = '✓ Login successful! Redirecting...';
                formSuccess.style.display = 'block';

                // Redirect after 1 second
                setTimeout(() => {
                    console.log('[Auth] Redirecting to /dashboard');
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                formError.textContent = data.detail || 'Login failed. Please try again.';
                formError.style.display = 'block';
            }
        } catch (error) {
            console.error('Login error:', error);
            formError.textContent = 'Network error. Please check your connection.';
            formError.style.display = 'block';
        }
    });
}

// ============ Register Form Handler ============
const registerForm = document.getElementById('registerForm');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formError = document.getElementById('formError');
        const formSuccess = document.getElementById('formSuccess');

        // Clear messages
        formError.style.display = 'none';
        formSuccess.style.display = 'none';

        const fullName = document.getElementById('fullName').value;
        const email = document.getElementById('email').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const role = document.getElementById('role').value;
        const terms = document.getElementById('terms').checked;

        // Validate terms
        if (!terms) {
            document.getElementById('termsError').textContent = 'You must agree to the terms';
            document.getElementById('termsError').style.display = 'block';
            return;
        }

        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    full_name: fullName,
                    email,
                    username,
                    password,
                    role
                })
            });

            const data = await response.json();

            if (response.ok) {
                formSuccess.innerHTML = `
                    <div style="text-align: center;">
                        <p style="margin-bottom: 12px;">✓ Account created successfully!</p>
                        <p style="font-size: 14px;">You can now sign in with your credentials.</p>
                        <a href="/login" style="color: var(--primary-color); text-decoration: underline; margin-top: 12px; display: block;">Go to Sign In</a>
                    </div>
                `;
                formSuccess.style.display = 'block';
                registerForm.reset();
            } else {
                formError.textContent = data.detail || 'Registration failed. Please try again.';
                formError.style.display = 'block';
            }
        } catch (error) {
            console.error('Registration error:', error);
            formError.textContent = 'Network error. Please check your connection.';
            formError.style.display = 'block';
        }
    });
}

// ============ OAuth Buttons (Placeholder) ============
document.querySelectorAll('.oauth-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        alert('OAuth login will be implemented soon!');
    });
});
