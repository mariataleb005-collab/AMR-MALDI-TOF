const historyRows = document.getElementById('historyRows');
const historyStatus = document.getElementById('historyStatus');
const historyEmpty = document.getElementById('historyEmpty');
const historySearch = document.getElementById('historySearch');
const historyMode = document.getElementById('historyMode');
const historyDetails = document.getElementById('historyDetails');
const historyDetailMeta = document.getElementById('historyDetailMeta');
const historyDetailResults = document.getElementById('historyDetailResults');
let allRecords = [];

function summarize(records) {
    const calls = records.flatMap(r => Object.values(r.predictions));
    document.getElementById('statAnalyses').textContent = records.length;
    document.getElementById('statResistant').textContent = calls.filter(x => x === 'R').length;
    document.getElementById('statSusceptible').textContent = calls.filter(x => x === 'S').length;
}
function cell(row, text) {
    const td = document.createElement('td');
    td.textContent = String(text);
    row.appendChild(td);
    return td;
}
function showDetails(record) {
    historyDetails.hidden = false;
    historyDetailMeta.textContent = `Record #${record.id} · ${record.filename} · ${record.created_at} UTC · Demo / Simulated`;
    historyDetailResults.replaceChildren();
    for (const [antibiotic, result] of Object.entries(record.predictions)) {
        const item = document.createElement('div');
        item.className = 'history-result';
        const name = document.createElement('span');
        name.textContent = antibiotic;
        const badge = document.createElement('strong');
        badge.className = result === 'R' ? 'resistant' : 'susceptible';
        badge.textContent = result === 'R' ? 'R — Simulated' : 'S — Simulated';
        item.append(name, badge);
        historyDetailResults.appendChild(item);
    }
    historyDetails.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
function renderHistory() {
    const query = historySearch.value.trim().toLowerCase();
    const mode = historyMode.value;
    const filtered = allRecords.filter(r =>
        (mode === 'all' || r.mode === mode) &&
        (`${r.id} ${r.filename}`.toLowerCase().includes(query))
    );
    historyRows.replaceChildren();
    for (const record of filtered) {
        const tr = document.createElement('tr');
        const values = Object.values(record.predictions);
        cell(tr, `#${record.id}`);
        cell(tr, record.created_at.replace('T', ' ').replace('+00:00', ''));
        cell(tr, record.filename);
        cell(tr, 'Demo / Simulated');
        cell(tr, `${values.filter(x => x === 'R').length} R / ${values.filter(x => x === 'S').length} S`);
        const actionCell = document.createElement('td');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'history-view';
        button.textContent = 'View';
        button.addEventListener('click', () => showDetails(record));
        actionCell.appendChild(button);
        tr.appendChild(actionCell);
        historyRows.appendChild(tr);
    }
    historyEmpty.hidden = filtered.length !== 0;
    historyStatus.textContent = `Showing ${filtered.length} of ${allRecords.length} analyses`;
}
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error('Could not load history.');
        const data = await response.json();
        allRecords = data.records;
        summarize(allRecords);
        renderHistory();
    } catch (error) {
        historyStatus.textContent = error.message;
    }
}
historySearch.addEventListener('input', renderHistory);
historyMode.addEventListener('change', renderHistory);
document.getElementById('historyClose').addEventListener('click', () => { historyDetails.hidden = true; });
loadHistory();
