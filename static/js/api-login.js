/**
 * API-Based Login System
 * Handles multi-step authentication with 2FA and backup codes
 */

class APILogin {
    constructor() {
        this.currentStep = 'credentials';
        this.loginData = {};
        this.initializeEventListeners();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Credentials form
        const credentialsForm = document.getElementById('credentials-form');
        if (credentialsForm) {
            credentialsForm.addEventListener('submit', (e) => this.handleCredentialsSubmit(e));
        }

        // 2FA form
        const totpForm = document.getElementById('totp-form');
        if (totpForm) {
            totpForm.addEventListener('submit', (e) => this.handleTotpSubmit(e));
        }

        // Backup code form
        const backupForm = document.getElementById('backup-form');
        if (backupForm) {
            backupForm.addEventListener('submit', (e) => this.handleBackupSubmit(e));
        }

        // Navigation buttons
        const showBackupBtn = document.getElementById('show-backup-code');
        if (showBackupBtn) {
            showBackupBtn.addEventListener('click', () => this.showStep('backup'));
        }

        const backToCredentialsBtn = document.getElementById('back-to-credentials');
        if (backToCredentialsBtn) {
            backToCredentialsBtn.addEventListener('click', () => this.showStep('credentials'));
        }

        const backTo2faBtn = document.getElementById('back-to-2fa');
        if (backTo2faBtn) {
            backTo2faBtn.addEventListener('click', () => this.showStep('2fa'));
        }

        // Auto-format TOTP input (numbers only)
        const totpInput = document.getElementById('totp-token');
        if (totpInput) {
            totpInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '').substring(0, 6);
            });
        }

        // Auto-format backup code input (numbers only)
        const backupInput = document.getElementById('backup-code');
        if (backupInput) {
            backupInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '').substring(0, 8);
            });
        }
    }

    /**
     * Handle credentials form submission
     */
    async handleCredentialsSubmit(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        if (!email || !password) {
            this.showMessage('Please enter both email and password.', 'error');
            return;
        }

        // Store credentials for later use
        this.loginData = { email, password };

        this.setLoading('credentials-submit', true);
        this.hideMessage();

        try {
            const response = await this.makeAPICall('/api/v1/auth/login/', {
                email: email,
                password: password
            });

            if (response.success && response.data) {
                const data = response.data;

                if (data.requires_2fa) {
                    // Show 2FA step
                    this.showStep('2fa');
                    this.showMessage(`Authentication required. ${data.backup_codes_available ? 'You can also use a backup code.' : ''}`, 'info');
                } else if (data.access && data.refresh) {
                    // Direct login success (no 2FA)
                    this.handleLoginSuccess(data);
                }
            } else {
                this.showMessage(response.error || 'Login failed. Please check your credentials.', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Login failed. Please try again.', 'error');
        } finally {
            this.setLoading('credentials-submit', false);
        }
    }

    /**
     * Handle TOTP form submission
     */
    async handleTotpSubmit(e) {
        e.preventDefault();
        
        const totpToken = document.getElementById('totp-token').value;

        console.log('TOTP submit - token:', totpToken);
        console.log('TOTP submit - loginData:', this.loginData);

        if (!totpToken || totpToken.length !== 6) {
            this.showMessage('Please enter a 6-digit authentication code.', 'error');
            return;
        }

        this.setLoading('totp-submit', true);
        this.hideMessage();

        try {
            console.log('Making TOTP verification API call...');
            
            const response = await this.makeAPICall('/api/v1/auth/login/', {
                email: this.loginData.email,
                password: this.loginData.password,
                totp_token: totpToken
            });

            console.log('TOTP API response:', response);

            if (response.success && response.data) {
                const data = response.data;
                
                console.log('TOTP verification successful, data:', data);
                
                if (data.access && data.refresh) {
                    console.log('Tokens received, calling handleLoginSuccess...');
                    this.handleLoginSuccess(data);
                } else {
                    console.log('No tokens in response');
                    this.showMessage('Authentication failed. Please check your code.', 'error');
                }
            } else {
                console.log('TOTP verification failed:', response.error);
                this.showMessage(response.error || 'Invalid authentication code.', 'error');
                // Clear the input for retry
                document.getElementById('totp-token').value = '';
                document.getElementById('totp-token').focus();
            }
        } catch (error) {
            console.error('2FA verification error:', error);
            this.showMessage('Verification failed. Please try again.', 'error');
        } finally {
            this.setLoading('totp-submit', false);
        }
    }

    /**
     * Handle backup code form submission
     */
    async handleBackupSubmit(e) {
        e.preventDefault();
        
        const backupCode = document.getElementById('backup-code').value;

        if (!backupCode || backupCode.length !== 8) {
            this.showMessage('Please enter an 8-digit backup code.', 'error');
            return;
        }

        this.setLoading('backup-submit', true);
        this.hideMessage();

        try {
            const response = await this.makeAPICall('/api/v1/auth/login/', {
                email: this.loginData.email,
                password: this.loginData.password,
                backup_code: backupCode
            });

            if (response.success && response.data) {
                const data = response.data;
                
                if (data.access && data.refresh) {
                    this.handleLoginSuccess(data);
                } else {
                    this.showMessage('Authentication failed. Please check your backup code.', 'error');
                }
            } else {
                this.showMessage(response.error || 'Invalid backup code.', 'error');
                // Clear the input for retry
                document.getElementById('backup-code').value = '';
                document.getElementById('backup-code').focus();
            }
        } catch (error) {
            console.error('Backup code verification error:', error);
            this.showMessage('Verification failed. Please try again.', 'error');
        } finally {
            this.setLoading('backup-submit', false);
        }
    }

    /**
     * Handle successful login
     */
    async handleLoginSuccess(data) {
        console.log('handleLoginSuccess called with data:', data);
        
        // Store tokens in sessionStorage
        sessionStorage.setItem('access_token', data.access);
        sessionStorage.setItem('refresh_token', data.refresh);
        
        console.log('Tokens stored in sessionStorage');
        
        this.showMessage('Login successful! Establishing session...', 'success');
        
        try {
            console.log('Attempting to establish Django session...');
            
            // Establish Django session
            const sessionResponse = await this.makeAPICall('/accounts/establish-session/', {
                access_token: data.access
            });
            
            console.log('Session establishment response:', sessionResponse);
            
            if (sessionResponse.success) {
                console.log('Session established successfully, redirecting to:', sessionResponse.data.redirect_url);
                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = sessionResponse.data.redirect_url || '/dashboard/';
                }, 500);
            } else {
                console.log('Session establishment failed, using fallback redirect');
                // Fall back to storing tokens and redirecting
                this.showMessage('Login successful! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard/';
                }, 500);
            }
        } catch (error) {
            console.error('Session establishment error:', error);
            console.log('Using fallback redirect due to session error');
            // Fall back to storing tokens and redirecting
            this.showMessage('Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard/';
            }, 500);
        }
    }

    /**
     * Show a specific step in the login process
     */
    showStep(step) {
        // Hide all steps
        const steps = document.querySelectorAll('.login-step');
        steps.forEach(stepEl => stepEl.classList.add('hidden'));

        // Show the requested step
        const targetStep = document.getElementById(`step-${step}`);
        if (targetStep) {
            targetStep.classList.remove('hidden');
            this.currentStep = step;

            // Focus on the main input field
            const focusMap = {
                'credentials': 'email',
                '2fa': 'totp-token',
                'backup': 'backup-code'
            };
            
            const inputToFocus = document.getElementById(focusMap[step]);
            if (inputToFocus) {
                setTimeout(() => inputToFocus.focus(), 100);
            }
        }
    }

    /**
     * Show/hide loading state for buttons
     */
    setLoading(buttonId, loading) {
        const button = document.getElementById(buttonId);
        if (!button) return;

        const btnText = button.querySelector('.btn-text');
        const spinner = button.querySelector('.loading-spinner');

        if (loading) {
            button.disabled = true;
            if (btnText) btnText.classList.add('hidden');
            if (spinner) spinner.classList.remove('hidden');
        } else {
            button.disabled = false;
            if (btnText) btnText.classList.remove('hidden');
            if (spinner) spinner.classList.add('hidden');
        }
    }

    /**
     * Show message to user
     */
    showMessage(message, type = 'info') {
        const container = document.getElementById('message-container');
        const content = document.getElementById('message-content');
        const icon = document.getElementById('message-icon');
        const text = document.getElementById('message-text');

        if (!container || !content || !icon || !text) return;

        // Set message text
        text.textContent = message;

        // Set styling based on type
        const styles = {
            'error': {
                bgClass: 'bg-red-50',
                iconClass: 'text-red-400',
                textClass: 'text-red-800',
                iconPath: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z'
            },
            'success': {
                bgClass: 'bg-green-50',
                iconClass: 'text-green-400',
                textClass: 'text-green-800',
                iconPath: 'M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z'
            },
            'info': {
                bgClass: 'bg-blue-50',
                iconClass: 'text-blue-400',
                textClass: 'text-blue-800',
                iconPath: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z'
            }
        };

        const style = styles[type] || styles.info;

        // Update classes using classList methods
        content.className = ''; // Clear existing classes
        content.classList.add('rounded-md', 'p-4', style.bgClass);
        
        // For SVG elements, use classList methods
        icon.setAttribute('class', ''); // Clear existing classes
        icon.classList.add('h-5', 'w-5', style.iconClass);
        
        text.className = ''; // Clear existing classes
        text.classList.add('text-sm', 'font-medium', style.textClass);
        
        // Update icon path
        icon.innerHTML = `<path fill-rule="evenodd" d="${style.iconPath}" clip-rule="evenodd" />`;

        // Show container
        container.classList.remove('hidden');
    }

    /**
     * Hide message
     */
    hideMessage() {
        const container = document.getElementById('message-container');
        if (container) {
            container.classList.add('hidden');
        }
    }

    /**
     * Make API call with proper error handling
     */
    async makeAPICall(url, data) {
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                return { success: true, data: result };
            } else {
                return { 
                    success: false, 
                    error: result.error || result.detail || 'Request failed',
                    data: result 
                };
            }
        } catch (error) {
            console.error('API call failed:', error);
            return { 
                success: false, 
                error: 'Network error. Please check your connection.' 
            };
        }
    }

    /**
     * Get CSRF token from cookies
     */
    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) {
                return decodeURIComponent(value);
            }
        }
        return null;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new APILogin();
}); 