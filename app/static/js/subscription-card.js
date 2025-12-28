(function () {
  const cards = document.querySelectorAll('[data-subscription-card]');
  if (!cards.length) {
    return;
  }

  const plansUrl = document.body?.dataset?.subscriptionPlansUrl || '/api/subscriptions/plans';

  const normalizeKey = (value) => (value || '').toString().trim().toLowerCase();

  const formatTerm = (planType) => {
    switch (normalizeKey(planType)) {
      case 'trial':
        return 'trial period';
      case 'yearly':
        return 'year';
      case 'lifetime':
        return 'lifetime access';
      default:
        return 'month';
    }
  };

  const formatBadge = (plan) => {
    if (!plan) {
      return 'Most popular';
    }
    if (!plan.is_active) {
      return 'Unavailable';
    }
    if (normalizeKey(plan.plan_type) === 'trial') {
      return 'Free pilot';
    }
    if (plan.is_featured) {
      return 'Featured plan';
    }
    return 'Active plan';
  };

  const formatDuration = (days) => {
    if (!days) {
      return 'Rolling access';
    }
    if (days % 30 === 0) {
      const months = Math.round(days / 30);
      return `${months}-month cycles`;
    }
    return `${days}-day cycles`;
  };

  const updateCard = (card, plan) => {
    if (!plan) {
      return;
    }
    const nameEl = card.querySelector('[data-plan-name]');
    const badgeEl = card.querySelector('[data-plan-badge]');
    const priceEl = card.querySelector('[data-plan-price]');
    const termEl = card.querySelector('[data-plan-term]');
    const subtextEl = card.querySelector('[data-plan-subtext]');
    const durationEl = card.querySelector('[data-plan-duration]');
    const trialEl = card.querySelector('[data-plan-trial]');

    if (nameEl) {
      nameEl.textContent = plan.name;
    }
    if (badgeEl) {
      badgeEl.textContent = formatBadge(plan);
    }
    if (priceEl) {
      const formatter = new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: plan.currency || 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });
      priceEl.textContent = formatter.format(Number(plan.price_usd || 0));
    }
    if (termEl) {
      const label = formatTerm(plan.plan_type);
      termEl.textContent = `/${label}`;
    }
    if (durationEl) {
      durationEl.textContent = formatDuration(Number(plan.duration_days));
    }
    if (trialEl) {
      const trial = Number(plan.trial_days || 0);
      trialEl.textContent = trial > 0 ? `${trial}-day pilot` : 'Cancel anytime';
    }
    if (subtextEl) {
      const trialText = plan.trial_days ? `${plan.trial_days}-day pilot included.` : 'Cancel anytime.';
      subtextEl.textContent = plan.description || trialText;
    }
    card.classList.add('subscription-card--loaded');
  };

  const buildPlanIndex = (plans = []) => {
    const index = new Map();
    plans.forEach((plan) => {
      const codeKey = normalizeKey(plan.code);
      if (codeKey) {
        index.set(codeKey, plan);
      }
      const typeKey = normalizeKey(plan.plan_type);
      if (typeKey && !index.has(typeKey)) {
        index.set(typeKey, plan);
      }
      if (plan.tier) {
        const tierKey = normalizeKey(plan.tier);
        if (tierKey && !index.has(tierKey)) {
          index.set(tierKey, plan);
        }
      }
    });
    return index;
  };

  const resolvePlanForCard = (card, { featured, index, fallback }) => {
    const dataset = card.dataset || {};
    const codeKey = normalizeKey(dataset.planCode);
    const tierKey = normalizeKey(dataset.planTier);

    if (codeKey && index.has(codeKey)) {
      return index.get(codeKey);
    }
    if (tierKey && index.has(tierKey)) {
      return index.get(tierKey);
    }
    const featuredKey = featured ? normalizeKey(featured.code) : null;
    if (featuredKey && index.has(featuredKey)) {
      return index.get(featuredKey);
    }
    return featured || fallback;
  };

  const loadPlans = async () => {
    try {
      const response = await fetch(plansUrl, { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error('Failed to load plans');
      }
      const payload = await response.json();
      const plans = payload.plans || [];
      const featuredPlan = payload.featured_plan || null;
      const planIndex = buildPlanIndex(plans);
      const fallbackPlan = featuredPlan || plans[0] || null;

      cards.forEach((card) => {
        const planForCard = resolvePlanForCard(card, {
          featured: featuredPlan,
          index: planIndex,
          fallback: fallbackPlan,
        });
        updateCard(card, planForCard);
      });
    } catch (error) {
      console.warn('Subscription plan data unavailable. Falling back to defaults.', error);
    }
  };

  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(loadPlans);
  } else {
    window.addEventListener('DOMContentLoaded', loadPlans);
  }
})();
