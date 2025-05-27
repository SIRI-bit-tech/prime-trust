// Simple carousel functionality
document.addEventListener('DOMContentLoaded', function() {
    const carouselSlides = document.querySelectorAll('.carousel-slide');
    const carouselDots = document.querySelectorAll('.carousel-dot');
    let currentSlide = 0;
    
    // Function to show a specific slide
    function showSlide(index) {
        // Hide all slides
        carouselSlides.forEach(slide => {
            slide.classList.add('hidden');
        });
        
        // Remove active class from all dots
        carouselDots.forEach(dot => {
            dot.classList.remove('active');
        });
        
        // Show the selected slide
        carouselSlides[index].classList.remove('hidden');
        
        // Add active class to the selected dot
        carouselDots[index].classList.add('active');
        
        // Update current slide index
        currentSlide = index;
    }
    
    // Set up dot click handlers
    carouselDots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            showSlide(index);
        });
    });
    
    // Auto-rotate slides every 5 seconds
    function autoRotate() {
        let nextSlide = (currentSlide + 1) % carouselSlides.length;
        showSlide(nextSlide);
    }
    
    // Set up auto-rotation
    const autoRotateInterval = setInterval(autoRotate, 5000);
    
    // Pause auto-rotation when user interacts with dots
    carouselDots.forEach(dot => {
        dot.addEventListener('click', () => {
            clearInterval(autoRotateInterval);
            // Restart auto-rotation after 10 seconds of inactivity
            setTimeout(() => {
                setInterval(autoRotate, 5000);
            }, 10000);
        });
    });
});
