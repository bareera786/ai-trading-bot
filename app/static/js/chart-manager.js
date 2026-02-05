
/**
 * ChartManager - Wrapper for TradingView Lightweight Charts
 * Handles chart initialization, data loading, and real-time updates.
 */
class ChartManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.currentSymbol = null;
    }

    init() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Create Chart
        this.chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 400,
            layout: {
                background: { type: 'solid', color: '#0f172a' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(51, 65, 85, 0.4)' },
                horzLines: { color: 'rgba(51, 65, 85, 0.4)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            timeScale: {
                borderColor: 'rgba(148, 163, 184, 0.2)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Add Candlestick Series
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        // Add Volume Series (Histogram)
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#3b82f6',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '', // Overlay on main chart or generic
        });

        // Put volume on a separate scale or overlay at bottom?
        // Lightweight charts default puts volume on main pane if priceScaleId is set to overlay.
        // To put it separate, we need extra config. For now, overlay at bottom is fine.
        this.volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8, // volume takes bottom 20%
                bottom: 0,
            },
        });

        // Handle resize
        window.addEventListener('resize', () => {
            this.chart.applyOptions({
                width: container.clientWidth,
            });
        });
    }

    async loadSymbol(symbol) {
        this.currentSymbol = symbol;
        const container = document.getElementById(this.containerId);

        // Show loading state if possible
        container.style.opacity = '0.5';

        try {
            const response = await fetch(`/api/market-data/history/${symbol}`);
            const data = await response.json();

            if (data.success && data.candles) {
                // Ensure data is sorted by time
                const candles = data.candles.sort((a, b) => a.time - b.time);

                const prices = candles.map(c => ({
                    time: c.time,
                    open: c.open,
                    high: c.high,
                    low: c.low,
                    close: c.close
                }));

                const volumes = candles.map(c => ({
                    time: c.time,
                    value: c.volume,
                    color: c.close >= c.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)'
                }));

                this.candleSeries.setData(prices);
                this.volumeSeries.setData(volumes);

                // Auto-fit content
                this.chart.timeScale().fitContent();
            }
        } catch (error) {
            console.error("Failed to load chart data:", error);
        } finally {
            container.style.opacity = '1';
        }
    }

    updateCandle(candle) {
        // Real-time update single candle
        if (!this.candleSeries) return;

        this.candleSeries.update({
            time: candle.time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close
        });

        if (this.volumeSeries && candle.volume) {
            this.volumeSeries.update({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)'
            });
        }
    }
}
