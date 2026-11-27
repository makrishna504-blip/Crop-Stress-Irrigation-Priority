
const API_URL = "https://crop-stress-irrigation-priority.onrender.com";



function showPage(pageName) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active");
    });

    const selectedPage = document.getElementById(pageName);

    if (selectedPage) {
        selectedPage.classList.add("active");
    }

    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.remove("active");
    });

    const activeLink = document.querySelector(
        `[data-page="${pageName}"]`
    );

    if (activeLink) {
        activeLink.classList.add("active");
    }

    
    if (
        pageName.toLowerCase().includes("history") ||
        pageName.toLowerCase().includes("record")
    ) {
        loadHistory();
    }

    if (pageName.toLowerCase().includes("dashboard")) {
        loadHistory();
    }
}


document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", function (event) {
        event.preventDefault();

        const pageName =
            this.dataset.page ||
            this.getAttribute("data-target") ||
            this.getAttribute("href");

        if (pageName) {
            showPage(pageName.replace("#", ""));
        }
    });
});



function updateDateTime() {
    const dateElement = document.getElementById("currentDate");
    const timeElement = document.getElementById("currentTime");

    const now = new Date();

    if (dateElement) {
        dateElement.textContent = now.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );
    }

    if (timeElement) {
        timeElement.textContent = now.toLocaleTimeString(
            "en-IN",
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );
    }
}

updateDateTime();



function getElementValue(id) {
    const element = document.getElementById(id);

    if (!element) {
        return "";
    }

    return element.value.trim();
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function showMessage(message, type = "info") {
    let messageBox = document.getElementById("messageBox");

    if (!messageBox) {
        messageBox = document.createElement("div");
        messageBox.id = "messageBox";

        messageBox.style.position = "fixed";
        messageBox.style.top = "20px";
        messageBox.style.right = "20px";
        messageBox.style.padding = "15px 20px";
        messageBox.style.borderRadius = "10px";
        messageBox.style.zIndex = "9999";
        messageBox.style.maxWidth = "350px";
        messageBox.style.fontSize = "14px";
        messageBox.style.boxShadow = "0 4px 15px rgba(0,0,0,0.15)";

        document.body.appendChild(messageBox);
    }

    messageBox.textContent = message;

    if (type === "success") {
        messageBox.style.background = "#dcfce7";
        messageBox.style.color = "#166534";
    } else if (type === "error") {
        messageBox.style.background = "#fee2e2";
        messageBox.style.color = "#991b1b";
    } else {
        messageBox.style.background = "#dbeafe";
        messageBox.style.color = "#1e40af";
    }

    messageBox.style.display = "block";

    setTimeout(function () {
        messageBox.style.display = "none";
    }, 5000);
}



async function checkAPIConnection() {
    const statusElement = document.getElementById("apiStatus");

    if (statusElement) {
        statusElement.textContent = "Checking connection...";
    }

    try {
        const response = await fetch(API_URL + "/");

        if (response.ok) {
            if (statusElement) {
                statusElement.textContent = "Backend Connected";
                statusElement.style.color = "green";
            }
        } else {
            if (statusElement) {
                statusElement.textContent = "Backend Responded";
            }
        }

    } catch (error) {
        console.error("API connection error:", error);

        if (statusElement) {
            statusElement.textContent = "Backend Unavailable";
            statusElement.style.color = "red";
        }
    }
}



function collectPredictionData() {

    const inputData = {
        village: getElementValue("village"),
        district: getElementValue("district"),
        state: getElementValue("state"),
        field_id: getElementValue("field_id"),
        crop: getElementValue("crop"),
        growth_stage: getElementValue("growth_stage"),
        season: getElementValue("season"),
        soil_moisture: Number(
            getElementValue("soil_moisture") || 0
        )
    };

    return inputData;
}


function showPredictionLoading(isLoading) {
    const button = document.getElementById("predictButton");

    if (button) {
        button.disabled = isLoading;
        button.textContent = isLoading
            ? "Analyzing Crop..."
            : "Predict Crop Condition";
    }

    const loadingElement = document.getElementById("loading");

    if (loadingElement) {
        loadingElement.style.display = isLoading
            ? "block"
            : "none";
    }
}


async function predictCrop(event) {

    if (event) {
        event.preventDefault();
    }

    const inputData = collectPredictionData();

    if (!inputData.crop) {
        showMessage("Please select a crop.", "error");
        return;
    }

    if (!inputData.season) {
        showMessage("Please select a season.", "error");
        return;
    }

    showPredictionLoading(true);

    try {

        const response = await fetch(API_URL + "/predict", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(inputData)
        });

        let result;

        try {
            result = await response.json();
        } catch {
            result = {};
        }

        if (!response.ok) {

            const errorMessage =
                result.detail ||
                result.error ||
                "Prediction request failed.";

            throw new Error(
                typeof errorMessage === "string"
                    ? errorMessage
                    : JSON.stringify(errorMessage)
            );
        }

        displayPrediction(result);

        showMessage(
            "Crop prediction completed successfully!",
            "success"
        );

        // Refresh prediction history after successful prediction
        loadHistory();

    } catch (error) {

        console.error("Prediction error:", error);

        showMessage(
            "Prediction failed: " + error.message,
            "error"
        );

    } finally {
        showPredictionLoading(false);
    }
}



