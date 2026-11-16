const historyRows = document.getElementById("historyRows");
const historyStatus = document.getElementById("historyStatus");
const historyEmpty = document.getElementById("historyEmpty");
const historySearch = document.getElementById("historySearch");
let allRecords = [];

const countCalls = (results, call) => results.filter(r => r.call === call).length;

function summarize(records) {
    const results = records.flatMap(r => r.results);
    document.getElementById("statAnalyses").textContent = records.length;
    document.getElementById("statResistant").textContent = countCalls(results, "R");
    document.getElementById("statSusceptible").textContent = countCalls(results, "S");
    document.getElementById("statAntibiotics").textContent = records.length ? records[0].results.length : "—";
}

function cell(row, text) {
    const td = document.createElement("td");
    td.textContent = String(text);
    row.appendChild(td);
    return td;
}

function utcText(iso) {
    return iso.replace("T", " ").replace("+00:00", "");
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
        cell(tr, `${countCalls(r, "R")} R, ${countCalls(r, "S")} S`);
        const actionCell = document.createElement("td");
        const link = document.createElement("a");
        link.href = `/analysis/${record.id}`;
        link.textContent = "Open";
        link.setAttribute("aria-label", `Open analysis ${record.id}`);
        actionCell.appendChild(link);
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
loadHistory();
