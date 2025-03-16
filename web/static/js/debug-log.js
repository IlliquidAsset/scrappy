/**
 * Enhanced debug log functionality
 */

// Debug log state
let debugLogState = {
    lastTimestamp: null,
    pollingEnabled: false,
    pollingInterval: 2000, // ms
    sessionId: null,
    pollingTimer: null,
    maxLogEntries: 100,
    logColors: {
        debug: '#8c9eff',   // Light blue
        info: '#ffffff',    // White
        success: '#69f0ae', // Green
        warning: '#ffd740', // Yellow/amber
        error: '#ff5252'    // Red
    }
};

/**
 * Initialize debug log functionality
 * @param {string} sessionId - Current session ID
 * @param {boolean} enablePolling - Whether to poll for new logs
 */
function initDebugLog(sessionId, enablePolling = true) {
    debugLogState.sessionId = sessionId;

    // Clear any existing polling
    if (debugLogState.pollingTimer) {
        clearInterval(debugLogState.pollingTimer);
        debugLogState.pollingTimer = null;
    }

    // Start polling if enabled
    if (enablePolling) {
        debugLogState.pollingEnabled = true;
        startLogPolling();
    }

    // Add event handling for log controls
    document.getElementById('clearDebugLog')?.addEventListener('click', clearDebugLog);

    // Initial log message
    addToDebugLog(`Debug log initialized for session: ${sessionId.substring(0, 8)}...`, 'info');
}

/**
 * Start polling for new logs
 */
function startLogPolling() {
    if (debugLogState.pollingTimer) {
        return; // Already polling
    }

    // Poll immediately
    pollServerLogs();

    // Set up interval for polling
    debugLogState.pollingTimer = setInterval(pollServerLogs, debugLogState.pollingInterval);

    addToDebugLog("Server log polling started", "debug");
}

/**
 * Stop polling for new logs
 */
function stopLogPolling() {
    if (debugLogState.pollingTimer) {
        clearInterval(debugLogState.pollingTimer);
        debugLogState.pollingTimer = null;
        addToDebugLog("Server log polling stopped", "debug");
    }
}

/**
 * Poll server for new logs
 */
async function pollServerLogs() {
    if (!debugLogState.sessionId) {
        return;
    }

    try {
        // Build URL with since parameter if we have a timestamp
        let url = `/api/logs/${debugLogState.sessionId}`;
        if (debugLogState.lastTimestamp) {
            url += `?since=${encodeURIComponent(debugLogState.lastTimestamp)}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        // Process new logs
        if (data.logs && data.logs.length > 0) {
            // Update the timestamp for next poll
            debugLogState.lastTimestamp = data.logs[data.logs.length - 1].timestamp;

            // Add each log to the display
            data.logs.forEach(log => {
                const timestamp = new Date(log.timestamp).toLocaleTimeString();
                addToDebugLog(log.message, log.level, timestamp);
            });
        }
    } catch (error) {
        console.error('Error polling server logs:', error);
        // Don't show polling errors in the log to avoid spam
    }
}

/**
 * Add message to debug log with proper styling
 * @param {string} message - Log message
 * @param {string} level - Log level (debug, info, success, warning, error)
 * @param {string} timestamp - Optional timestamp (will use current time if not provided)
 */
function addToDebugLog(message, level = 'info', timestamp = null) {
    const debugLog = document.getElementById('debugLog');
    if (!debugLog) return;

    // Create timestamp if not provided
    if (!timestamp) {
        timestamp = new Date().toLocaleTimeString();
    }

    // Get color for level
    const color = debugLogState.logColors[level] || debugLogState.logColors.info;

    // Create log entry with proper styling
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${level}`;
    logEntry.innerHTML = `<span style="color: #8c9eff;">[${timestamp}]</span> <span style="color: ${color};">${message}</span>`;

    // Append to log
    debugLog.appendChild(logEntry);

    // Remove old entries if we exceed the max
    while (debugLog.children.length > debugLogState.maxLogEntries) {
        debugLog.removeChild(debugLog.children[0]);
    }

    // Scroll to bottom
    debugLog.scrollTop = debugLog.scrollHeight;
}

/**
 * Clear debug log
 */
function clearDebugLog() {
    const debugLog = document.getElementById('debugLog');
    if (debugLog) {
        debugLog.innerHTML = '';
        addToDebugLog('Log cleared', 'debug');
    }
}

/**
 * Update the debug log configuration
 * @param {Object} config - New configuration options
 */
function updateDebugLogConfig(config) {
    if (config.pollingInterval) {
        debugLogState.pollingInterval = config.pollingInterval;

        // Restart polling with new interval
        if (debugLogState.pollingEnabled) {
            stopLogPolling();
            startLogPolling();
        }
    }

    if (config.maxLogEntries) {
        debugLogState.maxLogEntries = config.maxLogEntries;
    }
}
