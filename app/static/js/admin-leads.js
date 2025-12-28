(function () {
  const table = document.querySelector('[data-leads-table]');
  const api = document.body?.dataset?.leadsApi;
  if (!table || !api) {
    return;
  }

  const formatDate = (value) => {
    if (!value) {
      return '—';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  };

  const renderRows = (leads) => {
    if (!Array.isArray(leads) || leads.length === 0) {
      table.innerHTML = '<tr><td colspan="7">No leads captured yet.</td></tr>';
      return;
    }
    const rows = leads
      .map(
        (lead) => `
        <tr>
          <td>${lead.name || ''}</td>
          <td>${lead.email || ''}</td>
          <td>${lead.company || '—'}</td>
          <td><span class="status-pill">${lead.status || 'new'}</span></td>
          <td>${lead.source || 'marketing_form'}</td>
          <td>${formatDate(lead.created_at)}</td>
          <td>${lead.message ? lead.message.slice(0, 64) + (lead.message.length > 64 ? '…' : '') : '—'}</td>
        </tr>`
      )
      .join('');
    table.innerHTML = rows;
  };

  const refresh = async () => {
    try {
      const response = await fetch(api, { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error('Unable to load leads');
      }
      const payload = await response.json();
      renderRows(payload.leads || []);
    } catch (error) {
      console.warn(error);
    }
  };

  refresh();
  setInterval(refresh, 60 * 1000);
})();
