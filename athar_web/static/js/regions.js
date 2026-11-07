const antibioticSelect = document.getElementById('antibioticSelect');
const highlightCount = document.getElementById('highlightCount');
const regionMessage = document.getElementById('regionMessage');
const regionDetail = document.getElementById('regionDetail');
const regionDetailText = document.getElementById('regionDetailText');
const resetSpectrumButton = document.getElementById('resetSpectrumView');
const zoomStatus = document.getElementById('zoomStatus');
let spectrumData = null;
let currentRegions = [];
let requestNumber = 0;
const fmt = (n, digits = 0) => Number(n).toLocaleString('en-US', {maximumFractionDigits: digits});
const makeCell = (tr, value) => { const td = document.createElement('td'); td.textContent = String(value); tr.appendChild(td); };
const positiveRegions = () => [...currentRegions].filter(r => Number(r.importance) > 0).sort((a,b) => b.importance - a.importance);
const highlightedRegions = () => positiveRegions().slice(0, Number(highlightCount.value));

async function loadSpectrum() {
  const response = await fetch('/static/data/representative_spectrum.json');
  if (!response.ok) throw new Error('Example spectrum file not found. Run the spectrum export script first.');
  const data = await response.json();
  if (!Array.isArray(data.mz) || !Array.isArray(data.intensity) || data.mz.length !== 6000 || data.intensity.length !== 6000 || data.intensity.some(v => !Number.isFinite(v))) throw new Error('Spectrum JSON does not contain 6,000 valid intensity values.');
  spectrumData = data;
}

function showRegion(region) {
  regionDetail.hidden = false;
  regionDetailText.textContent = `Region ${region.region} · m/z ${fmt(region.mz_from)}–${fmt(region.mz_to)} Da · peak ${fmt(region.peak_mz,1)} Da · ${region.ra_pso_seeds} RA-PSO seeds · ΔAUPRC ${region.importance.toFixed(5)} · ${region.direction}`;
}

// Zoom to a 360 Da neighborhood so the selected 30 Da interval is visible.
async function focusRegion(region) {
  showRegion(region);
  const chart = document.getElementById('spectrumChart');
  if (!chart.data) return;
  const midpoint = (Number(region.mz_from) + Number(region.mz_to)) / 2;
  const halfWindow = 180;
  const left = Math.max(2000, midpoint - halfWindow);
  const right = Math.min(20000, midpoint + halfWindow);
  await Plotly.relayout(chart, {'xaxis.range': [left, right]});
  zoomStatus.textContent = `Focused on region ${region.region} · ${fmt(left)}–${fmt(right)} Da`;
  chart.scrollIntoView({behavior: 'smooth', block: 'center'});
}

async function resetSpectrumView() {
  const chart = document.getElementById('spectrumChart');
  if (!chart.data) return;
  await Plotly.relayout(chart, {'xaxis.range': [2000, 20000]});
  zoomStatus.textContent = 'Full spectrum · 2,000–20,000 Da';
}

async function renderSpectrum() {
  if (!spectrumData) return;
  const selected = highlightedRegions();
  const yMax = Math.max(...spectrumData.intensity);
  const shapes = selected.map(r => ({type:'rect',xref:'x',yref:'paper',x0:r.mz_from,x1:r.mz_to,y0:0,y1:1,fillcolor:'rgba(20,125,121,0.17)',line:{color:'rgba(20,125,121,0.65)',width:1},layer:'below'}));
  const regionPeaks = selected.map(r => {
    const start = Math.max(0, Math.floor((r.mz_from - 2000) / 3));
    const end = Math.min(6000, Math.ceil((r.mz_to - 2000) / 3));
    return Math.max(0, ...spectrumData.intensity.slice(start,end));
  });
  await Plotly.react('spectrumChart', [
    {x:spectrumData.mz,y:spectrumData.intensity,type:'scatter',mode:'lines',line:{color:'#213e62',width:1},name:'Example spectrum',hovertemplate:'m/z %{x:.1f} Da<br>Intensity %{y:.6f}<extra></extra>'},
    {x:selected.map(r => (r.mz_from+r.mz_to)/2),y:regionPeaks,type:'scatter',mode:'markers',marker:{color:'#147d79',size:9,symbol:'circle-open',line:{width:2}},customdata:selected.map(r=>r.region),hovertemplate:'Region %{customdata}<br>m/z %{x:.1f} Da<extra></extra>',name:'Highlighted regions'}
  ],{margin:{t:15,r:18,b:52,l:68},height:355,xaxis:{title:'m/z (Da)',range:[2000,20000],gridcolor:'#eef2f4',zeroline:false},yaxis:{title:'Intensity',range:[0,yMax*1.08],gridcolor:'#eef2f4',zeroline:false},shapes,paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'Segoe UI, Arial, sans-serif',size:11,color:'#526675'},showlegend:false,hovermode:'closest',dragmode:'zoom'}, {responsive:true,displaylogo:false,scrollZoom:true});
  const chart = document.getElementById('spectrumChart');
  if (!chart.dataset.clickBound) {
    chart.on('plotly_click', event => {const p=event.points?.[0];if (!p || p.curveNumber !== 1) return;const r=currentRegions.find(r=>r.region===p.customdata);if(r)focusRegion(r);});
    chart.dataset.clickBound='true';
  }
  document.getElementById('metricHighlighted').textContent = String(selected.length);
}

