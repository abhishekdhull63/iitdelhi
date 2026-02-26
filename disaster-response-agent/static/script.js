/**
 * ==========================================================================
 * script.js — NEXUS COMMAND CENTER (Frontend Logic — Gemini Edition)
 * Claw & Shield 2026 Hackathon | ArmorIQ Security Compliant
 * ==========================================================================
 *
 * Vanilla JavaScript — no dependencies.
 *
 * Features:
 *   - Live UTC clock
 *   - Cinematic terminal typewriter loader
 *   - Crypto-secure incident ID generation
 *   - FormData multipart submission (text + optional image)
 *   - Photo upload with preview
 *   - Geolocation + Voice Dictation
 *   - Loading states, error toasts, analysis history
 *
 * Security:
 *   - All user text rendered via textContent (XSS-safe)
 *   - No eval(), no Function(), no document.write()
 */

"use strict";

// ==========================================================================
// DOM ELEMENT REFERENCES
// ==========================================================================
var reportForm = document.getElementById("report-form");
var reportInput = document.getElementById("report-input");
var submitBtn = document.getElementById("submit-btn");
var btnText = document.getElementById("btn-text");
var btnSpinner = document.getElementById("btn-spinner");
var charCounter = document.getElementById("char-counter");

var resultsPlaceholder = document.getElementById("results-placeholder");
var resultsContainer = document.getElementById("results-container");
var severityBadge = document.getElementById("severity-badge");
var actionsList = document.getElementById("actions-list");
var reasoningText = document.getElementById("reasoning-text");
var jsonOutput = document.getElementById("json-output");

var historyList = document.getElementById("history-list");
var historyEmpty = document.getElementById("history-empty");
var clearHistoryBtn = document.getElementById("clear-history-btn");

var errorToast = document.getElementById("error-toast");
var errorToastMsg = document.getElementById("error-toast-msg");
var toastCloseBtn = document.getElementById("toast-close-btn");

var statusIndicator = document.getElementById("status-indicator");
var terminalLoader = document.getElementById("terminal-loader");
var incidentIdEl = document.getElementById("incident-id");
var utcClockEl = document.getElementById("utc-clock");

// Mission cost badge elements
var missionCostBadge = document.getElementById("mission-cost-badge");
var missionCostText = document.getElementById("mission-cost-text");

// Photo upload elements
var uploadBtn = document.getElementById("upload-btn");
var photoInput = document.getElementById("photo-input");
var imagePreview = document.getElementById("image-preview");
var previewThumb = document.getElementById("preview-thumb");
var previewName = document.getElementById("preview-name");
var removeImageBtn = document.getElementById("remove-image");

// ==========================================================================
// CONSTANTS
// ==========================================================================
var API_ENDPOINT = "/api/analyze";
var MAX_CHARS = 1000;
var TOAST_TIMEOUT = 5000;

// Currently selected image file
var selectedImageFile = null;

// ==========================================================================
// LIVE UTC CLOCK
// ==========================================================================
var MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function updateClock() {
    var now = new Date();
    var month = MONTHS[now.getUTCMonth()];
    var day = String(now.getUTCDate()).padStart(2, "0");
    var year = now.getUTCFullYear();
    var h = String(now.getUTCHours()).padStart(2, "0");
    var m = String(now.getUTCMinutes()).padStart(2, "0");
    var s = String(now.getUTCSeconds()).padStart(2, "0");
    utcClockEl.textContent = month + " " + day + ", " + year + " // " + h + ":" + m + ":" + s + " UTC";
}

setInterval(updateClock, 1000);
updateClock();

// ==========================================================================
// ANALYSIS HISTORY
// ==========================================================================
var analysisHistory = [];

// ==========================================================================
// UTILITY: Sleep
// ==========================================================================
function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

// ==========================================================================
// UTILITY: insertAtCursor — Insert text at textarea cursor position
// ==========================================================================
function insertAtCursor(text) {
    var startPos = reportInput.selectionStart;
    var endPos = reportInput.selectionEnd;
    var currentValue = reportInput.value;

    reportInput.value = currentValue.substring(0, startPos)
        + text
        + currentValue.substring(endPos);

    var newPos = startPos + text.length;
    reportInput.selectionStart = newPos;
    reportInput.selectionEnd = newPos;
    reportInput.focus();
    reportInput.dispatchEvent(new Event("input"));
}

