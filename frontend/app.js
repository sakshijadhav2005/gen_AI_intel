// Dynamically set API_BASE_URL for Render.com deployment vs. local testing
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : 'https://vericheck-api.onrender.com'; // Replace with your actual Render API URL

async function verifyClaim() {
    const claimInput = document.getElementById('claimInput').value;

    if (!claimInput) {
        alert("Please enter a claim.");
        return;
    }

    showLoader();

    try {
        const response = await fetch(`${API_BASE_URL}/verdict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ claim_text: claimInput })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderResult(data);

    } catch (error) {
        console.error('Error verifying claim:', error);
        renderError(error.message);
    } finally {
        hideLoader();
    }
}

async function scrapeUrl() {
    const claimInput = document.getElementById('claimInput').value;

    if (!claimInput || !claimInput.startsWith('http')) {
        alert("Please enter a valid URL (starting with http:// or https://) for MCP scraping.");
        return;
    }

    showLoader();

    try {
        const response = await fetch(`${API_BASE_URL}/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: claimInput })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Show the scraped text in the input box for verification
        document.getElementById('claimInput').value = data.scraped_text;
        alert("URL Scraped via MCP! The extracted text has been placed in the input box. You can now verify it.");

    } catch (error) {
        console.error('Error scraping URL:', error);
        alert(`Error scraping URL: ${error.message}`);
    } finally {
        hideLoader();
    }
}

function renderResult(data) {
    const resultDiv = document.getElementById('result');
    const jsonOutput = document.getElementById('jsonOutput');
    const verdictLabel = document.getElementById('verdictLabel');
    const confidenceScore = document.getElementById('confidenceScore');
    const tierReached = document.getElementById('tierReached');
    const explanationText = document.getElementById('explanationText');
    const evidenceList = document.getElementById('evidenceList');

    resultDiv.style.display = 'block';

    // Update Badge
    verdictLabel.textContent = data.label;
    verdictLabel.className = `badge ${data.label}`;

    // Update Scores
    confidenceScore.textContent = `${(data.confidence * 100).toFixed(1)}%`;
    tierReached.textContent = data.tier_reached;

    // Update Text
    explanationText.textContent = data.explanation || "No explanation provided.";

    // Update Evidence
    evidenceList.innerHTML = '';
    if (data.evidence && data.evidence.length > 0) {
        data.evidence.forEach(ev => {
            const div = document.createElement('div');
            div.className = 'evidence-item';
            div.innerHTML = `
                <p>"${ev.text}"</p>
                <div class="evidence-meta">
                    <span>Source: ${ev.source || 'Unknown'}</span>
                    <span>Date: ${ev.date || 'Unknown'}</span>
                </div>
            `;
            evidenceList.appendChild(div);
        });
    } else {
        evidenceList.innerHTML = '<p style="color: var(--text-secondary);">No direct evidence found in database.</p>';
    }

    // Raw JSON
    jsonOutput.textContent = JSON.stringify(data, null, 2);
    jsonOutput.style.display = 'none'; // hidden by default
}

function renderError(message) {
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';

    document.getElementById('verdictLabel').textContent = 'ERROR';
    document.getElementById('verdictLabel').className = 'badge FALSE';
    document.getElementById('explanationText').textContent = message;
    document.getElementById('evidenceList').innerHTML = '';
    document.getElementById('jsonOutput').textContent = '';
}

function toggleJson() {
    const jsonOutput = document.getElementById('jsonOutput');
    jsonOutput.style.display = jsonOutput.style.display === 'none' ? 'block' : 'none';
}

function showLoader() {
    document.getElementById('loader').style.display = 'block';
    document.getElementById('result').style.display = 'none';
    document.getElementById('verifyBtn').disabled = true;
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
    document.getElementById('verifyBtn').disabled = false;
}

// Allow Enter key to submit
document.getElementById("claimInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        verifyClaim();
    }
});
