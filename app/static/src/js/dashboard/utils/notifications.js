/**
 * Notification utilities for the dashboard
 * Replaces alert() with modern Toast notifications
 */

export function showNotification(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) {
    console.warn('Toast container not found, falling back to alert');
    alert(message);
    return;
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  }[type] || 'ℹ️';

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <div class="toast-content">${message}</div>
    <button class="toast-close">×</button>
  `;

  // Auto-remove after 4 seconds
  const timeoutId = setTimeout(() => {
    removeToast(toast);
  }, 4000);

  // Close button handler
  toast.querySelector('.toast-close').addEventListener('click', () => {
    clearTimeout(timeoutId); // Prevent double-removal logic
    removeToast(toast);
  });

  // Hover to pause
  toast.addEventListener('mouseenter', () => clearTimeout(timeoutId));
  toast.addEventListener('mouseleave', () => {
    setTimeout(() => removeToast(toast), 2000);
  });

  // Append with animation
  container.appendChild(toast);
  // Force reflow for animation
  void toast.offsetWidth;
  toast.classList.add('show');
}

function removeToast(toast) {
  toast.classList.remove('show');
  toast.addEventListener('transitionend', () => {
    if (toast.parentElement) {
      toast.parentElement.removeChild(toast);
    }
  });
}