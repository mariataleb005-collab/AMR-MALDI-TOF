// Results page: plot the stored spectrum and shade the regions of the selected antibiotic's model.
const chart = document.getElementById("spectrumChart");
const select = document.getElementById("regionAntibiotic");
const regionsByAntibiotic = JSON.parse(document.getElementById("regionData").textContent);
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const analysisId = location.pathname.split("/").filter(Boolean)[1];

function shapesFor(name) {
    return (regionsByAntibiotic[name] || []).map(([from, to]) => ({
        type: "rect", xref: "x", yref: "paper", x0: from, x1: to, y0: 0, y1: 1,
        fillcolor: css("--accent-wash"), line: {color: css("--accent"), width: 1}, layer: "below",
    }));
}

function selectedName() {
    return select ? select.selectedOptions[0].dataset.name : null;
}

function showPanel() {
    if (!select) return;
    document.querySelectorAll("[data-regions]").forEach(panel => {
        panel.hidden = panel.dataset.regions !== select.value;
    });
    if (chart && chart.data) Plotly.relayout(chart, {shapes: shapesFor(selectedName())});
}

async function drawSpectrum() {
    if (!chart) return;
    const response = await fetch(`/api/analysis/${analysisId}/spectrum`);
    if (!response.ok) {
        chart.textContent = "The spectrum could not be loaded.";
        return;
    }
    const data = await response.json();
    await Plotly.newPlot(chart, [{
        x: data.mz, y: data.intensity, type: "scattergl", mode: "lines",
        line: {color: css("--ink"), width: 0.9},
        hovertemplate: "%{x:,.1f} Da<br>Intensity %{y:.5f}<extra></extra>",
    }], {
        height: 340, margin: {t: 10, r: 12, b: 48, l: 60},
        xaxis: {title: {text: "m/z (Da)"}, range: [2000, 20000], tickformat: ",",
                gridcolor: css("--grid"), linecolor: css("--rule-strong"), zeroline: false},
        yaxis: {title: {text: "Intensity"}, gridcolor: css("--grid"), zeroline: false, rangemode: "tozero"},
        shapes: shapesFor(selectedName()),
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
        font: {family: "IBM Plex Sans, sans-serif", size: 12, color: css("--ink-2")},
    }, {displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d"]});
}

if (select) select.addEventListener("change", showPanel);
drawSpectrum();
