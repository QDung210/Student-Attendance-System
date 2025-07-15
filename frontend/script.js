document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.form');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginButton = document.querySelector('.button');
    const forgotPasswordLink = document.getElementById('forgotPassword');
    const registerLink = document.getElementById('registerLink');
    const eyeIcon = document.querySelector('.icon-eye');

    // Demo accounts
    const accounts = [
        { email: 'admin@fpt.edu.vn', password: 'admin123' },
        { email: 'teacher@fpt.edu.vn', password: 'teacher123' },
        { email: 'student@fpt.edu.vn', password: 'student123' }
    ];

    // Toggle password visibility
    eyeIcon.addEventListener('click', function() {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
        } else {
            passwordInput.type = 'password';
        }
    });

    // Handle form submission
    loginButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        
        // Clear previous errors
        clearErrors();
        
        // Validation
        let isValid = true;
        
        if (!email) {
            showError('email', 'Please enter your email');
            isValid = false;
        } else if (!isValidEmail(email)) {
            showError('email', 'Please enter a valid email address');
            isValid = false;
        }
        
        if (!password) {
            showError('password', 'Please enter your password');
            isValid = false;
        }
        
        if (!isValid) {
            shakeForm();
            return;
        }
        
        // Check credentials
        const account = accounts.find(acc => acc.email === email && acc.password === password);
        
        if (account) {
            // Login successful
            showSuccess('Login successful!');
            
            // Redirect after delay
            setTimeout(() => {
                alert('Redirecting to Face Recognition System...');
                // Here you would typically redirect to your main application
                // window.location.href = 'main-app.html';
            }, 1500);
            
        } else {
            // Login failed
            showError('password', 'Invalid email or password');
            shakeForm();
        }
    });

    // Handle forgot password
    forgotPasswordLink.addEventListener('click', function(e) {
        e.preventDefault();
        alert('Forgot Password feature will be implemented later.\n\nDemo accounts:\n- admin@fpt.edu.vn/admin123\n- teacher@fpt.edu.vn/teacher123\n- student@fpt.edu.vn/student123');
    });

    // Handle register link
    registerLink.addEventListener('click', function(e) {
        e.preventDefault();
        alert('Registration feature will be implemented later.\n\nPlease use demo accounts:\n- admin@fpt.edu.vn/admin123\n- teacher@fpt.edu.vn/teacher123\n- student@fpt.edu.vn/student123');
    });

    // Utility functions
    function showError(fieldName, message) {
        const field = document.getElementById(fieldName);
        const errorElement = document.getElementById(fieldName + 'Error');
        const container = field.closest('.frame-4');
        
        container.classList.add('error');
        errorElement.textContent = message;
    }

    function clearErrors() {
        const errorElements = document.querySelectorAll('.error-message');
        const containers = document.querySelectorAll('.frame-4');
        
        errorElements.forEach(element => {
            element.textContent = '';
        });
        
        containers.forEach(container => {
            container.classList.remove('error');
        });
        
        // Remove existing success message
        const existingSuccess = document.querySelector('.success-message');
        if (existingSuccess) {
            existingSuccess.remove();
        }
    }

    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        
        form.insertBefore(successDiv, form.firstChild);
    }

    function shakeForm() {
        const formContainer = document.querySelector('.group');
        formContainer.classList.add('shake');
        setTimeout(() => {
            formContainer.classList.remove('shake');
        }, 500);
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Handle Enter key
    emailInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            passwordInput.focus();
        }
    });

    passwordInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loginButton.click();
        }
    });

    // Clear errors when user starts typing
    emailInput.addEventListener('input', function() {
        if (this.value.trim()) {
            const container = this.closest('.frame-4');
            const errorElement = document.getElementById('emailError');
            container.classList.remove('error');
            errorElement.textContent = '';
        }
    });

    passwordInput.addEventListener('input', function() {
        if (this.value.trim()) {
            const container = this.closest('.frame-4');
            const errorElement = document.getElementById('passwordError');
            container.classList.remove('error');
            errorElement.textContent = '';
        }
    });

    // Focus on email input when page loads
    emailInput.focus();
});
