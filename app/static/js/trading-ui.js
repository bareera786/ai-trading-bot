/**
 * Premium Trading UI Module
 * Handles real-time updates, animations, and interactions for trading pages
 */

class TradingUI {
    constructor(config = {}) {
        this.config = {
            pollInterval: config.pollInterval || 5000,
            animationDuration: config.animationDuration || 300,
            maxLogEntries: config.maxLogEntries || 50,
            ...config
        };

        this.isPolling = false;
        this.pollTimer = null;
        this.logContainer = null;
    }

    /**
     * Initialize the trading UI
     */
    init() {
        this.logContainer = document.getElementById('ai-logs') || document.getElementById('console-logs');
        this.startPolling();
        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Handle visibility change to pause/resume polling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });
    }

    /**
     * Start polling for updates
     */
    startPolling() {
        if (this.isPolling) return;
        this.isPolling = true;
        this.poll();
    }

    /**
     * Stop polling
     */
    stopPolling() {
        this.isPolling = false;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }

    /**
     * Poll for status updates
     */
    async poll() {
        if (!this.isPolling) return;

        try {
            await this.updateStatus();
        } catch (error) {
            console.error('Poll failed:', error);
        }

        if (this.isPolling) {
            this.pollTimer = setTimeout(() => this.poll(), this.config.pollInterval);
        }
    }

    /**
     * Update status from API
     * Override this in subclasses
     */
    async updateStatus() {
        // To be implemented by specific trading page
    }

    /**
     * Add log entry to console
     */
    addLog(tag, message, level = 'info') {
        if (!this.logContainer) return;

        const time = new Date().toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        // Check if we are inserting into a table body
        if (this.logContainer.tagName === 'TBODY') {
            const row = document.createElement('tr');
            row.className = 'log-entry-new'; // Add animation class if needed

            // Map to 5 columns: Time, Event, Symbol, Confidence, Action
            // Usage: addLog('SYSTEM', 'Message', 'success')
            // Time = time
            // Event = tag (SYSTEM)
            // Symbol = -
            // Confidence = - 
            // Action = message

            let symbol = '-';
            let confidence = '-';

            // Basic heuristic to parse message if needed, but keeping it simple for now

            row.innerHTML = `
                <td style="color: var(--text-secondary); font-size: 0.85rem;">${time}</td>
                <td><span class="console-tag console-tag-${level}">${tag}</span></td>
                <td>${symbol}</td>
                <td>${confidence}</td>
                <td style="color: var(--text-muted);">${this.escapeHtml(message)}</td>
            `;

            this.logContainer.insertBefore(row, this.logContainer.firstChild);

            // Limit rows
            while (this.logContainer.children.length > this.config.maxLogEntries) {
                this.logContainer.removeChild(this.logContainer.lastChild);
            }
        } else {
            // Default DIV behavior for non-table containers
            const entry = document.createElement('div');
            entry.className = 'console-entry';
            entry.innerHTML = `
                <span class="console-time">${time}</span>
                <span class="console-tag console-tag-${level}">${tag}</span>
                <span class="console-message">${this.escapeHtml(message)}</span>
            `;

            // Add to top of log
            this.logContainer.insertBefore(entry, this.logContainer.firstChild);

            // Limit number of entries
            while (this.logContainer.children.length > this.config.maxLogEntries) {
                this.logContainer.removeChild(this.logContainer.lastChild);
            }
        }
    }

    /**
     * Update status indicator
     */
    updateStatusIndicator(elementId, status, text) {
        const element = document.getElementById(elementId);
        if (!element) return;

        // Remove existing status classes
        element.classList.remove('text-success', 'text-warning', 'text-danger');

        // Add new status class and text
        switch (status) {
            case 'online':
            case 'active':
                element.classList.add('text-success');
                element.textContent = text || 'ONLINE';
                break;
            case 'paused':
            case 'warning':
                element.classList.add('text-warning');
                element.textContent = text || 'PAUSED';
                break;
            case 'offline':
            case 'error':
                element.classList.add('text-danger');
                element.textContent = text || 'OFFLINE';
                break;
            default:
                element.textContent = text || status;
        }

        // Trigger animation
        element.classList.add('updating');
        setTimeout(() => element.classList.remove('updating'), this.config.animationDuration);
    }

    /**
     * Animate counter/metric value
     */
    animateValue(elementId, start, end, duration = 1000) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const range = end - start;
        const increment = range / (duration / 16); // 60fps
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = this.formatNumber(current);
        }, 16);
    }

    /**
     * Format number for display
     */
    formatNumber(num) {
        if (typeof num !== 'number') return num;

        // Format currency
        if (Math.abs(num) >= 1) {
            return num.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        // Format small numbers
        return num.toFixed(4);
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `premium-toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            color: white;
            font-weight: 600;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        `;

        // Add color based on type
        switch (type) {
            case 'success':
                toast.style.borderColor = 'var(--premium-success)';
                break;
            case 'error':
                toast.style.borderColor = 'var(--premium-danger)';
                break;
            case 'warning':
                toast.style.borderColor = 'var(--premium-warning)';
                break;
        }

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Disable buttons during API call
     */
    setButtonsDisabled(buttonIds, disabled) {
        buttonIds.forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = disabled;
        });
    }
}

