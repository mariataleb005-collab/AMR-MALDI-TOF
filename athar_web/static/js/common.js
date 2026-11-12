// Shared helpers for the Analyze and History pages.

const CALL_LABELS = {R: "Resistant", S: "Susceptible", I: "Indeterminate"};

function callBadge(call) {
    const badge = document.createElement("span");
    badge.className = `call call-${call.toLowerCase()}`;
    badge.textContent = CALL_LABELS[call] || call;
    return badge;
}

function resultRow(result) {
    const tr = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = result.antibiotic;

    const call = document.createElement("td");
    call.appendChild(callBadge(result.call));

    const score = document.createElement("td");
    score.className = "num";
    score.textContent = result.score_type === "probability"
        ? `${(result.score * 100).toFixed(1)}%`
        : result.score.toFixed(3);

    const threshold = document.createElement("td");
    threshold.className = "num";
    threshold.textContent = result.score_type === "probability"
        ? `${(result.threshold * 100).toFixed(1)}%`
        : result.threshold.toFixed(3);

    tr.append(name, call, score, threshold);
    return tr;
}

function utcText(iso) {
    return iso.replace("T", " ").replace("+00:00", "");
}

function smoothScroll() {
    return matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}
