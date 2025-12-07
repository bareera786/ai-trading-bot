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
};

function updateCount(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

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
        <td>${user.last_login || 'Never'}</td>
        <td>${user.created_at || 'Unknown'}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 12px; margin-right: 4px;" onclick="editUser('${user.username}')">Edit</button>
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
  alert(`Edit user functionality for "${username}" coming soon.`);
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
  });
}