/**
 * Spot Trading UI Controller
 */
class SpotTradingUI extends TradingUI {
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            if (data.system_status) {
                const status = data.system_status.trading_enabled ? 'online' : 'paused';
                this.updateStatusIndicator('engineStatusText', status);
            }
        } catch (error) {
            console.error('Failed to update spot status:', error);
            this.updateStatusIndicator('engineStatusText', 'offline', 'OFFLINE');
        }
    }

    async toggleTrading(enable) {
        const btnStart = document.getElementById('btn-start');
        const btnStop = document.getElementById('btn-stop');

        this.setButtonsDisabled(['btn-start', 'btn-stop'], true);

        try {
            const response = await fetch('/api/spot/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable })
            });

            const data = await response.json();

            if (data.error) {
                this.showToast(data.error, 'error');
                this.updateStatusIndicator('engineStatusText', 'error', 'ERROR');
                this.addLog('ERROR', data.error, 'error');
            } else if (data.trading_enabled) {
                this.updateStatusIndicator('engineStatusText', 'online', 'ONLINE');
                this.addLog('SYSTEM', 'Spot Trading Engine Started', 'success');
                this.showToast('Spot trading enabled', 'success');
            } else {
                this.updateStatusIndicator('engineStatusText', 'paused', 'PAUSED');
                this.addLog('SYSTEM', 'Spot Trading Engine Paused', 'warning');
                this.showToast('Spot trading paused', 'warning');
            }
        } catch (error) {
            console.error('Toggle failed:', error);
            this.showToast('Failed to communicate with server', 'error');
            this.updateStatusIndicator('engineStatusText', 'offline', 'OFFLINE');
            this.addLog('ERROR', 'Failed to communicate with server', 'error');
        } finally {
            this.setButtonsDisabled(['btn-start', 'btn-stop'], false);
        }
    }
}

/**
 * Futures Trading UI Controller
 */
