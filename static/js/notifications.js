// Toggle mobile notification dropdown
document.addEventListener('DOMContentLoaded', function() {
    const notificationButton = document.getElementById('mobile-notification-button');
    const notificationDropdown = document.getElementById('mobile-notification-dropdown');
    
    if (notificationButton && notificationDropdown) {
        // Toggle dropdown when clicking the notification button
        notificationButton.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            
            // Toggle the dropdown
            const isHidden = notificationDropdown.classList.toggle('hidden');
            
            // Close other dropdowns
            if (!isHidden) {
                document.querySelectorAll('[id$="-dropdown"]').forEach(dropdown => {
                    if (dropdown !== notificationDropdown && !dropdown.classList.contains('hidden')) {
                        dropdown.classList.add('hidden');
                    }
                });
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (!notificationDropdown.contains(event.target) && !notificationButton.contains(event.target)) {
                notificationDropdown.classList.add('hidden');
            }
        });
    }
    
    // Handle HTMX after swap for notification dropdown
    document.body.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'mobile-notification-dropdown') {
            // Add click handler to notification items
            const notificationItems = document.querySelectorAll('#mobile-notification-dropdown a[href^="/notifications/"]');
            notificationItems.forEach(item => {
                item.addEventListener('click', function() {
                    document.getElementById('mobile-notification-dropdown').classList.add('hidden');
                });
            });
        }
    });
});
