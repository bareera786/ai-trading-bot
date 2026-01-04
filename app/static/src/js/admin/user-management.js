// Professional user management JS

document.addEventListener('DOMContentLoaded', function() {
    const userListDiv = document.getElementById('userList');
    const userDetailsDiv = document.getElementById('userDetails');
    const userSearch = document.getElementById('userSearch');

    function fetchUsers(query = '') {
        fetch(`/api/users?search=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => renderUserList(data.users));
    }

    function renderUserList(users) {
        let html = `<table class='table table-striped'><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Balance</th><th>Portfolio</th><th>Trades</th><th>Subscription</th><th>Status</th><th>Actions</th></tr></thead><tbody>`;
        for (const user of users) {
            html += `<tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.balance ?? 'N/A'}</td>
                <td>${user.portfolio_value ?? 'N/A'}</td>
                <td>${user.trade_count ?? 'N/A'}</td>
                <td>${user.subscription_expiry ?? 'N/A'}<br><small>${user.subscription_history ? user.subscription_history.map(s => `${s.plan} (${s.start} - ${s.end})`).join('<br>') : ''}</small></td>
                <td>${user.is_active ? 'Active' : 'Disabled'}</td>
                <td>
                    <button class='btn btn-sm btn-info' onclick='viewUser(${user.id})'>View/Edit</button>
                    <button class='btn btn-sm btn-warning' onclick='toggleUser(${user.id}, ${user.is_active})'>${user.is_active ? 'Disable' : 'Enable'}</button>
                </td>
            </tr>`;
        }
        html += '</tbody></table>';
        userListDiv.innerHTML = html;
    }

    window.viewUser = function(id) {
        fetch(`/api/users/${id}`)
            .then(res => res.json())
            .then(user => {
                userDetailsDiv.style.display = 'block';
                userDetailsDiv.innerHTML = `
                    <div class='card'>
                        <div class='card-body'>
                            <h4>User Profile</h4>
                            <p><strong>ID:</strong> ${user.id}</p>
                            <p><strong>Name:</strong> ${user.username}</p>
                            <p><strong>Email:</strong> ${user.email}</p>
                            <p><strong>Balance:</strong> ${user.balance ?? 'N/A'}</p>
                            <p><strong>Portfolio Value:</strong> ${user.portfolio_value ?? 'N/A'}</p>
                            <p><strong>Trade Count:</strong> ${user.trade_count ?? 'N/A'}</p>
                            <p><strong>Subscription Expiry:</strong> ${user.subscription_expiry ?? 'N/A'}</p>
                            <p><strong>Subscription History:</strong><br>${user.subscription_history ? user.subscription_history.map(s => `${s.plan} (${s.start} - ${s.end})`).join('<br>') : 'N/A'}</p>
                            <p><strong>Status:</strong> ${user.is_active ? 'Active' : 'Disabled'}</p>

                            <hr>
                            <h5>Subscription Controls</h5>
                            <div class='row g-2'>
                                <div class='col-md-4'>
                                    <label class='form-label'>Plan Code</label>
                                    <input id='sub-plan-code' class='form-control' value='pro-monthly' placeholder='pro-monthly'>
                                </div>
                                <div class='col-md-4'>
                                    <label class='form-label'>Grant Days (optional)</label>
                                    <input id='sub-grant-days' class='form-control' placeholder='e.g. 30'>
                                </div>
                                <div class='col-md-4'>
                                    <label class='form-label'>Grant Notes (optional)</label>
                                    <input id='sub-grant-notes' class='form-control' placeholder='Admin-granted access'>
                                </div>
                            </div>
                            <div class='mt-2' style='display:flex; gap:8px; flex-wrap:wrap;'>
                                <button class='btn btn-success' onclick='grantSubscription(${user.id})'>Grant / Replace Subscription</button>
                            </div>
                            <div class='row g-2 mt-2'>
                                <div class='col-md-4'>
                                    <label class='form-label'>Extend Days</label>
                                    <input id='sub-extend-days' class='form-control' placeholder='e.g. 7'>
                                </div>
                                <div class='col-md-8'>
                                    <label class='form-label'>Extend Notes (optional)</label>
                                    <input id='sub-extend-notes' class='form-control' placeholder='Reason for extension'>
                                </div>
                            </div>
                            <div class='mt-2' style='display:flex; gap:8px; flex-wrap:wrap;'>
                                <button class='btn btn-warning' onclick='extendSubscription(${user.id})'>Extend Active Subscription</button>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <button class='btn btn-primary' onclick='editUser(${user.id})'>Edit</button>
                                <button class='btn btn-secondary' onclick='openManageUserKeys(${user.id})'>Manage API Keys</button>
                            </div>
                        </div>
                    </div>
                `;
            });
    }

    window.grantSubscription = async function(userId) {
        const plan_code = (document.getElementById('sub-plan-code')?.value || 'pro-monthly').trim();
        const daysRaw = (document.getElementById('sub-grant-days')?.value || '').trim();
        const notes = (document.getElementById('sub-grant-notes')?.value || '').trim();

        const payload = { plan_code };
        if (daysRaw) payload.days = daysRaw;
        if (notes) payload.notes = notes;

        try {
            const resp = await fetch(`/api/users/${userId}/subscription/grant`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const json = await resp.json();
            if (!resp.ok) {
                alert(json?.error || 'Failed to grant subscription');
                return;
            }
            alert('Subscription granted');
            fetchUsers(userSearch.value);
            viewUser(userId);
        } catch (err) {
            alert('Failed to grant subscription: ' + err);
        }
    }

    window.extendSubscription = async function(userId) {
        const daysRaw = (document.getElementById('sub-extend-days')?.value || '').trim();
        const notes = (document.getElementById('sub-extend-notes')?.value || '').trim();
        if (!daysRaw) {
            alert('Extend days is required');
            return;
        }
        const payload = { days: daysRaw };
        if (notes) payload.notes = notes;

        try {
            const resp = await fetch(`/api/users/${userId}/subscription/extend`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const json = await resp.json();
            if (!resp.ok) {
                alert(json?.error || 'Failed to extend subscription');
                return;
            }
            alert('Subscription extended');
            fetchUsers(userSearch.value);
            viewUser(userId);
        } catch (err) {
            alert('Failed to extend subscription: ' + err);
        }
    }

    // Admin: Manage user API keys
    window.openManageUserKeys = function(userId) {
        // Open admin modal prefilled with user's existing credentials
        fetch(`/api/users/${userId}/credentials`)
            .then(res => res.json())
            .then(data => {
                const creds = data.credentials || {};
                const spot = creds.spot || {};
                const futures = creds.futures || {};

                // Prefill modal inputs
                document.getElementById('admin-api-account-type').value = 'spot';
                document.getElementById('admin-api-key').value = spot.api_key || '';
                document.getElementById('admin-api-secret').value = spot.api_secret || '';
                document.getElementById('admin-api-testnet').checked = !!spot.testnet;
                document.getElementById('admin-user-keys-modal').dataset.userId = userId;
                document.getElementById('admin-user-keys-modal').style.display = 'flex';
            })
            .catch(err => alert('Failed to load user credentials: ' + err));
    }

    // Wire modal buttons
    document.addEventListener('DOMContentLoaded', function() {
        const testBtn = document.getElementById('admin-api-test-btn');
        const saveBtn = document.getElementById('admin-api-save-btn');

        if (testBtn) {
            testBtn.addEventListener('click', async function() {
                const apiKey = document.getElementById('admin-api-key').value.trim();
                const apiSecret = document.getElementById('admin-api-secret').value.trim();
                const testnet = document.getElementById('admin-api-testnet').checked;
                if (!apiKey || !apiSecret) { alert('API key and secret are required to test'); return; }
                try {
                    const resp = await fetch(`/api/users/${document.getElementById('admin-user-keys-modal').dataset.userId}/credentials/test`, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({apiKey, apiSecret, testnet})
                    });
                    const json = await resp.json();
                    if (json.connected) alert('Credentials validated successfully (connected)');
                    else if (json.error) alert('Validation failed: ' + json.error);
                    else alert('Validation result: ' + JSON.stringify(json));
                } catch (err) { alert('Failed to test API key: ' + err); }
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', async function() {
                const apiKey = document.getElementById('admin-api-key').value.trim();
                const apiSecret = document.getElementById('admin-api-secret').value.trim();
                const testnet = document.getElementById('admin-api-testnet').checked;
                const accountType = document.getElementById('admin-api-account-type').value || 'spot';
                const userId = document.getElementById('admin-user-keys-modal').dataset.userId;
                if (!apiKey || !apiSecret) { alert('API key and secret are required'); return; }
                try {
                    const resp = await fetch(`/api/users/${userId}/credentials`, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({apiKey, apiSecret, accountType, testnet})
                    });
                    const json = await resp.json();
                    if (json.saved) { alert('Saved'); document.getElementById('admin-user-keys-modal').style.display = 'none'; fetchUsers(userSearch.value); viewUser(userId); }
                    else alert('Save failed: ' + JSON.stringify(json));
                } catch (err) { alert('Failed to save: ' + err); }
            });
        }
    });

    window.removeUserKey = function(userId) {
        if (!confirm('Remove all API keys for this user?')) return;
        fetch(`/api/users/${userId}/credentials`, { method: 'DELETE' })
        .then(res => res.json())
        .then(() => { alert('Removed'); fetchUsers(userSearch.value); viewUser(userId); })
        .catch(err => alert('Failed to remove: ' + err));
    }

    window.editUser = function(id) {
        fetch(`/api/users/${id}`)
            .then(res => res.json())
            .then(user => {
                userDetailsDiv.innerHTML = `
                    <div class='card'>
                        <div class='card-body'>
                            <h4>Edit User Profile</h4>
                            <form id='editUserForm'>
                                <div class='mb-2'><label>Name</label><input class='form-control' name='username' value='${user.username}'></div>
                                <div class='mb-2'><label>Email</label><input class='form-control' name='email' value='${user.email}'></div>
                                <div class='mb-2'><label>Balance</label><input class='form-control' name='balance' value='${user.balance ?? ''}'></div>
                                <div class='mb-2'><label>Portfolio Value</label><input class='form-control' name='portfolio_value' value='${user.portfolio_value ?? ''}'></div>
                                <div class='mb-2'><label>Trade Count</label><input class='form-control' name='trade_count' value='${user.trade_count ?? ''}'></div>
                                <div class='mb-2'><label>Subscription Expiry</label><input class='form-control' name='subscription_expiry' value='${user.subscription_expiry ?? ''}'></div>
                                <div class='mb-2'><label>Subscription History (JSON)</label><textarea class='form-control' name='subscription_history'>${user.subscription_history ? JSON.stringify(user.subscription_history) : ''}</textarea></div>
                                <button type='submit' class='btn btn-success'>Save</button>
                            </form>
                        </div>
                    </div>
                `;
                document.getElementById('editUserForm').onsubmit = function(e) {
                    e.preventDefault();
                    const form = e.target;
                    let subscription_history = form.subscription_history.value;
                    try { subscription_history = JSON.parse(subscription_history); } catch { subscription_history = null; }
                    const data = {
                        username: form.username.value,
                        email: form.email.value,
                        balance: form.balance.value,
                        portfolio_value: form.portfolio_value.value,
                        trade_count: form.trade_count.value,
                        subscription_expiry: form.subscription_expiry.value,
                        subscription_history
                    };
                    fetch(`/api/users/${id}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    })
                    .then(res => res.json())
                    .then(() => {
                        fetchUsers(userSearch.value);
                        viewUser(id);
                    });
                };
            });
    }

    window.toggleUser = function(id, isActive) {
        fetch(`/api/users/${id}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({is_active: !isActive})
        })
        .then(res => res.json())
        .then(() => fetchUsers(userSearch.value));
    }

    userSearch.addEventListener('input', function() {
        fetchUsers(this.value);
    });

    fetchUsers();
});
