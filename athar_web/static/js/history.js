const historyRows = document.getElementById("historyRows");
const historyStatus = document.getElementById("historyStatus");
const historyEmpty = document.getElementById("historyEmpty");
const historySearch = document.getElementById("historySearch");
const historyDetails = document.getElementById("historyDetails");
const historyDetailMeta = document.getElementById("historyDetailMeta");
const historyDetailResults = document.getElementById("historyDetailResults");
let allRecords = [];

const countCalls = (results, call) => results.filter(r => r.call === call).length;

function summarize(records) {
    const results = records.flatMap(r => r.results);
    document.getElementById("statAnalyses").textContent = records.length;
    document.getElementById("statResistant").textContent = countCalls(results, "R");
    document.getElementById("statSusceptible").textContent = countCalls(results, "S");
    document.getElementById("statIndeterminate").textContent = countCalls(results, "I");
}

function cell(row, text) {
    const td = document.createElement("td");
    td.textContent = String(text);
    row.appendChild(td);
    return td;
}

function showDetails(record) {
    historyDetails.hidden = false;
    const sample = record.sample_id ? `Sample ${record.sample_id}, ` : "";
    historyDetailMeta.textContent =
        `Analysis ${record.id}. ${sample}${record.filename}, ${record.species}, ${utcText(record.created_at)} UTC.`;
    historyDetailResults.replaceChildren(...record.results.map(resultRow));
    historyDetails.scrollIntoView({behavior: smoothScroll(), block: "nearest"});
}

function renderHistory() {
    const query = historySearch.value.trim().toLowerCase();
    const filtered = allRecords.filter(r =>
        `${r.id} ${r.sample_id} ${r.filename}`.toLowerCase().includes(query));
    historyRows.replaceChildren();
    for (const record of filtered) {
        const tr = document.createElement("tr");
        cell(tr, record.id);
        cell(tr, utcText(record.created_at));
        cell(tr, record.sample_id || "–");
        cell(tr, record.filename);
        const r = record.results;
        const i = countCalls(r, "I");
        cell(tr, `${countCalls(r, "R")} R, ${countCalls(r, "S")} S${i ? `, ${i} I` : ""}`);
        const actionCell = document.createElement("td");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button-link";
        button.textContent = "View";
        button.setAttribute("aria-label", `View analysis ${record.id}`);
        button.addEventListener("click", () => showDetails(record));
        actionCell.appendChild(button);
        tr.appendChild(actionCell);
        historyRows.appendChild(tr);
    }
    historyEmpty.hidden = allRecords.length !== 0;
    historyStatus.textContent = allRecords.length
        ? `${filtered.length} of ${allRecords.length} analyses shown.`
        : "";
}

async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        if (!response.ok) throw new Error("The history could not be loaded.");
        const data = await response.json();
        allRecords = data.records;
        summarize(allRecords);
        renderHistory();
    } catch (error) {
        historyStatus.textContent = error.message;
    }
}

historySearch.addEventListener("input", renderHistory);
document.getElementById("historyClose").addEventListener("click", () => { historyDetails.hidden = true; });
loadHistory();
