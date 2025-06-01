// Registration form multi-step functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize the form with step 1 visible
    showStep(1);

    // Add event listener for state dropdown to populate cities
    const stateSelect = document.getElementById('id_state');
    if (stateSelect) {
        stateSelect.addEventListener('change', function() {
            populateCities(this.value);
        });
        
        // If state already has a value, populate cities
        if (stateSelect.value) {
            populateCities(stateSelect.value);
        }
    }

    // Add event listener for phone number formatting
    const phoneInput = document.getElementById('id_phone_number');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            formatPhoneNumber(this);
        });
        
        // Format phone number if it already has a value
        if (phoneInput.value) {
            formatPhoneNumber(phoneInput);
        }
    }
    
    // Check if we need to show step 2 (e.g., after form validation error)
    const registrationStep = document.getElementById('registration_step');
    if (registrationStep && registrationStep.value === '2') {
        showStep(2);
    }
});

// Make functions globally accessible
window.populateCities = populateCities;
window.goToSecurityQuestions = goToSecurityQuestions;
window.goBackToPersonalInfo = goBackToPersonalInfo;
window.formatPhoneNumber = formatPhoneNumber;

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
            indicator.classList.remove('bg-primary-100', 'border-primary-500', 'text-primary-700', 'bg-primary-500', 'text-white');
            indicator.classList.add('bg-gray-200', 'border-gray-300', 'text-gray-700');
        }
    });
}

/**
 * Go to the security questions step (step 2)
 */
function goToSecurityQuestions() {
    // Validate step 1 fields first
    if (validateStep1()) {
        showStep(2);
    }
}

/**
 * Go back to the personal information step (step 1)
 */
function goBackToPersonalInfo() {
    showStep(1);
}

/**
 * Format phone number input to US format (XXX) XXX-XXXX
 * @param {HTMLInputElement} input - The phone number input element
 */
function formatPhoneNumber(input) {
    // Strip all non-numeric characters
    let phoneNumber = input.value.replace(/\D/g, '');
    
    // Format the number as (XXX) XXX-XXXX
    if (phoneNumber.length > 0) {
        if (phoneNumber.length <= 3) {
            phoneNumber = `(${phoneNumber}`;
        } else if (phoneNumber.length <= 6) {
            phoneNumber = `(${phoneNumber.substring(0, 3)}) ${phoneNumber.substring(3)}`;
        } else {
            phoneNumber = `(${phoneNumber.substring(0, 3)}) ${phoneNumber.substring(3, 6)}-${phoneNumber.substring(6, 10)}`;
        }
    }
    
    // Update the input value (only if it's different to avoid cursor jumping)
    if (input.value !== phoneNumber) {
        input.value = phoneNumber;
    }
}

/**
 * Validate all required fields in step 1
 * @returns {boolean} True if all fields are valid, false otherwise
 */
function validateStep1() {
    // Get all required fields in step 1
    const step1 = document.getElementById('step-1');
    const requiredFields = step1.querySelectorAll('[required]');
    
    let isValid = true;
    
    // Check each required field
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            // Add error styling
            field.classList.add('border-red-500');
            
            // Get or create error message
            let errorMsg = field.parentNode.querySelector('.error-message');
            if (!errorMsg) {
                errorMsg = document.createElement('p');
                errorMsg.className = 'mt-1 text-sm text-red-600 error-message';
                field.parentNode.appendChild(errorMsg);
            }
            errorMsg.textContent = 'This field is required';
        } else {
            // Remove error styling
            field.classList.remove('border-red-500');
            
            // Remove error message if exists
            const errorMsg = field.parentNode.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.remove();
            }
        }
    });
    
    return isValid;
}
/**
 * US States and their cities mapping
 * This is used for the city dropdown population in the registration form
 */
