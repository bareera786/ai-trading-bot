(function () {
  const form = document.querySelector('[data-lead-form]');
  if (!form) {
    return;
  }

  const endpoint = form.dataset.leadEndpoint || '/api/leads';
  const statusEl = form.querySelector('[data-lead-status]');

  const setStatus = (message, variant) => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = message || '';
    statusEl.classList.remove('success', 'error');
    if (variant) {
      statusEl.classList.add(variant);
    }
  };

  const serialize = () => {
    const payload = {};
    const formData = new FormData(form);
    formData.forEach((value, key) => {
      payload[key] = value.toString();
    });
    return payload;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus('Submitting your request…', '');

    try {
      const payload = serialize();
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const err = new Error(body.error || 'Unable to submit request');
        if (body.retry_after_seconds) {
          err.retryAfter = body.retry_after_seconds;
        }
        throw err;
      }

      form.reset();
      setStatus('Thanks! Our team will follow up shortly.', 'success');
    } catch (error) {
      const retry = error?.retryAfter;
      let message = error?.message || 'Submission failed. Please email us directly.';
      if (retry) {
        message += ` Try again in ${retry} seconds.`;
      }
      setStatus(message, 'error');
    }
  });
})();
