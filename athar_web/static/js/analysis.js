// Results page: the stored spectrum with the selected model's regions shaded, and a bar chart of the
// regions with the largest effect on each call.
const chart = document.getElementById("spectrumChart");
const select = document.getElementById("regionAntibiotic");
const chartData = JSON.parse(document.getElementById("chartData").textContent);
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const analysisId = location.pathname.split("/").filter(Boolean)[1];
const font = () => ({family: "IBM Plex Sans, sans-serif", size: 12, color: css("--ink-2")});
const drawn = new Set();

function shapesFor(name) {
    return ((chartData[name] || {}).shading || []).map(([from, to]) => ({
        type: "rect", xref: "x", yref: "paper", x0: from, x1: to, y0: 0, y1: 1,
        fillcolor: css("--accent-wash"), line: {color: css("--accent"), width: 1}, layer: "below",
    }));
}

function selectedName() {
    return select ? select.selectedOptions[0].dataset.name : null;
}

function drawEffects(name) {
    const target = document.querySelector(`.effect-chart[data-effects="${CSS.escape(name)}"]`);
    const data = chartData[name];
    if (!target || !data || !data.effects.length || drawn.has(name)) return;
    drawn.add(name);
    const scale = data.score_type === "probability" ? 100 : 1;
    const bars = [...data.effects].reverse();               // largest at the top
    Plotly.newPlot(target, [{
        type: "bar", orientation: "h",
        x: bars.map(b => b.effect * scale), y: bars.map(b => b.label),
        marker: {color: bars.map(b => b.effect >= 0 ? css("--res") : css("--sus"))},
        hovertemplate: data.score_type === "probability"
            ? "%{y}<br>%{x:+.1f} points<extra></extra>" : "%{y}<br>%{x:+.3f}<extra></extra>",
    }], {
        height: 60 + 26 * bars.length, margin: {t: 8, r: 16, b: 36, l: 130},
        xaxis: {zeroline: true, zerolinecolor: css("--rule-strong"), gridcolor: css("--grid"),
                title: {text: data.score_type === "probability" ? "Effect (percentage points)" : "Effect on score"}},
        yaxis: {automargin: true},
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: font(),
    }, {displaylogo: false, responsive: true, displayModeBar: false});
}

function showPanel() {
    if (!select) return;
    document.querySelectorAll("[data-regions]").forEach(panel => {
        panel.hidden = panel.dataset.regions !== select.value;
    });
    drawEffects(selectedName());
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
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: font(),
    }, {displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d"]});
}

if (select) select.addEventListener("change", showPanel);
drawSpectrum();
if (select) drawEffects(selectedName());