// ==========================================================================
// CINEMATIC TERMINAL LOADER
// ==========================================================================
var TERMINAL_MESSAGES = [
    "> Initializing ArmorIQ Shield enforcement layer...",
    "> Scanning input for injection vectors — CLEAR",
    "> Transmitting to Gemini neural core via secure uplink...",
    "> Grounding analysis with real-time search data...",
    "> Applying disaster triage classification model..."
];

function runTerminalSequence() {
    return new Promise(function (resolve) {
        terminalLoader.innerHTML = "";
        terminalLoader.style.display = "block";
        terminalLoader.style.opacity = "1";

        var lineIndex = 0;

        function typeLine() {
            if (lineIndex >= TERMINAL_MESSAGES.length) {
                resolve();
                return;
            }

            var msg = TERMINAL_MESSAGES[lineIndex];
            var charDelay = Math.max(12, Math.floor(800 / msg.length));
            var line = document.createElement("div");
            line.className = "terminal-line typing";
            terminalLoader.appendChild(line);

            var charIdx = 0;

            function typeChar() {
                if (charIdx < msg.length) {
                    line.textContent = msg.substring(0, charIdx + 1);
                    charIdx++;
                    setTimeout(typeChar, charDelay);
                } else {
                    line.classList.remove("typing");
                    line.classList.add("done");
                    lineIndex++;
                    setTimeout(typeLine, 150);
                }
            }

            typeChar();
        }

        typeLine();
    });
}

// ==========================================================================
// INCIDENT ID GENERATOR
// ==========================================================================
function generateIncidentId() {
    var charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    var bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    var id = "";
    for (var i = 0; i < 8; i++) {
        id += charset[bytes[i] % charset.length];
    }
    return id;
}

// ==========================================================================
// CHARACTER COUNTER
// ==========================================================================
reportInput.addEventListener("input", function () {
    var len = this.value.length;
    charCounter.textContent = len + " / " + MAX_CHARS;

    charCounter.classList.remove("near-limit", "at-limit");
    if (len >= MAX_CHARS) {
        charCounter.classList.add("at-limit");
    } else if (len >= MAX_CHARS * 0.85) {
        charCounter.classList.add("near-limit");
    }
});

// ==========================================================================
// ENTER TO SUBMIT — Enter submits, Shift+Enter inserts newline
// ==========================================================================
reportInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        reportForm.requestSubmit();
    }
});

// ==========================================================================
// PHOTO UPLOAD — Trigger file input + preview
// ==========================================================================
if (uploadBtn && photoInput) {
    uploadBtn.addEventListener("click", function () {
        photoInput.click();
    });

    photoInput.addEventListener("change", function () {
        var file = this.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith("image/")) {
            showToast("Please select an image file (JPEG, PNG, WebP).");
            this.value = "";
            return;
        }

        // Validate size (10 MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast("Image exceeds 10 MB size limit.");
            this.value = "";
            return;
        }

        selectedImageFile = file;

        // Show preview
        var reader = new FileReader();
        reader.onload = function (e) {
            previewThumb.src = e.target.result;
            previewName.textContent = file.name;
            imagePreview.style.display = "flex";
        };
        reader.readAsDataURL(file);

        // Update upload button
        uploadBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span>Photo Added</span>';
    });
}

// Remove image handler
if (removeImageBtn) {
    removeImageBtn.addEventListener("click", function () {
        selectedImageFile = null;
        photoInput.value = "";
        imagePreview.style.display = "none";
        previewThumb.src = "";
        uploadBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg><span>Upload Photo</span>';
    });
}

