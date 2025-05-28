document.addEventListener('DOMContentLoaded', function() {
    // Toggle recurring payment options
    const isRecurringCheckbox = document.getElementById('is_recurring');
    const recurringOptions = document.getElementById('recurring-options');
    
    function toggleRecurringOptions() {
        if (isRecurringCheckbox.checked) {
            recurringOptions.classList.remove('hidden');
        } else {
            recurringOptions.classList.add('hidden');
        }
    }
    
    if (isRecurringCheckbox) {
        isRecurringCheckbox.addEventListener('change', toggleRecurringOptions);
    }
    
    // Set minimum date for scheduled_date to today
    const scheduledDateInput = document.getElementById('scheduled_date');
    if (scheduledDateInput) {
        const today = new Date().toISOString().split('T')[0];
        scheduledDateInput.min = today;
        
        // Set minimum date for end_date to scheduled_date
        const endDateInput = document.getElementById('end_date');
        if (endDateInput) {
            scheduledDateInput.addEventListener('change', function() {
                endDateInput.min = this.value;
            });
        }
    }
    
    // Initialize the form state
    if (isRecurringCheckbox) {
        toggleRecurringOptions();
    }
});
