
// Subscription Management Logic

export function initSubscriptionManagement() {
    const tableBody = document.getElementById('subscription-plans-table');
    if (!tableBody) return; // Not an admin or section missing

    refreshPlans();
}

window.refreshPlans = async function () {
    const tableBody = document.getElementById('subscription-plans-table');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading plans...</td></tr>';

    try {
        const response = await fetch('/api/admin/subscription/plans');
        if (!response.ok) throw new Error('Failed to load plans');

        const data = await response.json();
        const plans = data.plans || [];

        renderPlans(plans);
    } catch (error) {
        console.error('Error loading plans:', error);
        tableBody.innerHTML = `<tr><td colspan="6" class="text-error">Error loading plans: ${error.message}</td></tr>`;
    }
};

function renderPlans(plans) {
    const tableBody = document.getElementById('subscription-plans-table');
    tableBody.innerHTML = '';

    if (plans.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No subscription plans found.</td></tr>';
        return;
    }

    plans.forEach(plan => {
        const row = document.createElement('tr');
        const statusClass = plan.is_active ? 'status-success' : 'status-warning';
        const statusText = plan.is_active ? 'Active' : 'Inactive';

        row.innerHTML = `
            <td>
                <div style="font-weight: 600; color: var(--text-primary);">${plan.name}</div>
                <div style="font-size: 0.8em; color: var(--text-secondary);">${plan.description || ''}</div>
            </td>
            <td><code>${plan.code}</code></td>
            <td>$${plan.price_usd}</td>
            <td><span class="badge badge-info">${plan.access_level}</span></td>
            <td><span class="status-indicator ${statusClass}">${statusText}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editPlan(${plan.id})">Edit</button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Modal Management
window.showAddPlanModal = function () {
    const modal = document.getElementById('add-plan-modal');
    const form = document.getElementById('add-plan-form');
    if (modal && form) {
        form.reset();
        modal.style.display = 'flex';
    }
};

window.closePlanModal = function (type) {
    const modal = document.getElementById(`${type}-plan-modal`);
    if (modal) {
        modal.style.display = 'none';
    }
};

// Create Plan
window.savePlan = async function (event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Checkbox handling
    data.is_featured = form.querySelector('[name="is_featured"]').checked;
    data.is_active = form.querySelector('[name="is_active"]').checked;

    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerText;
    btn.innerText = 'Creating...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/admin/subscription/plans', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrf_token || ''
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to create plan');
        }

        alert('Plan created successfully!');
        window.closePlanModal('add');
        window.refreshPlans();
    } catch (error) {
        alert(error.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
};

// Edit Plan
window.editPlan = async function (id) {
    try {
        // Find plan from local cache or re-fetch (simplest is finding from DOM or re-fetch list)
        // For simplicity, we'll re-fetch the list logic or assume we render data attributes.
        // Better: let's fetch the plan details if needed, or iterate the active `plans` variable if we had it globally.
        // Since `plans` is local to `refreshPlans`, we'll just fetch list again? No, inefficient.
        // Let's attach full plan data to the Edit button for easy access.
        const btn = document.querySelector(`button[onclick="editPlan(${id})"]`);
        if (!btn) return;

        // Hack: We stored plan data in the row? No. 
        // Let's just fetch the list to find it (fast enough) or fetch individual plan if endpoint exists.
        // The implementation_plan suggests just basic edit. Let's assume we can fetch list and filter.

        const response = await fetch('/api/admin/subscription/plans');
        const data = await response.json();
        const plan = data.plans.find(p => p.id === id);

        if (!plan) throw new Error("Plan not found");

        const modal = document.getElementById('edit-plan-modal');
        const form = document.getElementById('edit-plan-form');

        form.querySelector('[name="plan_id"]').value = plan.id;
        form.querySelector('[name="name"]').value = plan.name;
        form.querySelector('[name="code"]').value = plan.code;
        form.querySelector('[name="price_usd"]').value = plan.price_usd;
        form.querySelector('[name="duration_days"]').value = plan.duration_days;
        form.querySelector('[name="trial_days"]').value = plan.trial_days;
        form.querySelector('[name="description"]').value = plan.description || '';
        form.querySelector('[name="is_featured"]').checked = plan.is_featured;
        form.querySelector('[name="is_active"]').checked = plan.is_active;

        modal.style.display = 'flex';
    } catch (e) {
        console.error(e);
        alert("Failed to load plan details.");
    }
};

window.updatePlan = async function (event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    const id = data.plan_id;

    data.is_featured = form.querySelector('[name="is_featured"]').checked;
    data.is_active = form.querySelector('[name="is_active"]').checked;

    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerText;
    btn.innerText = 'Saving...';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/admin/subscription/plans/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrf_token || ''
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to update plan');
        }

        alert('Plan updated successfully!');
        window.closePlanModal('edit');
        window.refreshPlans();
    } catch (error) {
        alert(error.message);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
};
