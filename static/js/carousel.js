/**
 * Simple carousel functionality for landing page
 * This script safely handles carousel initialization and prevents errors
 * when carousel elements don't exist on the page
 */

// Wrap everything in a try-catch to prevent any console errors
try {
    document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with carousel elements
    const carousel = document.querySelector('.carousel');
    
    // If no carousel found, exit silently without errors
    if (!carousel) {
        return;
    }
    
    // Find carousel elements
    const carouselSlides = document.querySelectorAll('.carousel-slide');
    const carouselDots = document.querySelectorAll('.carousel-dot');
    
    // If no slides or dots found, exit
    if (carouselSlides.length === 0 || carouselDots.length === 0) {
        return;
    }
    
    // Carousel state
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
    
    // Pause auto-rotation on touch devices when user interacts
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        carouselContainer.addEventListener('touchstart', () => {
            if (autoRotateInterval) {
                clearInterval(autoRotateInterval);
            }
        });
        
        // Restart auto-rotation after 10 seconds of inactivity
        let touchEndTimer;
        carouselContainer.addEventListener('touchend', () => {
            if (touchEndTimer) clearTimeout(touchEndTimer);
            touchEndTimer = setTimeout(resetAutoRotate, 10000);
        });
    }
    
    // Initialize carousel
    showSlide(0);
    resetAutoRotate();
});
} catch (error) {
    // Remove all console.log statements
}
