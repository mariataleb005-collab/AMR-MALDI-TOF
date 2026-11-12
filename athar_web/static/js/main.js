const form = document.getElementById("analyzeForm");
const fileInput = document.getElementById("spectrumFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const exampleBtn = document.getElementById("exampleBtn");
const uploadZone = document.getElementById("uploadZone");
const fileNameText = document.getElementById("selectedFileName");
const uploadMessage = document.getElementById("uploadMessage");
const resultsSection = document.getElementById("resultsSection");
const resultsMeta = document.getElementById("resultsMeta");
const predictionRows = document.getElementById("predictionRows");

let selectedFile = null;

function setFile(file) {
    selectedFile = file;
    resultsSection.hidden = true;
    predictionRows.replaceChildren();
    uploadMessage.textContent = "";
    uploadMessage.classList.remove("is-error");
    uploadZone.classList.toggle("has-file", Boolean(file));
    fileNameText.textContent = file ? file.name : "or drop it here";
    analyzeBtn.disabled = !file;
}

function showError(text) {
    uploadMessage.textContent = text;
    uploadMessage.classList.add("is-error");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0] || null));

uploadZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadZone.classList.add("is-dragging");
});

uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("is-dragging"));

uploadZone.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadZone.classList.remove("is-dragging");
    if (event.dataTransfer.files.length !== 1) {
        showError("Drop one file at a time.");
        return;
    }
    setFile(event.dataTransfer.files[0]);
});

// Builds a real DRIAMS-A spectrum file from the example shipped with the site.
exampleBtn.addEventListener("click", async () => {
    try {
        const response = await fetch("/static/data/representative_spectrum.json");
        if (!response.ok) throw new Error("The example spectrum is missing from static/data.");
        const data = await response.json();
        const csv = data.intensity.join("\n");
        const file = new File([csv], `DRIAMS-A_example_${data.spectrum_index}.csv`, {type: "text/csv"});
        fileInput.value = "";
        setFile(file);
        uploadMessage.textContent = "Example spectrum loaded. Select Analyze spectrum to run it.";
    } catch (error) {
        showError(error.message);
    }
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedFile) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing…";
    uploadMessage.classList.remove("is-error");
    uploadMessage.textContent = "Checking the spectrum.";
    resultsSection.hidden = true;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("sample_id", document.getElementById("sampleId").value.trim());
    formData.append("species", document.getElementById("species").value);

    try {
        const response = await fetch("/api/predict", {method: "POST", body: formData});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "The spectrum could not be analyzed.");

        predictionRows.replaceChildren();
        for (const result of data.results) predictionRows.appendChild(resultRow(result));

        const sample = data.sample_id ? `Sample ${data.sample_id}, ` : "";
        resultsMeta.textContent = `${sample}${data.filename}, analysis ${data.analysis_id}.`;
        const missing = data.not_installed.map(a => a.antibiotic);
        document.getElementById("resultsNote").textContent = missing.length
            ? `No model is installed for ${missing.join(", ")}, so ${missing.length === 1 ? "it was" : "they were"} skipped.`
            : "";
        resultsSection.hidden = false;
        uploadMessage.textContent = "Analysis complete.";
        resultsSection.scrollIntoView({behavior: smoothScroll(), block: "start"});
    } catch (error) {
        showError(error.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze spectrum";
    }
});
