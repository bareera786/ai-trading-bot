// PHASE 6: MODEL HEALTH MONITOR JAVASCRIPT
// Add these functions to the <script> section in brain_dashboard.html

// ===== HEALTH MONITORING FUNCTIONS =====

async function fetchHealthMetrics() {
    try {
        const res = await fetch(`${API_BASE}/performance/active`);
        if (!res.ok) {
            console.log('No active model or health data not available yet');
            return;
        }

        const data = await res.json();

        // Update health badge
        const badge = document.getElementById('healthBadge');
        if (badge) {
            badge.textContent = data.health_state;
            badge.style.padding = '4px 12px';
            badge.style.borderRadius = '12px';
            badge.style.fontSize = '0.75rem';
            badge.style.fontWeight = '700';
            badge.style.textTransform = 'uppercase';
            badge.style.letterSpacing = '0.5px';

            if (data.health_state === 'HEALTHY') {
                badge.style.background = 'rgba(0, 212, 170, 0.2)';
                badge.style.color = '#00d4aa';
                badge.style.border = '1px solid #00d4aa';
            } else if (data.health_state === 'DEGRADING') {
                badge.style.background = 'rgba(255, 193, 7, 0.2)';
                badge.style.color = '#ffc107';
                badge.style.border = '1px solid #ffc107';
            } else if (data.health_state === 'FAILING') {
                badge.style.background = 'rgba(225, 112, 85, 0.2)';
                badge.style.color = '#e17055';
                badge.style.border = '1px solid #e17055';
            } else {
                badge.style.background = 'rgba(108, 117, 125, 0.2)';
                badge.style.color = '#6c757d';
                badge.style.border = '1px solid #6c757d';
            }
        }

        // Update metrics
        if (data.metrics) {
            const winRate = document.getElementById('winRate7d');
            if (winRate) {
                winRate.textContent = ((data.metrics.win_rate_7d || 0) * 100).toFixed(1) + '%';
            }

            const avgConf = document.getElementById('avgConfidence');
            if (avgConf) {
                avgConf.textContent = ((data.metrics.avg_confidence_7d || 0) * 100).toFixed(1) + '%';
            }

            const drawdown = document.getElementById('currentDrawdown');
            if (drawdown) {
                drawdown.textContent = (data.metrics.current_drawdown_pct || 0).toFixed(1) + '%';
            }

            const streak = document.getElementById('lossStreak');
            if (streak) {
                streak.textContent = data.metrics.consecutive_losses || 0;
            }

            const score = document.getElementById('healthScore');
            if (score) {
                score.textContent = ((data.health_score || 0) * 100).toFixed(0) + '/100';
            }

            // Update bias chart
            const biasLong = document.getElementById('biasLong');
            const biasShort = document.getElementById('biasShort');
            const biasFlat = document.getElementById('biasFlat');

            if (biasLong && biasShort && biasFlat && data.metrics.signal_bias) {
                const longPct = (data.metrics.signal_bias.long || 0.33) * 100;
                const shortPct = (data.metrics.signal_bias.short || 0.33) * 100;
                const flatPct = (data.metrics.signal_bias.flat || 0.34) * 100;

                biasLong.style.width = longPct + '%';
                biasShort.style.width = shortPct + '%';
                biasFlat.style.width = flatPct + '%';
            }
        }

        // Update last check time
        if (data.last_check) {
            const lastCheck = document.getElementById('lastCheck');
            if (lastCheck) {
                lastCheck.textContent = new Date(data.last_check).toLocaleTimeString();
            }
        }

        // Show auto-pause warning if active
        const warning = document.getElementById('autoPauseWarning');
        if (data.auto_paused && warning) {
            warning.style.display = 'block';
            const reason = document.getElementById('autoPauseReason');
            if (reason) {
                reason.textContent = data.auto_pause_reason;
            }
        } else if (warning) {
            warning.style.display = 'none';
        }

    } catch (e) {
        console.error('Failed to fetch health metrics:', e);
    }
}

async function manualResume() {
    const confirmed = confirm(
        '⚠️ MANUAL OVERRIDE WARNING\n\n' +
        'You are about to manually resume signals after an automatic pause.\n\n' +
        'The watchdog detected a problem with the model and paused signals for your protection.\n\n' +
        'Are you ABSOLUTELY SURE you want to override this safety measure?\n\n' +
        'You will need to monitor the system very closely after resuming.'
    );

    if (!confirmed) return;

    const phrase = prompt('Enter confirmation phrase exactly as shown:\n\nMANUAL OVERRIDE CONFIRMED');
    if (phrase !== 'MANUAL OVERRIDE CONFIRMED') {
        alert('❌ Incorrect confirmation phrase. Override cancelled.');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/watchdog/resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmation_phrase: phrase })
        });

        const data = await res.json();

        if (res.ok) {
            alert('✅ ' + data.message + '\n\nSignals have been resumed. Monitor the system closely!');
            fetchHealthMetrics();
            fetchStatus();
        } else {
            alert('❌ Error: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('❌ Network error: ' + e.message);
    }
}

// ===== INITIALIZATION =====

// Add to existing DOMContentLoaded event
document.addEventListener('DOMContentLoaded', () => {
    // ... existing initialization code ...

    // Phase 6: Start health monitoring
    fetchHealthMetrics();
    setInterval(fetchHealthMetrics, 10000);  // Poll every 10 seconds
});
