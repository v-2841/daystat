// Shared Chart.js theming: reads CSS tokens, repaints on theme switch.
window.DaystatCharts = (() => {
    const charts = [];

    const cssVar = (name) =>
        getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    const palette = () => ({
        accent: cssVar("--accent"),
        text: cssVar("--text-body"),
        muted: cssVar("--text-muted"),
        grid: cssVar("--chart-grid"),
        tooltipBg: cssVar("--chart-tooltip"),
        tooltipText: cssVar("--text-strong"),
        line2: cssVar("--chart-line-2"),
    });

    const fade = (ctx, color) => {
        const area = ctx.chart.chartArea;
        if (!area) return "transparent";
        const gradient = ctx.chart.ctx.createLinearGradient(
            0, area.top, 0, area.bottom
        );
        gradient.addColorStop(0, `${color}55`);
        gradient.addColorStop(1, `${color}00`);
        return gradient;
    };

    const baseOptions = () => {
        const c = palette();
        return {
            maintainAspectRatio: false,
            animation: {
                duration: window.matchMedia("(prefers-reduced-motion: reduce)")
                    .matches
                    ? 0
                    : 900,
                easing: "easeOutQuart",
            },
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    display: false,
                    labels: { color: c.text, usePointStyle: true, boxWidth: 8 },
                },
                tooltip: {
                    backgroundColor: c.tooltipBg,
                    titleColor: c.tooltipText,
                    bodyColor: c.text,
                    borderColor: c.grid,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 14,
                    displayColors: false,
                    titleFont: { family: "Comfortaa", weight: "bold" },
                    bodyFont: { family: "Nunito", size: 13 },
                },
            },
            scales: {
                x: {
                    type: "time",
                    time: { unit: "day", tooltipFormat: "d MMMM yyyy" },
                    adapters: { date: { locale: "ru" } },
                    grid: { color: c.grid, drawTicks: false },
                    border: { display: false },
                    ticks: {
                        color: c.muted,
                        maxRotation: 0,
                        autoSkipPadding: 24,
                        font: { family: "Nunito", size: 11 },
                    },
                },
                y: {
                    grid: { color: c.grid, drawTicks: false },
                    border: { display: false },
                    ticks: {
                        color: c.muted,
                        font: { family: "Nunito", size: 11 },
                        padding: 8,
                    },
                },
            },
        };
    };

    // every chart repaints the same axes, grid and tooltip on a theme switch
    const applyTheme = (chart, colors, scales) => {
        for (const name of scales) {
            const scale = chart.options.scales[name];
            if (!scale) continue;
            if (scale.grid) scale.grid.color = colors.grid;
            if (scale.ticks) scale.ticks.color = colors.muted;
        }
        const tooltip = chart.options.plugins.tooltip;
        tooltip.backgroundColor = colors.tooltipBg;
        tooltip.titleColor = colors.tooltipText;
        tooltip.bodyColor = colors.text;
        tooltip.borderColor = colors.grid;
        if (chart.options.plugins.legend.labels) {
            chart.options.plugins.legend.labels.color = colors.text;
        }
    };

    const register = (chart, restyle) => {
        charts.push({ chart, restyle });
    };

    document.addEventListener("daystat:theme", () => {
        charts.forEach(({ chart, restyle }) => {
            restyle(chart, palette());
            chart.update("none");
        });
    });

    return { palette, fade, baseOptions, register, applyTheme };
})();
