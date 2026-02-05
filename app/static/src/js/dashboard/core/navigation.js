/**
 * WARNING:
 * This app uses SERVER-SIDE ROUTING (Flask).
 * DO NOT intercept <a> clicks or use SPA navigation here.
 * Any preventDefault() on navigation is a production-breaking bug.
 */
export function initNavigation() {
  // Navigation is now handled server-side.
  // This function is kept to maintain the module structure but no longer hijacks links.
  console.log('Navigation initialized (Server-Side Mode)');

  // Handle Hash-based initial view (SPA-lite behavior for specific tabs like #subscription-management)
  if (window.location.hash) {
    const targetId = window.location.hash.substring(1);
    const targetSection = document.getElementById(targetId);
    if (targetSection && targetSection.classList.contains('page-section')) {
      // Hide all other page sections (and ensure their inline styles don't override)
      document.querySelectorAll('.page-section').forEach(sec => {
        sec.style.display = 'none';
        sec.classList.remove('active');
      });
      // Show target
      targetSection.style.display = 'block';
      targetSection.classList.add('active');
      targetSection.scrollIntoView();
    }
  }

  // Update navbar active state based on hash? (Optional, might conflict with server-side rendered class)
}

export function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  sidebar.classList.toggle('open');
}

// Add touch event handlers for mobile navigation
if (typeof window !== 'undefined') {
  window.toggleSidebar = toggleSidebar;
}
