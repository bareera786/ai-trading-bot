import { fetchJson } from '../utils/network.js';

const IDS = {
  total: 'total-users-count',
  active: 'active-users-count',
  admin: 'admin-users-count',
  lastLogin: 'last-login-time',
  table: 'users-table',
  modal: 'add-user-modal',
  username: 'new-username',
  password: 'new-password',
  confirm: 'confirm-password',
  role: 'new-user-role',
  assignModal: 'assign-subscription-modal',
  assignUsername: 'assign-user-username',
  currentSubscription: 'current-subscription-info',
  planSelect: 'subscription-plan-select',
  trialDays: 'trial-days-input',
  autoRenew: 'auto-renew-checkbox',
  cancelExisting: 'cancel-existing-checkbox',
  notes: 'subscription-notes',
};

function updateCount(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function formatSubscriptionInfo(subscription) {
  if (!subscription) {
    return '<span class="status-indicator status-neutral">None</span>';
  }
  
  const status = subscription.is_active ? 'status-success' : 'status-error';
  const statusText = subscription.is_active ? 'Active' : 'Inactive';
  const planName = subscription.plan_name || 'Unknown Plan';
  const expires = subscription.expires_at ? new Date(subscription.expires_at).toLocaleDateString() : 'Never';
  
  return `<span class="status-indicator ${status}">${statusText}</span><br><small>${planName}<br>Expires: ${expires}</small>`;
}

let availablePlans = [];

export async function refreshUsers() {
  try {
    const data = await fetchJson('/api/users');
    const users = data?.users || [];
    const active = users.filter((user) => user.is_active).length;
    const admin = users.filter((user) => user.is_admin).length;
    const lastLogin = users.reduce((latest, user) => {
      if (!user.last_login) return latest;
      const current = new Date(user.last_login);
      return current > latest ? current : latest;
    }, new Date(0));

    updateCount(IDS.total, users.length);
    updateCount(IDS.active, active);
    updateCount(IDS.admin, admin);
    updateCount(IDS.lastLogin, lastLogin.getTime() ? lastLogin.toLocaleString() : 'Never');

    const tbody = document.getElementById(IDS.table);
    if (!tbody) return;
    tbody.innerHTML = '';

    users.forEach((user) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${user.username}</td>
        <td>${user.is_admin ? 'Administrator' : 'User'}</td>
        <td>${user.is_active ? '<span class="status-indicator status-success">Active</span>' : '<span class="status-indicator status-neutral">Inactive</span>'}</td>
        <td>${formatSubscriptionInfo(user.subscription)}</td>
        <td>${user.last_login || 'Never'}</td>
        <td>${user.created_at || 'Unknown'}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px; margin-right: 4px;" onclick="editUser('${user.username}')">Edit</button>
          <button class="btn btn-primary" style="padding: 4px 8px; font-size: 12px; margin-right: 4px;" onclick="assignSubscriptionToUser('${user.username}')">Subscription</button>
          <button class="btn btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteUser('${user.username}')">Delete</button>
        </td>
      `;
      tbody.appendChild(row);
    });
  } catch (error) {
    console.error('Failed to refresh users:', error);
  }
}

export function showAddUserModal() {
  const modal = document.getElementById(IDS.modal);
  if (modal) modal.style.display = 'flex';
}

export function closeAddUserModal() {
  const modal = document.getElementById(IDS.modal);
  if (modal) modal.style.display = 'none';
  const username = document.getElementById(IDS.username);
  const password = document.getElementById(IDS.password);
  const confirm = document.getElementById(IDS.confirm);
  const role = document.getElementById(IDS.role);
  if (username) username.value = '';
  if (password) password.value = '';
  if (confirm) confirm.value = '';
  if (role) role.value = 'user';
}

export async function addNewUser() {
  const username = document.getElementById(IDS.username)?.value.trim();
  const password = document.getElementById(IDS.password)?.value;
  const confirm = document.getElementById(IDS.confirm)?.value;
  const role = document.getElementById(IDS.role)?.value || 'user';

  if (!username || !password) {
    alert('Username and password are required');
    return;
  }
  if (password !== confirm) {
    alert('Passwords do not match');
    return;
  }

  try {
    const response = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ username, password, is_admin: role === 'admin' }),
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert('User created successfully');
      closeAddUserModal();
      refreshUsers();
    }
  } catch (error) {
    console.error('Failed to add user:', error);
    alert('Failed to create user');
  }
}

export async function deleteUser(username) {
  if (!confirm(`Delete user "${username}"?`)) return;
  try {
    const response = await fetch(`/api/users/${username}`, {
      method: 'DELETE',
      credentials: 'same-origin',
    });
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert('User deleted successfully');
      refreshUsers();
    }
  } catch (error) {
    console.error('Failed to delete user:', error);
    alert('Failed to delete user');
  }
}

export function editUser(username) {
  // Open modal and load user details
  fetchJson(`/api/users/${username}`)
    .then(user => {
      document.getElementById('edit-user-modal').style.display = 'flex';
      document.getElementById('edit-username').value = user.username || '';
      document.getElementById('edit-email').value = user.email || '';
      document.getElementById('edit-user-role').value = user.is_admin ? 'admin' : 'user';
      document.getElementById('edit-user-status').value = user.is_active ? 'active' : 'inactive';
      document.getElementById('edit-user-balance').value = user.portfolio_value || 0;
      document.getElementById('edit-user-subscription-expiry').value = (user.subscription && user.subscription.expires_at) ? new Date(user.subscription.expires_at).toLocaleDateString() : 'Never';
      document.getElementById('edit-user-password').value = '';
      window._editUserUsername = user.username;
    })
    .catch(err => {
      alert('Failed to load user details: ' + (err?.message || err));
    });
}

export function closeEditUserModal() {
  document.getElementById('edit-user-modal').style.display = 'none';
}

export async function saveUserEdit() {
  const username = window._editUserUsername;
  if (!username) return alert('No user selected.');
  const email = document.getElementById('edit-email').value;
  const is_admin = document.getElementById('edit-user-role').value === 'admin';
  const is_active = document.getElementById('edit-user-status').value === 'active';
  const password = document.getElementById('edit-user-password').value;
  const payload = { email, is_admin, is_active };
  if (password) payload.password = password;
  try {
    const resp = await fetch(`/api/users/${username}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || 'Unknown error');
    alert('User updated successfully.');
    closeEditUserModal();
    refreshUsers();
  } catch (err) {
    alert('Failed to update user: ' + (err?.message || err));
  }
}

export async function assignSubscriptionToUser(username) {
  // Set the username in the modal
  const usernameEl = document.getElementById(IDS.assignUsername);
  if (usernameEl) usernameEl.textContent = username;
  
  // Load available plans
  try {
    const plansData = await fetchJson('/api/admin/subscription/plans');
    availablePlans = plansData.plans || [];
    
    const select = document.getElementById(IDS.planSelect);
    if (select) {
      select.innerHTML = '<option value="">Select a plan...</option>';
      availablePlans.forEach(plan => {
        const option = document.createElement('option');
        option.value = plan.id;
        option.textContent = `${plan.name} - $${plan.price_usd}/${plan.plan_type}`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Failed to load subscription plans:', error);
    alert('Failed to load subscription plans');
    return;
  }
  
  // Load current user subscription info
  try {
    const userData = await fetchJson(`/api/users/${username}`);
    const subscriptionInfo = document.getElementById(IDS.currentSubscription);
    if (subscriptionInfo) {
      if (userData.subscription) {
        subscriptionInfo.innerHTML = `
          <strong>${userData.subscription.plan_name || 'Unknown Plan'}</strong><br>
          Status: ${userData.subscription.is_active ? 'Active' : 'Inactive'}<br>
          Expires: ${userData.subscription.expires_at ? new Date(userData.subscription.expires_at).toLocaleString() : 'Never'}<br>
          Auto-renew: ${userData.subscription.auto_renew ? 'Yes' : 'No'}
        `;
      } else {
        subscriptionInfo.innerHTML = '<em>No active subscription</em>';
      }
    }
  } catch (error) {
    console.error('Failed to load user subscription info:', error);
    const subscriptionInfo = document.getElementById(IDS.currentSubscription);
    if (subscriptionInfo) {
      subscriptionInfo.innerHTML = '<em>Failed to load subscription info</em>';
    }
  }
  
  // Show the modal
  const modal = document.getElementById(IDS.assignModal);
  if (modal) modal.style.display = 'flex';
}

export function closeAssignSubscriptionModal() {
  const modal = document.getElementById(IDS.assignModal);
  if (modal) modal.style.display = 'none';
  
  // Reset form
  const select = document.getElementById(IDS.planSelect);
  const trialDays = document.getElementById(IDS.trialDays);
  const autoRenew = document.getElementById(IDS.autoRenew);
  const cancelExisting = document.getElementById(IDS.cancelExisting);
  const notes = document.getElementById(IDS.notes);
  
  if (select) select.value = '';
  if (trialDays) trialDays.value = '';
  if (autoRenew) autoRenew.checked = true;
  if (cancelExisting) cancelExisting.checked = true;
  if (notes) notes.value = '';
}

export async function assignSubscription() {
  const username = document.getElementById(IDS.assignUsername)?.textContent;
  const planId = document.getElementById(IDS.planSelect)?.value;
  const trialDays = document.getElementById(IDS.trialDays)?.value;
  const autoRenew = document.getElementById(IDS.autoRenew)?.checked;
  const cancelExisting = document.getElementById(IDS.cancelExisting)?.checked;
  const notes = document.getElementById(IDS.notes)?.value.trim();
  
  if (!username) {
    alert('Username not found');
    return;
  }
  
  if (!planId) {
    alert('Please select a subscription plan');
    return;
  }
  
  try {
    const response = await fetch(`/api/users/${username}/subscription`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        plan_id: parseInt(planId),
        trial_days: trialDays ? parseInt(trialDays) : undefined,
        auto_renew: autoRenew,
        cancel_existing: cancelExisting,
        notes: notes || undefined,
      }),
    });
    
    const data = await response.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
    } else {
      alert('Subscription assigned successfully');
      closeAssignSubscriptionModal();
      refreshUsers();
    }
  } catch (error) {
    console.error('Failed to assign subscription:', error);
    alert('Failed to assign subscription');
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('dashboard:user-management-visible', () => refreshUsers());
  document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('user-management');
    if (section && section.classList.contains('active')) {
      refreshUsers();
    }
  });

  Object.assign(window, {
    refreshUsers,
    showAddUserModal,
    closeAddUserModal,
    addNewUser,
    deleteUser,
    editUser,
    assignSubscriptionToUser,
    closeAssignSubscriptionModal,
    assignSubscription,
  });
}
