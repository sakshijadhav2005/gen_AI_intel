async function verifyClaim() {
    const claimInput = document.getElementById('claimInput').value;
    const resultDiv = document.getElementById('result');
    const jsonOutput = document.getElementById('jsonOutput');

    if (!claimInput) {
        alert("Please enter a claim.");
        return;
    }

    try {
        const response = await fetch('http://localhost:8000/verdict', {
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

        resultDiv.style.display = 'block';
        jsonOutput.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        console.error('Error verifying claim:', error);
        resultDiv.style.display = 'block';
        jsonOutput.textContent = `Error: ${error.message}`;
    }
}
