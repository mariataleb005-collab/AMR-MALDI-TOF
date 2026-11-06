const fileInput = document.getElementById("spectrumFile");
const selectBtn = document.getElementById("selectFileBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const uploadZone = document.getElementById("uploadZone");
const fileNameText = document.getElementById("selectedFileName");
const uploadMessage = document.getElementById("uploadMessage");
const resultsSection = document.getElementById("resultsSection");
const predictionCards = document.getElementById("predictionCards");

let selectedFile = null;

function setFile(file) {
    selectedFile = file;
    resultsSection.hidden = true;
    predictionCards.replaceChildren();
    uploadMessage.textContent = "";

    if (!file) {
        analyzeBtn.disabled = true;
        fileNameText.textContent = "";
        return;
    }

    fileNameText.textContent = `Selected: ${file.name}`;
    analyzeBtn.disabled = false;
}

selectBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
    setFile(fileInput.files[0] || null);
});

uploadZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadZone.classList.add("dragging");
});

uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("dragging");
});

uploadZone.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadZone.classList.remove("dragging");

    if (event.dataTransfer.files.length !== 1) {
        uploadMessage.textContent = "Please upload one file at a time.";
        return;
    }

    setFile(event.dataTransfer.files[0]);
});

analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
    uploadMessage.textContent = "Validating spectrum...";
    resultsSection.hidden = true;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const response = await fetch("/api/predict", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Upload failed.");
        }

        predictionCards.replaceChildren();

        for (const [antibiotic, result] of Object.entries(data.predictions)) {
            const card = document.createElement("article");
            card.className = "prediction-card";

            const title = document.createElement("h3");
            title.textContent = antibiotic;

            const badge = document.createElement("span");
            badge.className = result === "R" ? "resistant" : "susceptible";
            badge.textContent = result === "R"
                ? "R — Resistant"
                : "S — Susceptible";

            card.append(title, badge);
            predictionCards.appendChild(card);
        }

        resultsSection.hidden = false;
        uploadMessage.textContent = "Demo results generated successfully.";

    } catch (error) {
        uploadMessage.textContent = error.message;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze Spectrum";
    }
});
