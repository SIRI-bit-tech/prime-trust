document.addEventListener('DOMContentLoaded', function() {
    // Toggle loan application form
    const showApplicationBtn = document.getElementById('show-application-btn');
    const loanApplicationForm = document.getElementById('loan-application-form');
    
    if (showApplicationBtn && loanApplicationForm) {
        showApplicationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            loanApplicationForm.classList.toggle('hidden');
            this.textContent = loanApplicationForm.classList.contains('hidden') ? 
                'Apply for a New Loan' : 'Cancel Application';
        });
    }
    
    // Handle loan amount slider
    const loanAmountSlider = document.getElementById('loan-amount');
    const loanAmountValue = document.getElementById('loan-amount-value');
    
    if (loanAmountSlider && loanAmountValue) {
        loanAmountSlider.addEventListener('input', function() {
            loanAmountValue.textContent = '$' + Number(this.value).toLocaleString();
            updateLoanEstimate();
        });
    }
    
    // Handle loan term change
    const loanTermSelect = document.getElementById('loan-term');
    
    if (loanTermSelect) {
        loanTermSelect.addEventListener('change', updateLoanEstimate);
    }
    
    // Update loan estimate
    function updateLoanEstimate() {
        const amount = parseFloat(loanAmountSlider.value) || 0;
        const term = parseInt(loanTermSelect.value) || 12;
        
        // Simple interest calculation (in a real app, this would be more complex)
        const interestRate = 0.08; // 8% annual interest
        const monthlyRate = interestRate / 12;
        const monthlyPayment = (amount * monthlyRate * Math.pow(1 + monthlyRate, term)) / 
                             (Math.pow(1 + monthlyRate, term) - 1);
        
        const totalPayment = monthlyPayment * term;
        const totalInterest = totalPayment - amount;
        
        // Update the UI
        const monthlyPaymentEl = document.getElementById('monthly-payment');
        const totalInterestEl = document.getElementById('total-interest');
        const totalPaymentEl = document.getElementById('total-payment');
        
        if (monthlyPaymentEl) monthlyPaymentEl.textContent = '$' + monthlyPayment.toFixed(2);
        if (totalInterestEl) totalInterestEl.textContent = '$' + totalInterest.toFixed(2);
        if (totalPaymentEl) totalPaymentEl.textContent = '$' + totalPayment.toFixed(2);
    }
    
    // Initialize the loan calculator
    if (loanAmountSlider) {
        loanAmountSlider.dispatchEvent(new Event('input'));
    }
});