// ==========================================================================
// FORM SUBMISSION — FormData multipart (text + optional image)
// ==========================================================================
reportForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    var reportText = reportInput.value.trim();

    if (!reportText) {
        showToast("Please enter an emergency report before submitting.");
        return;
    }

    if (reportText.length > MAX_CHARS) {
        showToast("Report exceeds " + MAX_CHARS + " character limit.");
        return;
    }

    // ----- Enter loading state & show terminal -----
    setLoading(true);
    submitBtn.style.display = "none";

    var startTime = Date.now();

    try {
        // Build FormData for multipart submission
        var formData = new FormData();
        formData.append("report", reportText);

        if (selectedImageFile) {
            formData.append("image", selectedImageFile);
        }

        // Run fetch and terminal animation in parallel
        var results = await Promise.all([
            fetch(API_ENDPOINT, {
                method: "POST",
                body: formData,
                // No Content-Type header — browser sets multipart boundary
            }),
            runTerminalSequence()
        ]);

        var response = results[0];
        var data = await response.json();

        if (!response.ok) {
            console.groupCollapsed("🚨 NEXUS: Non-OK HTTP Response");
            console.error("Status:", response.status, response.statusText);
            console.error("Body:", JSON.stringify(data, null, 2));
            console.error("Endpoint:", API_ENDPOINT);
            console.groupEnd();
            var errorMsg = (data && data.error) ? data.error : "Service unavailable. Try later.";
            showToast(errorMsg);
            return;
        }

        if (!data.severity || !data.recommended_actions || !data.reasoning) {
            console.error("🚨 NEXUS: Invalid response schema:", JSON.stringify(data, null, 2));
            showToast("Received an unexpected response. Please try again.");
            return;
        }

        // Enforce minimum 2-second total delay
        var elapsed = Date.now() - startTime;
        var remaining = Math.max(0, 2000 - elapsed);
        if (remaining > 0) {
            await sleep(remaining);
        }

        // Fade out terminal
        terminalLoader.style.opacity = "0";
        await sleep(400);

        // Generate incident ID
        var iid = generateIncidentId();
        incidentIdEl.textContent = "Incident #" + iid;
        incidentIdEl.style.display = "inline-block";

        // Render results and record history
        renderResults(data);
        addToHistory(reportText, data);

    } catch (err) {
        console.groupCollapsed("🚨 NEXUS FETCH ERROR");
        console.error("Error:", err);
        console.error("Stack:", err.stack);
        console.error("Endpoint:", window.location.origin + API_ENDPOINT);
        console.groupEnd();
        showToast("Connection failed. Check your network and try again.");
    } finally {
        terminalLoader.style.display = "none";
        terminalLoader.style.opacity = "1";
        terminalLoader.innerHTML = "";
        submitBtn.style.display = "";
        setLoading(false);
    }
});

// ==========================================================================
// RENDER RESULTS
// ==========================================================================
function renderResults(data) {
    resultsPlaceholder.style.display = "none";
    resultsContainer.style.display = "block";
    resultsContainer.style.opacity = "0";
    resultsContainer.style.transform = "translateY(12px)";

    // Trigger reflow for animation
    void resultsContainer.offsetWidth;

    resultsContainer.style.transition = "opacity 0.5s ease, transform 0.5s ease";
    resultsContainer.style.opacity = "1";
    resultsContainer.style.transform = "translateY(0)";

    var severity = data.severity || "Unknown";
    var cssClass = getSeverityCSSClass(severity);
    severityBadge.className = "severity-badge " + cssClass;
    severityBadge.textContent = severity;

    actionsList.innerHTML = "";
    var actions = data.recommended_actions || [];
    actions.forEach(function (action, index) {
        var card = document.createElement("div");
        card.className = "action-card";

        var number = document.createElement("span");
        number.className = "action-number";
        number.textContent = String(index + 1).padStart(2, "0");

        var text = document.createElement("span");
        text.className = "action-text";
        text.textContent = action;

        card.appendChild(number);
        card.appendChild(text);
        actionsList.appendChild(card);
    });

    reasoningText.textContent = data.reasoning || "No reasoning provided.";
    jsonOutput.textContent = JSON.stringify(data, null, 2);

    // Mission Cost Badge
    if (missionCostBadge && missionCostText && data.total_mission_cost != null) {
        var cost = "$" + data.total_mission_cost.toFixed(6);
        var tokens = data.total_tokens || 0;
        missionCostText.textContent = "Mission Cost: " + cost + "  (" + tokens + " tokens)";
        missionCostBadge.style.display = "flex";
    } else if (missionCostBadge) {
        missionCostBadge.style.display = "none";
    }

    // Show Export Brief button
    var exportBtn = document.getElementById("export-brief-btn");
    if (exportBtn) exportBtn.style.display = "inline-flex";

    // Haptic feedback on supported devices
    if (navigator.vibrate) navigator.vibrate([50, 30, 50]);
}

