/**
 * Notification utilities for the dashboard
 */

export function showNotification(message, type = 'info') {
  // For now, use alert. In a real app, you'd want a proper toast notification system
  const prefix = {
    success: '✅ ',
    error: '❌ ',
    warning: '⚠️ ',
    info: 'ℹ️ '
  }[type] || '';

  alert(prefix + message);
}