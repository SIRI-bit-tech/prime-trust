// landing.js: Initialize parallax (Rellax) and carousel animations
document.addEventListener('DOMContentLoaded', function() {
  // Parallax: initialize on all elements with class 'rellax'
  if (typeof Rellax !== 'undefined') {
    new Rellax('.rellax', { center: true, round: true, breakpoints: [576, 768, 1201] });
  }
  // Animate on scroll (Landing) using AOS
  if (typeof AOS !== 'undefined') {
    AOS.init({ disable: 'mobile', offset: 120, duration: 600, easing: 'ease-in-out', once: true });
  }
  // Carousel
  const slides = document.querySelectorAll('.carousel-slide');
  const dots = document.querySelectorAll('.carousel-dot');
  let current = 0;
  function showSlide(i) {
    slides.forEach((s, idx) => s.classList.toggle('hidden', idx !== i));
    dots.forEach((d, idx) => d.classList.toggle('active', idx === i));
  }
  function nextSlide() {
    current = (current + 1) % slides.length;
    showSlide(current);
  }
  showSlide(0);
  setInterval(nextSlide, 5000);
  // Scroll animations
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-fade-in', 'opacity-100');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.feature-card').forEach(el => {
    el.classList.add('opacity-0');
    observer.observe(el);
  });
  // Counter animations
  const countElements = document.querySelectorAll('.count-up');
  const countObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  countElements.forEach(el => countObserver.observe(el));

  function animateCount(el) {
    const target = +el.getAttribute('data-target');
    let current = 0;
    const increment = target / 200;
    function update() {
      current += increment;
      if (current < target) {
        el.textContent = Math.floor(current).toLocaleString();
        requestAnimationFrame(update);
      } else {
        el.textContent = target.toLocaleString();
      }
    }
    update();
  }
});
