/* =========================================================
   GITHUB PAGES VERSION
   Direct Gemini REST API — no Flask required for the website UI.
   The visitor's API key is kept only in this browser tab and is
   sent directly to Google Gemini. Never hard-code a real key here.
   ========================================================= */

const GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash"
];

let selectedMode = "short";
let configured = false;
let lastSummary = "";
let lastStats = null;

const apiKeyInput = document.getElementById("apiKey");
const sourceText = document.getElementById("sourceText");
const output = document.getElementById("output");
const summarizeBtn = document.getElementById("summarizeBtn");
const connectBtn = document.getElementById("connectBtn");
const keyMessage = document.getElementById("keyMessage");

const footerDate = document.getElementById("footerDate");
if (footerDate) {
    footerDate.textContent = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric"
    }).format(new Date());
}

function updateStats() {
    const text = sourceText.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    const sentences = text.trim()
        ? (text.match(/[.!?।]+/g) || []).length
        : 0;

    document.getElementById("wordCount").textContent = words.toLocaleString();
    document.getElementById("charCount").textContent = chars.toLocaleString();
    document.getElementById("sentenceCount").textContent = sentences.toLocaleString();
}

function selectMode(button) {
    document.querySelectorAll(".mode-btn")
        .forEach(btn => btn.classList.remove("active"));

    button.classList.add("active");
    selectedMode = button.dataset.mode;
}

function showKeyMessage(message, type = "") {
    keyMessage.textContent = message;
    keyMessage.className = "key-message " + type;
}

function setOutput(text) {
    if (!text) {
        output.innerHTML =
            '<div class="output-placeholder">Your AI-generated summary will appear here.</div>';
        return;
    }

    output.textContent = text;
}

function showResultStats(stats) {
    if (!stats) return;

    document.getElementById("resultStats").style.display = "grid";
    document.getElementById("originalWords").textContent =
        Number(stats.original_words || 0).toLocaleString();
    document.getElementById("summaryWords").textContent =
        Number(stats.summary_words || 0).toLocaleString();
    document.getElementById("savedWords").textContent =
        Number(stats.words_saved || 0).toLocaleString();
    document.getElementById("reduction").textContent =
        Number(stats.reduction_percentage || 0).toFixed(1) + "%";
}