const US_STATES_CITIES = {
    'AL': ['Birmingham', 'Montgomery', 'Mobile', 'Huntsville', 'Tuscaloosa'],
    'AK': ['Anchorage', 'Fairbanks', 'Juneau', 'Sitka', 'Ketchikan'],
    'AZ': ['Phoenix', 'Tucson', 'Mesa', 'Chandler', 'Scottsdale', 'Glendale', 'Tempe'],
    'AR': ['Little Rock', 'Fort Smith', 'Fayetteville', 'Springdale', 'Jonesboro'],
    'CA': ['Los Angeles', 'San Diego', 'San Jose', 'San Francisco', 'Fresno', 'Sacramento', 'Long Beach', 'Oakland'],
    'CO': ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins', 'Lakewood', 'Boulder'],
    'CT': ['Bridgeport', 'New Haven', 'Hartford', 'Stamford', 'Waterbury'],
    'DE': ['Wilmington', 'Dover', 'Newark', 'Middletown', 'Smyrna'],
    'FL': ['Jacksonville', 'Miami', 'Tampa', 'Orlando', 'St. Petersburg', 'Hialeah', 'Tallahassee'],
    'GA': ['Atlanta', 'Augusta', 'Columbus', 'Savannah', 'Athens', 'Sandy Springs'],
    'HI': ['Honolulu', 'Hilo', 'Kailua', 'Kapolei', 'Kaneohe'],
    'ID': ['Boise', 'Nampa', 'Meridian', 'Idaho Falls', 'Pocatello'],
    'IL': ['Chicago', 'Aurora', 'Rockford', 'Joliet', 'Naperville', 'Springfield'],
    'IN': ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend', 'Carmel'],
    'IA': ['Des Moines', 'Cedar Rapids', 'Davenport', 'Sioux City', 'Iowa City'],
    'KS': ['Wichita', 'Overland Park', 'Kansas City', 'Olathe', 'Topeka'],
    'KY': ['Louisville', 'Lexington', 'Bowling Green', 'Owensboro', 'Covington'],
    'LA': ['New Orleans', 'Baton Rouge', 'Shreveport', 'Lafayette', 'Lake Charles'],
    'ME': ['Portland', 'Lewiston', 'Bangor', 'South Portland', 'Auburn'],
    'MD': ['Baltimore', 'Frederick', 'Rockville', 'Gaithersburg', 'Bowie'],
    'MA': ['Boston', 'Worcester', 'Springfield', 'Lowell', 'Cambridge'],
    'MI': ['Detroit', 'Grand Rapids', 'Warren', 'Sterling Heights', 'Ann Arbor'],
    'MN': ['Minneapolis', 'St. Paul', 'Rochester', 'Duluth', 'Bloomington'],
    'MS': ['Jackson', 'Gulfport', 'Southaven', 'Hattiesburg', 'Biloxi'],
    'MO': ['Kansas City', 'St. Louis', 'Springfield', 'Columbia', 'Independence'],
    'MT': ['Billings', 'Missoula', 'Great Falls', 'Bozeman', 'Butte'],
    'NE': ['Omaha', 'Lincoln', 'Bellevue', 'Grand Island', 'Kearney'],
    'NV': ['Las Vegas', 'Henderson', 'Reno', 'North Las Vegas', 'Sparks'],
    'NH': ['Manchester', 'Nashua', 'Concord', 'Derry', 'Dover'],
    'NJ': ['Newark', 'Jersey City', 'Paterson', 'Elizabeth', 'Edison'],
    'NM': ['Albuquerque', 'Las Cruces', 'Rio Rancho', 'Santa Fe', 'Roswell'],
    'NY': ['New York City', 'Buffalo', 'Rochester', 'Yonkers', 'Syracuse', 'Albany'],
    'NC': ['Charlotte', 'Raleigh', 'Greensboro', 'Durham', 'Winston-Salem'],
    'ND': ['Fargo', 'Bismarck', 'Grand Forks', 'Minot', 'West Fargo'],
    'OH': ['Columbus', 'Cleveland', 'Cincinnati', 'Toledo', 'Akron'],
    'OK': ['Oklahoma City', 'Tulsa', 'Norman', 'Broken Arrow', 'Edmond'],
    'OR': ['Portland', 'Salem', 'Eugene', 'Gresham', 'Hillsboro'],
    'PA': ['Philadelphia', 'Pittsburgh', 'Allentown', 'Erie', 'Reading'],
    'RI': ['Providence', 'Warwick', 'Cranston', 'Pawtucket', 'East Providence'],
    'SC': ['Columbia', 'Charleston', 'North Charleston', 'Mount Pleasant', 'Rock Hill'],
    'SD': ['Sioux Falls', 'Rapid City', 'Aberdeen', 'Brookings', 'Watertown'],
    'TN': ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Clarksville'],
    'TX': ['Houston', 'San Antonio', 'Dallas', 'Austin', 'Fort Worth', 'El Paso', 'Arlington'],
    'UT': ['Salt Lake City', 'West Valley City', 'Provo', 'West Jordan', 'Orem'],
    'VT': ['Burlington', 'South Burlington', 'Rutland', 'Essex Junction', 'Bennington'],
    'VA': ['Virginia Beach', 'Norfolk', 'Chesapeake', 'Richmond', 'Newport News'],
    'WA': ['Seattle', 'Spokane', 'Tacoma', 'Vancouver', 'Bellevue'],
    'WV': ['Charleston', 'Huntington', 'Parkersburg', 'Morgantown', 'Wheeling'],
    'WI': ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine'],
    'WY': ['Cheyenne', 'Casper', 'Laramie', 'Gillette', 'Rock Springs'],
    'DC': ['Washington']
};

/**
 * Populate the city dropdown based on the selected state
 * @param {string} stateCode - The selected state code
 */
function populateCities(stateCode) {
    const citySelect = document.getElementById('id_city');
    if (!citySelect) {
        return;
    }
    
    // Store the current selected city if any
    const currentCity = citySelect.value;
    
    // Clear existing options
    citySelect.innerHTML = '';
    
    // Add default option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select a city';
    citySelect.appendChild(defaultOption);
    
    // If no state is selected or state doesn't exist in our data
    if (!stateCode || !US_STATES_CITIES[stateCode]) {
        citySelect.disabled = true;
        return;
    }
    
    // Enable the city select
    citySelect.disabled = false;
    
    // Add cities for the selected state
    const cities = US_STATES_CITIES[stateCode];
    cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        
        // If this was the previously selected city, select it again
        if (city === currentCity) {
            option.selected = true;
        }
        
        citySelect.appendChild(option);
    });
    
    // Trigger change event to notify any listeners
    const event = new Event('change', { bubbles: true });
    citySelect.dispatchEvent(event);
    

    
    // If there's only one city, select it automatically
    if (cities.length === 1) {
        citySelect.value = cities[0];
    }
}
