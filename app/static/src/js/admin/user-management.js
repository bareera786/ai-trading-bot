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
                            <button class='btn btn-primary' onclick='editUser(${user.id})'>Edit</button>
                        </div>
                    </div>
                `;
            });
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
