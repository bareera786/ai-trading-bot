
/**
 * Industrial-Grade Admin User Management
 * Handles fetching, rendering, filtering, and interactions for the user management grid.
 */

// State
let usersData = [];
let currentFilter = 'all'; // all, active, inactive, admin

export function initUserManagement() {
    const tableBody = document.getElementById('user-table-body');
    const searchInput = document.getElementById('user-search-input');
    const refreshBtn = document.getElementById('user-refresh-btn');
    const filterSelect = document.getElementById('user-filter-select');

    if (!tableBody) return; // Feature not present on page

    // Initial Load
    fetchUsers();

    // Event Listeners
    if (searchInput) {
        searchInput.addEventListener('input', (e) => filterUsers(e.target.value));
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchUsers);
    }

    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => {
            currentFilter = e.target.value;
            filterUsers(searchInput ? searchInput.value : '');
        });
    }

    // Modal Events (delegated from global scope if needed, or bound here)
    window.handleToggleUser = handleToggleUser;
    window.handleEditUser = handleEditUser;
    window.handleDeleteUser = handleDeleteUser;
}

/**
 * Fetch users from the consolidated backend API
 */
async function fetchUsers() {
    const tableBody = document.getElementById('user-table-body');
    const loadingState = document.getElementById('user-loading-state');

    if (loadingState) loadingState.style.display = 'block';
    if (tableBody) tableBody.innerHTML = '';

    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('Failed to load users');

        const data = await response.json();
        usersData = data.users || [];

        renderUsers(usersData);
        updateStats(usersData);

    } catch (error) {
        console.error('User fetch error:', error);
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="7" class="text-error text-center">Failed to load users: ${error.message}</td></tr>`;
        }
    } finally {
        if (loadingState) loadingState.style.display = 'none';
    }
}

/**
 * Render the user grid
 */
function renderUsers(users) {
    const tableBody = document.getElementById('user-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';

    if (users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No users found matching criteria.</td></tr>';
        return;
    }

    users.forEach(user => {
        const row = document.createElement('tr');

        // Status Badge
        const statusClass = user.is_active ? 'status-success' : 'status-danger';
        const statusText = user.is_active ? 'Active' : 'Banned';

        // Role Badge
        const roleClass = user.is_admin ? 'badge-primary' : 'badge-secondary';
        const roleText = user.is_admin ? 'ADMIN' : 'USER';

        // Plan Info
        const planCode = user.subscription?.plan?.code || 'Free';

        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never';
        const joined = new Date(user.created_at).toLocaleDateString();

        row.innerHTML = `
            <td>
                <div style="font-weight: 600; color: var(--text-primary);">${user.username}</div>
                <div style="font-size: 0.8em; color: var(--text-secondary);">${user.email}</div>
                <div style="font-size: 0.7em; color: var(--text-muted);">Joined: ${joined}</div>
            </td>
            <td><span class="badge ${roleClass}">${roleText}</span></td>
            <td><span class="status-indicator ${statusClass}">${statusText}</span></td>
            <td><code style="color:var(--accent-primary);">${planCode}</code></td>
            <td style="font-size:0.85em; color:var(--text-secondary);">${lastLogin}</td>
            <td class="text-right">$${formatMoney(user.portfolio.balance)}</td>
            <td class="text-center">${user.stats.trade_count}</td>
            <td class="text-right">
                <button class="btn-icon" onclick="handleEditUser('${user.id}')" title="Edit">✏️</button>
                <button class="btn-icon" onclick="handleToggleUser('${user.id}')" title="${user.is_active ? 'Deactivate' : 'Activate'}">
                    ${user.is_active ? '🛑' : '✅'}
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function formatMoney(value) {
    return Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Filter users based on search text and status dropdown
 */
function filterUsers(searchTerm) {
    const lowerTerm = searchTerm.toLowerCase();

    const filtered = usersData.filter(user => {
        // Text Match
        const matchesText = user.username.toLowerCase().includes(lowerTerm) ||
            user.email.toLowerCase().includes(lowerTerm);

        // Status Match
        let matchesFilter = true;
        if (currentFilter === 'active') matchesFilter = user.is_active;
        if (currentFilter === 'inactive') matchesFilter = !user.is_active;
        if (currentFilter === 'admin') matchesFilter = user.is_admin;

        return matchesText && matchesFilter;
    });

    renderUsers(filtered);
}

function updateStats(users) {
    const totalEl = document.getElementById('total-users-count');
    const activeEl = document.getElementById('active-users-count');

    if (totalEl) totalEl.textContent = users.length;
    if (activeEl) activeEl.textContent = users.filter(u => u.is_active).length;
}

// ------------------------------------------------------------------
// Actions
// ------------------------------------------------------------------

async function handleToggleUser(userId) {
    if (!confirm("Are you sure you want to toggle this user's status?")) return;

    try {
        const response = await fetch(`/api/admin/users/${userId}/toggle-active`, { method: 'POST' });
        const result = await response.json();

        if (result.success) {
            // Optimistic update or refresh
            const user = usersData.find(u => u.id === userId);
            if (user) user.is_active = result.is_active;

            // Re-render filtering
            const searchInput = document.getElementById('user-search-input');
            filterUsers(searchInput ? searchInput.value : '');

            // Notify
            // alert(result.is_active ? "User Activated" : "User Deactivated");
        } else {
            alert(result.error);
        }
    } catch (e) {
        alert("Action failed: " + e.message);
    }
}

async function handleDeleteUser(userId) {
    if (!confirm("CRITICAL WARNING: This will permanently delete the user and all their data?")) return;

    // ... impl
}

async function handleEditUser(userId) {
    if (window.handleEditUser) {
        window.handleEditUser(userId);
    } else {
        console.error("Global handleEditUser not found");
        alert("Edit feature not fully initialized");
    }
}