function getSeverityCSSClass(severity) {
    var map = {
        "Critical": "severity-critical",
        "High": "severity-high",
        "Medium": "severity-medium",
        "Low": "severity-low",
        "Error": "severity-error",
    };
    return map[severity] || "severity-medium";
}

// ==========================================================================
// LOADING STATE
// ==========================================================================
function setLoading(loading) {
    if (loading) {
        submitBtn.classList.add("loading");
        submitBtn.disabled = true;
        btnText.textContent = "Analyzing...";
    } else {
        submitBtn.classList.remove("loading");
        submitBtn.disabled = false;
        btnText.textContent = "Analyze Emergency";
    }
}

// ==========================================================================
// ERROR TOAST
// ==========================================================================
var toastTimer = null;

function showToast(message) {
    errorToastMsg.textContent = message;
    errorToast.classList.add("visible");

    if (toastTimer) clearTimeout(toastTimer);

    toastTimer = setTimeout(function () {
        hideToast();
    }, TOAST_TIMEOUT);
}

function hideToast() {
    errorToast.classList.remove("visible");
    if (toastTimer) {
        clearTimeout(toastTimer);
        toastTimer = null;
    }
}

toastCloseBtn.addEventListener("click", hideToast);

// ==========================================================================
// ANALYSIS HISTORY
// ==========================================================================
function addToHistory(reportSnippet, result) {
    var entry = {
        timestamp: new Date().toLocaleString(),
        snippet: reportSnippet.substring(0, 80),
        severity: result.severity || "Unknown",
    };

    analysisHistory.unshift(entry);
    if (analysisHistory.length > 20) {
        analysisHistory.pop();
    }
    renderHistory();
}

function renderHistory() {
    historyList.innerHTML = "";

    if (analysisHistory.length === 0) {
        var emptyMsg = document.createElement("p");
        emptyMsg.className = "history-empty";
        emptyMsg.id = "history-empty";
        emptyMsg.textContent = "No analyses yet. Submit a report to begin.";
        historyList.appendChild(emptyMsg);
        return;
    }

    analysisHistory.forEach(function (entry, index) {
        var card = document.createElement("div");
        card.className = "history-card";

        var dot = document.createElement("span");
        dot.className = "history-severity-dot dot-" + entry.severity.toLowerCase();

        var info = document.createElement("div");
        info.className = "history-info";

        var ts = document.createElement("div");
        ts.className = "history-timestamp";
        ts.textContent = entry.timestamp;

        var snippet = document.createElement("div");
        snippet.className = "history-snippet";
        snippet.textContent = entry.snippet + "...";

        info.appendChild(ts);
        info.appendChild(snippet);

        var label = document.createElement("span");
        label.className = "history-severity-label";
        label.textContent = entry.severity.toUpperCase();
        label.style.color = getSeverityColor(entry.severity);

        // Individual delete button
        var deleteBtn = document.createElement("button");
        deleteBtn.className = "history-delete-btn";
        deleteBtn.title = "Remove this analysis";
        deleteBtn.textContent = "\u00d7";
        deleteBtn.setAttribute("data-index", index);
        deleteBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            var idx = parseInt(this.getAttribute("data-index"));
            analysisHistory.splice(idx, 1);
            renderHistory();
        });

        card.appendChild(dot);
        card.appendChild(info);
        card.appendChild(label);
        card.appendChild(deleteBtn);
        historyList.appendChild(card);
    });
}

function getSeverityColor(severity) {
    var map = {
        "Critical": "#f87171",
        "High": "#fb923c",
        "Medium": "#fbbf24",
        "Low": "#4ade80",
        "Error": "#a1a1aa",
    };
    return map[severity] || "#a1a1aa";
}

// ==========================================================================
// CLEAR HISTORY
// ==========================================================================
clearHistoryBtn.addEventListener("click", function () {
    analysisHistory = [];
    renderHistory();
});

// ==========================================================================
// TRIAGE CHIPS — Insert template at cursor
// ==========================================================================
var triageChips = document.querySelectorAll(".triage-chip");

