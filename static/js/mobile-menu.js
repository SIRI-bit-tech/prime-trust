// Initialize mobile menu functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenu();
    initNotificationSystem();
});

function initMobileMenu() {
    // Get elements with error handling
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const closeMenuButton = document.getElementById('close-mobile-menu');
    const mobileMenu = document.getElementById('mobile-menu');
    
    // Check if elements exist before proceeding
    if (!mobileMenuButton) {
        return false;
    }
    
    if (!mobileMenu) {
        return false;
    }
    
    // We can still proceed without the close button
    
    // Add padding to the top of the page to account for the fixed mobile top bar
    if (window.innerWidth < 768) { // md breakpoint in Tailwind
        document.body.classList.add('has-mobile-topbar');
    }
    
    // Get the menu panel (the sliding part)
    const menuPanel = mobileMenu.querySelector('.fixed.inset-y-0.right-0');
    
    if (!menuPanel) {
        // Try a more generic selector as fallback
        const altMenuPanel = mobileMenu.querySelector('div > div');
        if (!altMenuPanel) {
            return false;
        }
        return setupMenuHandlers(mobileMenuButton, closeMenuButton, mobileMenu, altMenuPanel);
    }
    
    return setupMenuHandlers(mobileMenuButton, closeMenuButton, mobileMenu, menuPanel);
}

// Set up event handlers for the mobile menu
function setupMenuHandlers(mobileMenuButton, closeMenuButton, mobileMenu, menuPanel) {
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
    mobileMenuButton.addEventListener('click', function(e) {
        e.preventDefault();
        openMenu();
    });
    
    // Close menu when clicking the close button
    if (closeMenuButton) {
        closeMenuButton.addEventListener('click', function(e) {
            e.preventDefault();
            closeMenu();
        });
    }
    
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
        link.addEventListener('click', function() {
            closeMenu();
        });
    });
    
    return true;
}

// Initialize notification system
function initNotificationSystem() {
    const notificationButton = document.getElementById('mobile-notification-button');
    const notificationDropdown = document.getElementById('mobile-notification-dropdown');
    
    if (!notificationButton || !notificationDropdown) {
        return false;
    }
    
    // Handle notification button click - load notifications via HTMX and show dropdown
    notificationButton.addEventListener('click', function(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Show the dropdown immediately
        notificationDropdown.classList.remove('hidden');
        
        // Listen for HTMX events to handle loading state
        document.body.addEventListener('htmx:beforeRequest', function(e) {
            if (e.detail.target.id === 'mobile-notification-dropdown') {
                // Loading state is already in the dropdown
            }
        }, {once: true});
        
        document.body.addEventListener('htmx:afterRequest', function(e) {
            if (e.detail.target.id === 'mobile-notification-dropdown') {
                // Ensure dropdown remains visible after request
                notificationDropdown.classList.remove('hidden');
            }
        }, {once: true})
        
        // Close mobile menu if open
        const mobileMenu = document.getElementById('mobile-menu');
        if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
            const menuPanel = mobileMenu.querySelector('.fixed.inset-y-0.right-0');
            if (menuPanel) {
                menuPanel.classList.add('translate-x-full');
                document.body.classList.remove('menu-open');
                
                mobileMenu.addEventListener('transitionend', function handler(e) {
                    if (e.target === menuPanel) {
                        mobileMenu.classList.add('hidden');
                        mobileMenu.removeEventListener('transitionend', handler);
                    }
                }, { once: true });
            }
        }
        
        // Close other dropdowns
        document.querySelectorAll('[id$="-dropdown"]').forEach(dropdown => {
            if (dropdown !== notificationDropdown && !dropdown.classList.contains('hidden')) {
                dropdown.classList.add('hidden');
            }
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
        if (!notificationDropdown.classList.contains('hidden') && 
            !notificationDropdown.contains(event.target) && 
            !notificationButton.contains(event.target)) {
            notificationDropdown.classList.add('hidden');
        }
    });
    
    // Poll for new notifications every 30 seconds
    setInterval(function() {
        if (document.getElementById('mobile-notification-button')) {
            const notificationUrl = document.getElementById('mobile-notification-button').getAttribute('hx-get');
            if (notificationUrl) {
                // Use fetch to check for new notifications without showing the dropdown
                fetch(notificationUrl)
                    .then(response => response.text())
                    .then(html => {
                        // Check if there are new notifications by looking for the notification indicator
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = html;
                        const hasNotifications = tempDiv.querySelector('.unread-notification') !== null;
                        
                        // Update the notification indicator
                        const indicator = document.querySelector('#mobile-notification-button .absolute');
                        if (hasNotifications && !indicator) {
                            // Add notification indicator if it doesn't exist
                            const newIndicator = document.createElement('span');
                            newIndicator.className = 'absolute top-0 left-0 block h-2 w-2 rounded-full bg-red-400 ring-2 ring-primary-600';
                            document.getElementById('mobile-notification-button').appendChild(newIndicator);
                        } else if (!hasNotifications && indicator) {
                            // Remove notification indicator if it exists but there are no notifications
                            indicator.remove();
                        }
                    })
                    .catch(error => {
                        // Silent error handling to avoid console errors
                    });
            }
        }
    }, 30000); // Check every 30 seconds
    
    return true;
}