function renderTables() {
  const sorted = [...currentRegions].sort((a,b)=>b.importance-a.importance);
  const summary = document.getElementById('regionSummaryBody');
  const details = document.getElementById('regionsTableBody');
  summary.replaceChildren(); details.replaceChildren();
  for (const r of sorted.slice(0,5)) {
    const tr=document.createElement('tr');
    [r.region,`${fmt(r.mz_from)}–${fmt(r.mz_to)}`,r.ra_pso_seeds,r.importance.toFixed(5)].forEach(v=>makeCell(tr,v));
    tr.tabIndex=0;tr.setAttribute('aria-label',`Focus spectrum on region ${r.region}`);tr.addEventListener('click',()=>focusRegion(r));tr.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();focusRegion(r);}});summary.appendChild(tr);
  }
  for (const r of sorted.slice(0,20)) {
    const tr=document.createElement('tr');
    [r.region,`${fmt(r.mz_from)}–${fmt(r.mz_to)}`,fmt(r.peak_mz,1),r.ra_pso_seeds,r.importance.toFixed(5),r.direction].forEach(v=>makeCell(tr,v));
    tr.tabIndex=0;tr.setAttribute('aria-label',`Focus spectrum on region ${r.region}`);tr.addEventListener('click',()=>focusRegion(r));tr.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();focusRegion(r);}});details.appendChild(tr);
  }
  document.getElementById('metricRegions').textContent=fmt(currentRegions.length);
  document.getElementById('metricTopImportance').textContent=sorted.length?sorted[0].importance.toFixed(5):'—';
}

async function renderImportance() {
  const ordered=[...currentRegions].sort((a,b)=>a.peak_mz-b.peak_mz);
  await Plotly.react('regionChart',[{x:ordered.map(r=>r.peak_mz),y:ordered.map(r=>r.importance),type:'scatter',mode:'markers',marker:{color:ordered.map(r=>r.importance>=0?'#147d79':'#b77945'),size:7,opacity:.85},text:ordered.map(r=>`Region ${r.region} · ${r.direction}`),hovertemplate:'%{text}<br>m/z %{x:.1f}<br>ΔAUPRC %{y:.5f}<extra></extra>'}],{height:260,margin:{t:10,r:12,b:45,l:65},xaxis:{title:'m/z (Da)',gridcolor:'#edf1f4'},yaxis:{title:'ΔAUPRC',gridcolor:'#edf1f4',zeroline:true,zerolinecolor:'#b6c4cb'},paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'Segoe UI, Arial, sans-serif',size:10,color:'#526675'}},{responsive:true,displaylogo:false});
}

async function loadRegions() {
  const thisRequest=++requestNumber;
  const antibiotic=antibioticSelect.value;
  regionMessage.textContent='Loading experimental results…';
  regionDetail.hidden=true;
  zoomStatus.textContent = 'Full spectrum · 2,000–20,000 Da';
  try {
    const response=await fetch(`/api/regions/${encodeURIComponent(antibiotic)}`);
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'Could not load region results.');
    if(thisRequest!==requestNumber)return;
    if(!Array.isArray(data.regions))throw new Error('Unexpected region API response.');
    currentRegions=data.regions;
    document.getElementById('metricAUPRC').textContent=Number.isFinite(Number(data.signature_cv_auprc)) && data.signature_cv_auprc != null ? Number(data.signature_cv_auprc).toFixed(3) : '—';
    renderTables();
    await Promise.all([renderSpectrum(),renderImportance()]);
    if(thisRequest===requestNumber)regionMessage.textContent=`Showing ${Math.min(20,currentRegions.length)} of ${currentRegions.length} reported regions for ${antibiotic}.`;
  } catch(error) {
    if(thisRequest!==requestNumber)return;
    regionMessage.textContent=error.message;
    currentRegions=[];
    document.getElementById('regionSummaryBody').replaceChildren();
    document.getElementById('regionsTableBody').replaceChildren();
    document.getElementById('metricRegions').textContent='—';
    document.getElementById('metricHighlighted').textContent='—';
    document.getElementById('metricTopImportance').textContent='—';
    document.getElementById('metricAUPRC').textContent='—';
    ['spectrumChart','regionChart'].forEach(id=>{const el=document.getElementById(id);if(el && el.data)Plotly.purge(el);});
  }
}
antibioticSelect.addEventListener('change',loadRegions);
highlightCount.addEventListener('change',()=>{regionDetail.hidden=true;zoomStatus.textContent='Full spectrum · 2,000–20,000 Da';renderSpectrum();});
resetSpectrumButton.addEventListener('click',resetSpectrumView);
(async()=>{try{await loadSpectrum();await loadRegions();}catch(error){regionMessage.textContent=error.message;}})();