function countWords(text) {
    return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function buildPrompt(mode, text) {
    const common = `
You are a professional AI text summarization engine.
Summarize ONLY the supplied source text.
Do not invent facts, examples, names, dates, numbers, causes, effects, or conclusions.
Preserve important technical terms and factual details.
Use clear, natural, exam-friendly language where appropriate.
Do not use markdown heading symbols such as #.
Source text:

${text}
`;

    const prompts = {
        short: `
${common}
Create a short, highly accurate and polished summary.
Keep the central idea, important facts, names, dates, numbers, causes, effects and conclusions.
Remove repetition and filler.
Return 1–2 compact paragraphs.
`,

        detailed: `
${common}
Create a detailed and comprehensive summary.
Organize the important ideas in a logical order.
Preserve definitions, concepts, facts, examples, processes, causes, effects, dates and numbers.
Use short paragraphs and clear section wording.
`,

        bullet: `
${common}
Create a structured study summary using ONLY this exact format:

1. Main Section
   i. Direct subpoint
   ii. Direct subpoint
       a. Supporting detail
       b. Supporting detail

2. Next Main Section
   i. Direct subpoint

Rules:
Use 1., 2., 3. for main sections.
Use i., ii., iii. for direct subpoints.
Use a., b., c. for supporting subpoints.
NEVER use *, -, or • as bullets.
Keep important facts, definitions, examples, names, dates, numbers and conclusions.
`,

        exam: `
${common}
Create exam-ready notes using ONLY this exact hierarchy:

1. Main Topic
   i. Definition / Core Concept
   ii. Important Point
       a. Supporting detail
       b. Example

2. Next Topic
   i. Important Point

Rules:
Main sections MUST use 1., 2., 3., etc.
Direct subpoints MUST use i., ii., iii., etc.
Supporting subpoints MUST use a., b., c., etc.
NEVER use *, -, or •.
Include definitions, core concepts, features, processes, advantages, limitations, examples/applications, causes/effects, names, dates and numbers when present in the source.
Make the notes easy to revise before an exam.
Do not add outside information.
`
    };

    return prompts[mode] || prompts.short;
}

async function geminiRequest(apiKey, model, prompt) {
    const url =
        `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "x-goog-api-key": apiKey
        },
        body: JSON.stringify({
            contents: [
                {
                    role: "user",
                    parts: [{ text: prompt }]
                }
            ]
        })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const message = data?.error?.message || `Gemini request failed (${response.status}).`;
        const error = new Error(message);
        error.status = response.status;
        throw error;
    }

    const text = data?.candidates?.[0]?.content?.parts
        ?.map(part => part.text || "")
        .join("")
        .trim();

    if (!text) {
        throw new Error("Gemini returned an empty response.");
    }

    return text;
}

async function generateWithRetry(apiKey, prompt) {
    let lastError = null;

    for (const model of GEMINI_MODELS) {
        for (const delay of [0, 2000, 4000, 8000]) {
            if (delay) {
                await new Promise(resolve => setTimeout(resolve, delay));
            }

            try {
                const result = await geminiRequest(apiKey, model, prompt);
                return { text: result, model };
            } catch (error) {
                lastError = error;

                // Authentication / permission / invalid request errors
                // should not be retried across every model.
                if ([400, 401, 403].includes(error.status)) {
                    throw error;
                }

                // Retry transient server overloads such as 500/502/503/504.
                if (![429, 500, 502, 503, 504].includes(error.status)) {
                    throw error;
                }
            }
        }
    }

    throw lastError || new Error("Gemini is temporarily unavailable.");
}

async function connectGemini() {
    const key = apiKeyInput.value.trim();

    if (!key) {
        configured = false;
        showKeyMessage("Please enter your Gemini API key.", "error");
        return;
    }

    connectBtn.disabled = true;
    connectBtn.textContent = "CHECKING...";
    showKeyMessage("Checking Gemini API access...", "");

    try {
        const response = await fetch(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash",
            {
                method: "GET",
                headers: {
                    "x-goog-api-key": key
                }
            }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data?.error?.message || `Gemini API check failed (${response.status}).`
            );
        }

        configured = true;
        showKeyMessage("Gemini connected successfully.", "success");
    } catch (error) {
        configured = false;
        showKeyMessage(error.message || "Gemini API connection failed.", "error");
    } finally {
        connectBtn.disabled = false;
        connectBtn.textContent = "CONNECT";
    }
}

async function summarize() {
    const text = sourceText.value.trim();

    if (!text) {
        setOutput("Please paste some text first.");
        return;
    }

    const key = apiKeyInput.value.trim();

    if (!key) {
        showKeyMessage("Please enter your Gemini API key first.", "error");
        return;
    }

    if (!configured) {
        try {
            await connectGemini();
        } catch (_) {}

        if (!configured) return;
    }

    summarizeBtn.disabled = true;
    summarizeBtn.innerHTML = '<span class="loader"></span> GENERATING...';
    setOutput("");

    try {
        const prompt = buildPrompt(selectedMode, text);
        const result = await generateWithRetry(key, prompt);

        lastSummary = result.text;

        const originalWords = countWords(text);
        const summaryWords = countWords(lastSummary);
        const wordsSaved = Math.max(0, originalWords - summaryWords);
        const reduction = originalWords
            ? (wordsSaved / originalWords) * 100
            : 0;

        lastStats = {
            original_words: originalWords,
            summary_words: summaryWords,
            words_saved: wordsSaved,
            reduction_percentage: reduction
        };

        setOutput(lastSummary);
        showResultStats(lastStats);
        showKeyMessage(`Generated with ${result.model}.`, "success");
    } catch (error) {
        configured = false;

        const message = error?.message || "Summary generation failed.";
        setOutput(`Gemini summarization failed: ${message}`);
        showKeyMessage("Gemini request failed. Check your key or try again.", "error");
    } finally {
        summarizeBtn.disabled = false;
        summarizeBtn.textContent = "GENERATE SUMMARY";
    }
}

async function copySummary() {
    if (!lastSummary) {
        alert("Generate a summary first.");
        return;
    }

    try {
        await navigator.clipboard.writeText(lastSummary);
        alert("Summary copied.");
    } catch (_) {
        alert("Copy failed. Please select and copy the text manually.");
    }
}

function downloadSummaryPDF() {
    if (!lastSummary) {
        alert("Generate a summary first.");
        return;
    }

    // GitHub Pages has no Python/reportlab server. Use the browser's
    // native print dialog so the user can choose "Save as PDF".
    const oldTitle = document.title;
    document.title = "AI_Text_Summary";
    window.print();
    document.title = oldTitle;
}

function downloadText() {
    if (!lastSummary) {
        alert("Generate a summary first.");
        return;
    }

    const blob = new Blob([lastSummary], {
        type: "text/plain;charset=utf-8"
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "AI_Summary.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
}

function loadSample() {
    sourceText.value = `Artificial intelligence is a branch of computer science that focuses on creating systems capable of performing tasks that normally require human intelligence. These tasks include learning, reasoning, problem solving, understanding natural language, recognizing patterns and making decisions.

Modern AI systems use techniques such as machine learning and deep learning to process large amounts of information. Machine learning allows a system to learn patterns from data instead of relying entirely on manually written rules. Deep learning uses neural networks with multiple layers and has become important for image recognition, speech processing and natural language applications.

AI is now used in many areas including education, healthcare, finance, transportation, manufacturing and customer service. However, responsible development is important because AI systems can produce incorrect results, reflect biases in training data and create privacy or security concerns.`;

    updateStats();
}

function clearSource() {
    sourceText.value = "";
    updateStats();

    lastSummary = "";
    lastStats = null;
    configured = false;

    document.getElementById("resultStats").style.display = "none";
    setOutput("");
}

// Do not persist the API key in localStorage/sessionStorage.
// It stays only in the current page memory.
updateStats();
