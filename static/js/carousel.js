// Simple carousel functionality
function initCarousel() {
    const carouselSlides = document.querySelectorAll('.carousel-slide');
    const carouselDots = document.querySelectorAll('.carousel-dot');
    
    // If no slides or dots found, exit
    if (carouselSlides.length === 0 || carouselDots.length === 0) {
        console.warn('Carousel elements not found');
        return;
    }
    
    let currentSlide = 0;
    let autoRotateInterval;
    
    // Function to show a specific slide
    function showSlide(index) {
        // Ensure index is within bounds
        if (index >= carouselSlides.length) index = 0;
        if (index < 0) index = carouselSlides.length - 1;
        
        // Hide all slides
        carouselSlides.forEach(slide => {
            slide.classList.add('hidden');
            slide.setAttribute('aria-hidden', 'true');
        });
        
        // Remove active class from all dots
        carouselDots.forEach(dot => {
            dot.classList.remove('active');
            dot.setAttribute('aria-selected', 'false');
        });
        
        // Show the selected slide
        carouselSlides[index].classList.remove('hidden');
        carouselSlides[index].setAttribute('aria-hidden', 'false');
        
        // Add active class to the selected dot
        if (carouselDots[index]) {
            carouselDots[index].classList.add('active');
            carouselDots[index].setAttribute('aria-selected', 'true');
        }
        
        // Update current slide index
        currentSlide = index;
    }
    
    // Set up dot click handlers
    carouselDots.forEach((dot, index) => {
        dot.addEventListener('click', (e) => {
            e.preventDefault();
            showSlide(index);
            resetAutoRotate();
        });
        
        // Add keyboard navigation
        dot.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showSlide(index);
                resetAutoRotate();
            }
        });
    });
    
    // Auto-rotate slides every 5 seconds
    function autoRotate() {
        let nextSlide = (currentSlide + 1) % carouselSlides.length;
        showSlide(nextSlide);
    }
    
    // Reset auto-rotation timer
    function resetAutoRotate() {
        if (autoRotateInterval) {
            clearInterval(autoRotateInterval);
        }
        autoRotateInterval = setInterval(autoRotate, 5000);
    }
    
    // Initialize the carousel
    function init() {
        // Show first slide
        showSlide(0);
        
        // Start auto-rotation
        resetAutoRotate();
        
        // Pause auto-rotation on touch devices when user interacts
        const carousel = document.querySelector('.carousel-container');
        if (carousel) {
            carousel.addEventListener('touchstart', () => {
                if (autoRotateInterval) {
                    clearInterval(autoRotateInterval);
                }
            });
            
            // Restart auto-rotation after 10 seconds of inactivity
            let touchEndTimer;
            carousel.addEventListener('touchend', () => {
                if (touchEndTimer) clearTimeout(touchEndTimer);
                touchEndTimer = setTimeout(resetAutoRotate, 10000);
            });
        }
    }
    
    // Initialize carousel when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already loaded
        init();
    }
}

// Initialize carousel
initCarousel();