function displayPrediction(result) {

    const cropCondition =
        result.predicted_crop_condition ||
        result.prediction ||
        result.crop_condition ||
        "Unknown";

    const confidence =
        result.confidence_percent ??
        result.confidence ??
        0;

    const riskScore =
        result.risk_score ??
        "--";

    const riskLevel =
        result.risk_level ??
        "--";

    const irrigationPriority =
        result.irrigation_priority ??
        "--";

    const insuranceRisk =
        result.insurance_risk_score ??
        "--";

    const recommendation =
        result.recommendation ||
        result.irrigation_recommendation ||
        "No recommendation provided by the backend.";

    setText("predictedCondition", cropCondition);
    setText("cropCondition", cropCondition);
    setText("confidence", confidence + "%");
    setText("confidencePercent", confidence + "%");

    setText("riskScore", riskScore);
    setText("riskLevel", riskLevel);

    setText("irrigationPriority", irrigationPriority);
    setText("insuranceRiskScore", insuranceRisk);

    setText("recommendation", recommendation);

    displayClassProbabilities(
        result.class_probabilities ||
        result.probabilities ||
        {}
    );

    const resultSection = document.getElementById("predictionResult");

    if (resultSection) {
        resultSection.style.display = "block";
    }

    if (resultSection) {
        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}



function displayClassProbabilities(probabilities) {

    const container =
        document.getElementById("classProbabilities");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    const classes = Object.keys(probabilities);

    if (classes.length === 0) {
        container.textContent =
            "Class probability data is not available.";
        return;
    }

    classes.forEach(className => {

        const probability = Number(
            probabilities[className]
        );

        const safeProbability =
            Number.isFinite(probability)
                ? probability
                : 0;

        const row = document.createElement("div");
        row.className = "probability-row";

        const label = document.createElement("span");
        label.textContent = className;

        const value = document.createElement("span");
        value.textContent = safeProbability + "%";

        const progress = document.createElement("div");
        progress.className = "probability-bar";

        const progressFill = document.createElement("div");
        progressFill.className = "probability-fill";

        progressFill.style.width =
            Math.max(0, Math.min(100, safeProbability)) + "%";

        progress.appendChild(progressFill);

        row.appendChild(label);
        row.appendChild(value);
        row.appendChild(progress);

        container.appendChild(row);
    });
}



async function loadHistory() {

    const historyContainer =
        document.getElementById("historyTableBody");

    if (!historyContainer) {
        return;
    }

    historyContainer.innerHTML = `
        <tr>
            <td colspan="8">Loading prediction history...</td>
        </tr>
    `;

    try {

        const response = await fetch(
            API_URL + "/api/history"
        );

        if (!response.ok) {
            throw new Error(
                "History endpoint is not available."
            );
        }

        const data = await response.json();

        let records = data;

        if (data.records) {
            records = data.records;
        }

        if (data.history) {
            records = data.history;
        }

        if (!Array.isArray(records)) {
            records = [];
        }

        displayHistory(records);

    } catch (error) {

        console.warn("History loading error:", error);

        historyContainer.innerHTML = `
            <tr>
                <td colspan="8">
                    History is unavailable.
                    The backend may not have an /api/history endpoint yet.
                </td>
            </tr>
        `;
    }
}


function displayHistory(records) {

    const historyContainer =
        document.getElementById("historyTableBody");

    if (!historyContainer) {
        return;
    }

    historyContainer.innerHTML = "";

    if (!records || records.length === 0) {

        historyContainer.innerHTML = `
            <tr>
                <td colspan="8">
                    No prediction records found.
                </td>
            </tr>
        `;

        return;
    }

    records.forEach(record => {

        const row = document.createElement("tr");

        const predictionId =
            record.prediction_id ??
            record.id ??
            "--";

        const crop =
            record.crop ??
            "--";

        const village =
            record.village ??
            "--";

        const condition =
            record.crop_condition ??
            record.predicted_crop_condition ??
            "--";

        const confidence =
            record.confidence_percent ??
            "--";

        const priority =
            record.irrigation_priority ??
            "--";

        const date =
            record.created_at ??
            record.timestamp ??
            "--";

        row.innerHTML = `
            <td>${escapeHTML(predictionId)}</td>
            <td>${escapeHTML(crop)}</td>
            <td>${escapeHTML(village)}</td>
            <td>${escapeHTML(condition)}</td>
            <td>${escapeHTML(confidence)}</td>
            <td>${escapeHTML(priority)}</td>
            <td>${escapeHTML(date)}</td>
        `;

        historyContainer.appendChild(row);
    });
}


function escapeHTML(value) {

    const element = document.createElement("div");

    element.textContent = String(value);

    return element.innerHTML;
}



async function loadDashboardStats() {

    try {

        const response = await fetch(
            API_URL + "/api/history"
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        let records = data;

        if (data.records) {
            records = data.records;
        }

        if (data.history) {
            records = data.history;
        }

        if (!Array.isArray(records)) {
            records = [];
        }

        const total = records.length;

        let stressed = 0;
        let healthy = 0;
        let highRisk = 0;

        records.forEach(record => {

            const condition = String(
                record.crop_condition ||
                record.predicted_crop_condition ||
                ""
            ).toLowerCase();

            const risk = String(
                record.risk_level || ""
            ).toLowerCase();

            if (
                condition.includes("stress") ||
                condition.includes("diseased") ||
                condition.includes("pest")
            ) {
                stressed++;
            }

            if (condition.includes("healthy")) {
                healthy++;
            }

            if (
                risk.includes("high") ||
                risk.includes("critical")
            ) {
                highRisk++;
            }
        });

        setText("totalPredictions", total);
        setText("stressedCrops", stressed);
        setText("healthyCrops", healthy);
        setText("highRiskFields", highRisk);

    } catch (error) {
        console.warn(
            "Dashboard statistics unavailable:",
            error
        );
    }
}



function clearPredictionForm() {

    const form =
        document.getElementById("predictionForm") ||
        document.getElementById("cropPredictionForm");

    if (form) {
        form.reset();
    }

    const resultSection =
        document.getElementById("predictionResult");

    if (resultSection) {
        resultSection.style.display = "none";
    }

    showMessage("Prediction form cleared.", "info");
}



document.addEventListener("DOMContentLoaded", function () {

    // Prediction form
    const predictionForm =
        document.getElementById("predictionForm") ||
        document.getElementById("cropPredictionForm");

    if (predictionForm) {
        predictionForm.addEventListener(
            "submit",
            predictCrop
        );
    }

    const predictButton =
        document.getElementById("predictButton");

    if (predictButton && !predictionForm) {
        predictButton.addEventListener(
            "click",
            predictCrop
        );
    }

    const clearButton =
        document.getElementById("clearButton");

    if (clearButton) {
        clearButton.addEventListener(
            "click",
            clearPredictionForm
        );
    }

    const refreshHistoryButton =
        document.getElementById("refreshHistory");

    if (refreshHistoryButton) {
        refreshHistoryButton.addEventListener(
            "click",
            loadHistory
        );
    }

    checkAPIConnection();
    loadHistory();
    loadDashboardStats();

    updateDateTime();

    console.log("SmartFarm Pro script loaded successfully.");
});



window.showPage = showPage;
window.predictCrop = predictCrop;
window.loadHistory = loadHistory;
window.loadDashboardStats = loadDashboardStats;
window.clearPredictionForm = clearPredictionForm;
window.checkAPIConnection = checkAPIConnection;
