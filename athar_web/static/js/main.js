// Analyze page: choose or drop a spectrum file, send it, then open the results page.
const form = document.getElementById("analyzeForm");
const fileInput = document.getElementById("spectrumFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const exampleBtn = document.getElementById("exampleBtn");
const uploadZone = document.getElementById("uploadZone");
const fileNameText = document.getElementById("selectedFileName");
const uploadMessage = document.getElementById("uploadMessage");

let selectedFile = null;

function setFile(file) {
    selectedFile = file;
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
        const file = new File([data.intensity.join("\n")], `DRIAMS-A_example_${data.spectrum_index}.csv`,
                              {type: "text/csv"});
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

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("sample_id", document.getElementById("sampleId").value.trim());
    formData.append("species", document.getElementById("species").value);

    try {
        const response = await fetch("/api/predict", {method: "POST", body: formData});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "The spectrum could not be analyzed.");
        uploadMessage.textContent = "Analysis complete. Opening the results.";
        window.location.assign(data.url);
    } catch (error) {
        showError(error.message);
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze spectrum";
    }
});
