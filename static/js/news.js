// Initializes AOS for scroll animations and Rellax for parallax effects

document.addEventListener('DOMContentLoaded', function() {
  // Animate on scroll (disable on mobile)
  if (typeof AOS !== 'undefined') {
    AOS.init({
      disable: 'mobile',
      offset: 120,      // offset (in px) from the original trigger point
      delay: 0,         // values from 0 to 3000, with step 50ms
      duration: 600,    // values from 0 to 3000, with step 50ms
      easing: 'ease-in-out',
      once: true,       // whether animation should happen only once - while scrolling down
    });
  }

  // Parallax (disable under 768px)
  if (typeof Rellax !== 'undefined') {
    new Rellax('.rellax', {
      center: true,
      round: true,
      breakpoints: [576, 768, 1201]
    });
  }
});