triageChips.forEach(function (chip) {
    chip.addEventListener("click", function () {
        var template = this.getAttribute("data-template");
        if (!template) return;

        insertAtCursor(template);

        this.style.transform = "scale(0.95)";
        var self = this;
        setTimeout(function () {
            self.style.transform = "scale(1)";
        }, 150);
    });
});

// ==========================================================================
// COPY FOR DISPATCH
// ==========================================================================
var copyReportBtn = document.getElementById("copy-report");
var copiedTooltip = document.getElementById("copied-tooltip");

if (copyReportBtn) {
    copyReportBtn.addEventListener("click", function () {
        var severityText = severityBadge ? severityBadge.textContent : "Unknown";

        var actionsTextList = [];
        var actionCards = document.querySelectorAll(".action-card");
        actionCards.forEach(function (card) {
            var actionText = card.querySelector(".action-text");
            if (actionText) {
                actionsTextList.push("- " + actionText.textContent);
            }
        });

        var textToCopy = "🚨 INCIDENT REPORT 🚨\n";
        textToCopy += "Severity: " + severityText + "\n\n";
        textToCopy += "IMMEDIATE ACTIONS:\n";
        textToCopy += actionsTextList.join("\n");

        var fallbackCopy = function (text) {
            var textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                showCopiedFeedback();
            } catch (err) {
                prompt("Copy to clipboard: Ctrl+C, Enter", text);
            }
            document.body.removeChild(textArea);
        };

        var showCopiedFeedback = function () {
            if (copiedTooltip) {
                copiedTooltip.classList.add("visible");
                setTimeout(function () {
                    copiedTooltip.classList.remove("visible");
                }, 2000);
            }
            if (navigator.vibrate) {
                navigator.vibrate(50);
            }
        };

        if (!navigator.clipboard) {
            fallbackCopy(textToCopy);
            return;
        }

        navigator.clipboard.writeText(textToCopy).then(function () {
            showCopiedFeedback();
        }, function () {
            fallbackCopy(textToCopy);
        });
    });
}

// ==========================================================================
// FEATURE: AUTO-GEOLOCATION
// ==========================================================================
var geoBtn = document.getElementById("geo-btn");

if (geoBtn) {
    if (!navigator.geolocation) {
        geoBtn.disabled = true;
        geoBtn.title = "Geolocation not supported in this browser";
        geoBtn.style.opacity = "0.4";
        geoBtn.style.cursor = "not-allowed";
    }

    geoBtn.addEventListener("click", function () {
        if (!navigator.geolocation) {
            showToast("Geolocation not supported in this browser.");
            return;
        }

        if (geoBtn.disabled) return;
        geoBtn.disabled = true;
        var originalHTML = geoBtn.innerHTML;
        geoBtn.querySelector("span").textContent = "Locating...";

        navigator.geolocation.getCurrentPosition(
            function (position) {
                var lat = position.coords.latitude.toFixed(6);
                var lon = position.coords.longitude.toFixed(6);
                var coordText = " 📍 [Lat: " + lat + ", Lon: " + lon + "]";

                var insertStart = reportInput.selectionStart;
                insertAtCursor(coordText);

                reportInput.selectionStart = insertStart;
                reportInput.selectionEnd = insertStart + coordText.length;
                reportInput.focus();

                geoBtn.querySelector("span").textContent = "Added!";
                setTimeout(function () {
                    geoBtn.innerHTML = originalHTML;
                    geoBtn.disabled = false;
                }, 2000);
            },
            function (err) {
                var msg = "Location denied — enter manually.";
                if (err.code === 2) msg = "Location unavailable — try again.";
                if (err.code === 3) msg = "Location timed out — try again.";
                showToast(msg);

                geoBtn.innerHTML = originalHTML;
                geoBtn.disabled = false;
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000,
            }
        );
    });
}

// ==========================================================================
// FEATURE: VOICE DICTATION (Speech-to-Text)
// ==========================================================================
var dictateBtn = document.getElementById("dictate-btn");
var recognition = null;
var isListening = false;

