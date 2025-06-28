// Registration form multi-step functionality

/**
 * Show the specified step and hide others
 * @param {number} stepNumber - The step number to show (1 or 2)
 */
function showStep(stepNumber) {
    // Hide all steps
    const steps = document.querySelectorAll('.registration-step');
    steps.forEach(step => {
        // Use display none/block instead of hidden class for compatibility
        step.style.display = 'none';
        step.classList.remove('active');
    });

    // Show the requested step
    const stepToShow = document.getElementById(`step-${stepNumber}`);
    if (stepToShow) {
        stepToShow.style.display = 'block';
        stepToShow.classList.add('active');
    }
    
    // Show/hide step buttons
    const step1Buttons = document.getElementById('step-1-buttons');
    if (step1Buttons) {
        step1Buttons.style.display = stepNumber === 1 ? 'block' : 'none';
    }

    // Update step indicators
    updateStepIndicators(stepNumber);
    
    // Update progress bar
    const progressBar = document.querySelector('.step-progress');
    if (progressBar) {
        if (stepNumber === 1) {
            progressBar.style.width = '0%';
            progressBar.classList.add('width-0');
        } else {
            progressBar.style.width = '100%';
            progressBar.classList.remove('width-0');
        }
    }
    
    // Update the registration_step hidden field
    const stepField = document.getElementById('registration_step');
    if (stepField) {
        stepField.value = stepNumber;
    }
}

/**
 * Update the step indicators to show current progress
 * @param {number} currentStep - The current active step
 */
function updateStepIndicators(currentStep) {
    const indicators = document.querySelectorAll('.step-indicator');
    
    indicators.forEach((indicator, index) => {
        // Step number is index + 1
        const stepNum = index + 1;
        
        if (stepNum < currentStep) {
            // Previous steps - completed
            indicator.classList.remove('bg-gray-200', 'border-gray-300', 'text-gray-700', 'bg-primary-100', 'border-primary-500', 'text-primary-700');
            indicator.classList.add('bg-primary-500', 'text-white', 'border-primary-500');
        } else if (stepNum === currentStep) {
            // Current step - active
            indicator.classList.remove('bg-gray-200', 'border-gray-300', 'text-gray-700', 'bg-primary-500', 'text-white');
            indicator.classList.add('bg-primary-100', 'border-primary-500', 'text-primary-700');
        } else {
            // Future steps - inactive
            indicator.classList.remove('bg-primary-500', 'text-white', 'bg-primary-100', 'border-primary-500', 'text-primary-700');
            indicator.classList.add('bg-gray-200', 'border-gray-300', 'text-gray-700');
        }
    });
}

/**
 * Format phone number as user types
 * @param {HTMLInputElement} input - The phone number input element
 */
function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');
    if (value.length > 0) {
        if (value.length <= 3) {
            value = `(${value}`;
        } else if (value.length <= 6) {
            value = `(${value.slice(0, 3)}) ${value.slice(3)}`;
        } else {
            value = `(${value.slice(0, 3)}) ${value.slice(3, 6)}-${value.slice(6, 10)}`;
        }
    }
    input.value = value;
}

/**
 * Populate cities dropdown based on selected state
 * @param {string} stateCode - The selected state code
 */
function populateCities(stateCode) {
    const citySelect = document.getElementById('id_city');
    if (!citySelect) return;
    
    // Clear existing options
    citySelect.innerHTML = '<option value="">Select City</option>';
    citySelect.disabled = true;

    if (stateCode && window.US_CITIES && window.US_CITIES[stateCode]) {
        // Add cities for selected state
        window.US_CITIES[stateCode].forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            citySelect.appendChild(option);
        });
        citySelect.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all DOM elements
    const form = document.getElementById('registrationForm');
    const monthSelect = document.querySelector('select[name="birth_month"]');
    const daySelect = document.querySelector('select[name="birth_day"]');
    const yearSelect = document.querySelector('select[name="birth_year"]');
    const dateInput = document.getElementById('id_date_of_birth');
    const stateSelect = document.getElementById('id_state');
    const citySelect = document.getElementById('id_city');
    const genderInputs = document.querySelectorAll('input[name="gender"]');
    const password1Input = document.getElementById('id_password1');
    const password2Input = document.getElementById('id_password2');
    const password1Error = document.getElementById('password1-error');
    const password2Error = document.getElementById('password2-error');

    // State name to code mapping
    const STATE_CODES = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
        'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
        'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
        'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
        'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
        'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
        'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
        'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
        'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
        'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
    };

    // Handle password validation
    function validatePasswords() {
        if (password1Input.value.length < 8) {
            password1Error.classList.remove('hidden');
            return false;
        } else {
            password1Error.classList.add('hidden');
        }

        if (password1Input.value !== password2Input.value) {
            password2Error.classList.remove('hidden');
            return false;
        } else {
            password2Error.classList.add('hidden');
        }
        return true;
    }

    // Add password validation listeners
    if (password1Input && password2Input) {
        password1Input.addEventListener('input', validatePasswords);
        password2Input.addEventListener('input', validatePasswords);
    }

    // Handle date of birth fields
    function updateDateOfBirth() {
        if (!monthSelect.value || !daySelect.value || !yearSelect.value) return;
        
        const month = monthSelect.value.padStart(2, '0');
        const day = daySelect.value.padStart(2, '0');
        const year = yearSelect.value;
        
        dateInput.value = `${year}-${month}-${day}`;
    }

    // Add event listeners for date of birth
    if (monthSelect && daySelect && yearSelect) {
        monthSelect.addEventListener('change', updateDateOfBirth);
        daySelect.addEventListener('change', updateDateOfBirth);
        yearSelect.addEventListener('change', updateDateOfBirth);
    }

    // Handle state and city selection
    function populateCities(stateValue) {
        if (!citySelect) return;
        
        // Clear existing options
        citySelect.innerHTML = '<option value="">Select City</option>';
        citySelect.disabled = true;
    
        if (!stateValue) return;
    
        // Get cities for the selected state
        const cities = window.US_CITIES[stateValue];
        if (cities && cities.length > 0) {
    cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
                citySelect.appendChild(option);
            });
            citySelect.disabled = false;
        }
    }

    // Add event listener for state dropdown
    if (stateSelect) {
        stateSelect.addEventListener('change', function() {
            populateCities(this.value);
        });

        // Populate cities for initial state value if exists
        if (stateSelect.value) {
            populateCities(stateSelect.value);
        }
    }

    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            // Update date of birth before validation
            updateDateOfBirth();

            // Validate required fields
            if (!monthSelect.value || !daySelect.value || !yearSelect.value) {
                e.preventDefault();
                alert('Please select a complete date of birth');
                return;
            }

            if (!validatePasswords()) {
                e.preventDefault();
                return;
            }

            // Validate gender
            const genderSelected = document.querySelector('input[name="gender"]:checked');
            if (!genderSelected) {
                e.preventDefault();
                alert('Please select a gender');
                return;
            }

            // Validate city
            if (!citySelect.value) {
                e.preventDefault();
                alert('Please select a city');
                return;
            }

            // Let the form submit if all validations pass
        });
    }
});
