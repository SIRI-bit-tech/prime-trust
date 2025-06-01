// Handle notification functionality
document.addEventListener('DOMContentLoaded', function() {
    // We're not initializing the dropdown toggle here anymore
    // That's handled in mobile-menu.js to avoid conflicts
    
    // We'll just focus on handling notification content after it's loaded
    
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