var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (dictateBtn) {
    if (!SpeechRecognition) {
        dictateBtn.disabled = true;
        dictateBtn.title = "Voice input not supported in this browser";
        dictateBtn.style.opacity = "0.4";
        dictateBtn.style.cursor = "not-allowed";
    } else {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-IN";

        var dictationInsertPos = 0;
        var lastTranscriptLength = 0;

        recognition.onstart = function () {
            isListening = true;
            dictateBtn.querySelector("span").textContent = "Listening...";
            dictateBtn.classList.add("dictate-pulse");
        };

        recognition.onresult = function (event) {
            var transcript = "";
            for (var i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }

            if (transcript) {
                var currentValue = reportInput.value;
                var before = currentValue.substring(0, dictationInsertPos);
                var after = currentValue.substring(dictationInsertPos + lastTranscriptLength);

                reportInput.value = before + transcript + after;
                lastTranscriptLength = transcript.length;

                var newPos = dictationInsertPos + transcript.length;
                reportInput.selectionStart = newPos;
                reportInput.selectionEnd = newPos;
                reportInput.dispatchEvent(new Event("input"));
            }
        };

        recognition.onend = function () {
            isListening = false;
            dictateBtn.classList.remove("dictate-pulse");
            dictateBtn.querySelector("span").textContent = "Done!";
            lastTranscriptLength = 0;

            setTimeout(function () {
                dictateBtn.querySelector("span").textContent = "Dictate";
            }, 2000);
        };

        recognition.onerror = function (event) {
            isListening = false;
            dictateBtn.classList.remove("dictate-pulse");
            dictateBtn.querySelector("span").textContent = "Dictate";
            lastTranscriptLength = 0;

            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                showToast("Mic access denied — check browser permissions.");
            } else if (event.error === "no-speech") {
                showToast("No speech detected — try again.");
            } else if (event.error !== "aborted") {
                showToast("Voice input error — try again.");
            }
        };

        dictateBtn.addEventListener("click", function () {
            if (!recognition) return;

            if (isListening) {
                recognition.stop();
            } else {
                dictationInsertPos = reportInput.selectionStart;
                lastTranscriptLength = 0;
                reportInput.focus();

                try {
                    recognition.start();
                } catch (e) {
                    showToast("Could not start voice input. Try again.");
                }
            }
        });
    }
}

// ==========================================================================
// FEATURE: 1-CLICK GPS TELEMETRY INJECTION
// ==========================================================================
var gpsInjectBtn = document.getElementById("gps-inject-btn");

function injectGPS() {
    if (!gpsInjectBtn) return;

    var originalText = gpsInjectBtn.textContent;
    gpsInjectBtn.textContent = "📍 Locating...";
    gpsInjectBtn.disabled = true;

    if (!navigator.geolocation) {
        reportInput.value += "\n[Live Telemetry: OFFLINE - Manual Entry Required]";
        reportInput.dispatchEvent(new Event("input"));
        gpsInjectBtn.textContent = "⚠️ GPS Offline";
        setTimeout(function () {
            gpsInjectBtn.textContent = originalText;
            gpsInjectBtn.disabled = false;
        }, 2000);
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function (position) {
            var lat = position.coords.latitude.toFixed(4);
            var lon = position.coords.longitude.toFixed(4);
            reportInput.value += "\n[Live Telemetry: " + lat + "° N, " + lon + "° E]";
            reportInput.dispatchEvent(new Event("input"));
            gpsInjectBtn.textContent = "✅ GPS Injected";
            setTimeout(function () {
                gpsInjectBtn.textContent = originalText;
                gpsInjectBtn.disabled = false;
            }, 2000);
        },
        function () {
            reportInput.value += "\n[Live Telemetry: OFFLINE - Manual Entry Required]";
            reportInput.dispatchEvent(new Event("input"));
            gpsInjectBtn.textContent = "⚠️ GPS Offline";
            setTimeout(function () {
                gpsInjectBtn.textContent = originalText;
                gpsInjectBtn.disabled = false;
            }, 2000);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
}

if (gpsInjectBtn) {
    gpsInjectBtn.addEventListener("click", injectGPS);
}

// ==========================================================================
// DRONE FEED TIMESTAMP TICKER
// ==========================================================================
var droneTs = document.getElementById("drone-timestamp");
if (droneTs) {
    setInterval(function () {
        var d = new Date();
        droneTs.textContent = d.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    }, 1000);
}
