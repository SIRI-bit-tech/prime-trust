function formatPhoneNumber(input) {
    // Remove all non-digit characters
    let value = input.value.replace(/\D/g, '');
    
    // Limit to 10 digits
    value = value.substring(0, 10);
    
    // Format as (XXX) XXX-XXXX
    if (value.length > 0) {
        if (value.length <= 3) {
            value = `(${value}`;
        } else if (value.length <= 6) {
            value = `(${value.substring(0, 3)}) ${value.substring(3)}`;
        } else {
            value = `(${value.substring(0, 3)}) ${value.substring(3, 6)}-${value.substring(6)}`;
        }
    }
    
    // Update the input value
    input.value = value;
}

// Add event listener when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Find all phone number inputs
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    
    // Add event listeners to each phone input
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            formatPhoneNumber(this);
        });
        
        // Format any existing value
        if (input.value) {
            formatPhoneNumber(input);
        }
    });
}); 