class FuturesTradingUI extends TradingUI {
    async updateStatus() {
        try {
            const response = await fetch('/api/futures/manual');
            const data = await response.json();

            // 1. Update Engine Status
            if (data.auto_trade_enabled !== undefined) {
                const status = data.auto_trade_enabled ? 'online' : 'paused';
                this.updateStatusIndicator('futuresEngineStatusText', status);
            }

            // 2. Update Stats (P&L, Leverage, Risk)
            const pnl = data.unrealized_pnl || 0;
            const pnlElem = document.getElementById('futuresPnl');
            if (pnlElem) {
                pnlElem.textContent = (pnl >= 0 ? '+' : '') + this.formatNumber(pnl);
                pnlElem.className = 'card-value ' + (pnl >= 0 ? 'text-success' : 'text-danger');
            }

            const levElem = document.getElementById('futuresLeverage');
            if (levElem) {
                levElem.textContent = (data.leverage || 1.0).toFixed(1) + 'x';
            }

            const riskElem = document.getElementById('futuresRiskScore');
            if (riskElem) {
                const score = data.risk_score || 0;
                riskElem.textContent = score + '/100';
                // Color mapping
                if (score < 30) riskElem.className = 'card-value text-info';
                else if (score < 60) riskElem.className = 'card-value text-warning';
                else riskElem.className = 'card-value text-danger';
            }

            // 3. Update Managed Futures Table
            const tbody = document.getElementById('futuresPositionsBody');
            if (tbody && data.selected_symbol) {
                if (!data.position) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                                No exposure. AI continues to scan for high-probability setups.
                            </td>
                        </tr>`;
                } else {
                    // We have an active position (simulated or real)
                    const sideClass = data.position === 'LONG' ? 'status-success' : 'status-danger';
                    const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
                    const markPrice = data.mark_price || data.entry_price || 0;

                    tbody.innerHTML = `
                        <tr class="log-entry-new">
                            <td style="font-weight: bold;">${data.selected_symbol}</td>
                            <td><span class="status-indicator ${sideClass}">${data.position}</span></td>
                            <td>${(data.leverage || 1).toFixed(0)}x</td>
                            <td>${this.formatNumber(data.entry_price || 0)}</td>
                            <td>${this.formatNumber(markPrice)}</td>
                            <td>${(data.position_notional / (markPrice || 1)).toFixed(3)}</td>
                            <td class="${pnlClass}">${(pnl >= 0 ? '+' : '') + this.formatNumber(pnl)}</td>
                            <td>${data.position === 'LONG' ? 'Higher' : 'Lower'}</td>
                            <td><span class="status-indicator status-success">OPEN</span></td>
                        </tr>
                    `;
                }
            }

        } catch (error) {
            console.error('Failed to update futures status:', error);
            this.updateStatusIndicator('futuresEngineStatusText', 'offline', 'OFFLINE');
        }
    }

    async toggleTrading(enable) {
        this.setButtonsDisabled(['btn-futures-start', 'btn-futures-stop'], true);

        try {
            const response = await fetch('/api/futures/manual/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable })
            });

            const data = await response.json();

            if (data.error) {
                this.showToast(data.error, 'error');
                this.updateStatusIndicator('futuresEngineStatusText', 'error', 'ERROR');
            } else if (data.auto_trade_enabled) {
                this.updateStatusIndicator('futuresEngineStatusText', 'online', 'ONLINE');
                this.showToast('Futures trading enabled', 'success');
            } else {
                this.updateStatusIndicator('futuresEngineStatusText', 'paused', 'PAUSED');
                this.showToast('Futures trading paused', 'warning');
            }
        } catch (error) {
            console.error('Toggle failed:', error);
            this.showToast('Failed to communicate with server', 'error');
            this.updateStatusIndicator('futuresEngineStatusText', 'offline', 'OFFLINE');
        } finally {
            this.setButtonsDisabled(['btn-futures-start', 'btn-futures-stop'], false);
        }
    }

    async panicClose() {
        if (!confirm("⚠️ PANIC BUTTON ACTIVATED ⚠️\n\nThis will immediately MARKET CLOSE all open positions and STOP the bot.\n\nProceed?")) {
            return;
        }

        try {
            await this.toggleTrading(false);
            this.showToast('All positions closed. Bot stopped.', 'success');
        } catch (error) {
            this.showToast('Failed to execute panic close', 'error');
        }
    }
}

// Export for use in HTML pages
window.TradingUI = TradingUI;
window.SpotTradingUI = SpotTradingUI;
window.FuturesTradingUI = FuturesTradingUI;
