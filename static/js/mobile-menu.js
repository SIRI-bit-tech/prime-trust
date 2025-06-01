document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const closeMenuButton = document.getElementById('close-mobile-menu');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuPanel = mobileMenu.querySelector('div > div');
    const body = document.body;
    
    function openMenu() {
        mobileMenu.classList.remove('hidden');
        body.classList.add('menu-open');
        // Force reflow to enable transition
        void mobileMenu.offsetWidth;
        menuPanel.classList.remove('translate-x-full');
    }
    
    function closeMenu() {
        menuPanel.classList.add('translate-x-full');
        body.classList.remove('menu-open');
        
        mobileMenu.addEventListener('transitionend', function handler(e) {
            // Only run this when the panel has finished transitioning
            if (e.target === menuPanel) {
                mobileMenu.classList.add('hidden');
                mobileMenu.removeEventListener('transitionend', handler);
            }
        }, { once: true });
    }
    
    // Toggle menu when clicking the hamburger button
    mobileMenuButton.addEventListener('click', openMenu);
    
    // Close menu when clicking the close button
    closeMenuButton.addEventListener('click', closeMenu);
    
    // Close menu when clicking outside the menu panel
    mobileMenu.addEventListener('click', function(e) {
        if (e.target === mobileMenu) {
            closeMenu();
        }
    });
    
    // Close menu when pressing Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !mobileMenu.classList.contains('hidden')) {
            closeMenu();
        }
    });
    
    // Close menu when clicking on any navigation link
    const navLinks = mobileMenu.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', closeMenu);
    });
});
