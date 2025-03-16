/**
 * Directly monitor for job confirmation requests
 * This is an alternative to polling the standard job status endpoint
 */
async function monitorForConfirmation(jobId, sessionId) {
    if (!jobId) return;

    try {
        // Make direct request to our local confirmation check endpoint
        const response = await fetch(`/api/jobs/${jobId}/status`);
        if (!response.ok) {
            console.error('Failed to check confirmation status');
            return;
        }

        const data = await response.json();

        // Check if confirmation is required
        if (data.status === 'confirmation_required') {
            // Update UI status badge
            const statusBadge = document.getElementById('jobStatus');
            statusBadge.textContent = 'Confirmation Required';
            statusBadge.className = 'badge bg-warning';

            // Log in debug pane
            if (typeof addToDebugLog === 'function') {
                addToDebugLog(`Confirmation required: "${data.owner}" matches "${data.match}"?`, 'warning');
            }

            // Show confirmation dialog
            if (typeof handleMatchConfirmation === 'function') {
                // Suspend polling
                if (typeof isPollingSuspended !== 'undefined') {
                    isPollingSuspended = true;
                }

                // Show confirmation dialog
                await handleMatchConfirmation(data.owner, data.match, data.confirmation_id);

                // Hide loading dialog if showing
                if (typeof hideLoadingModal === 'function') {
                    hideLoadingModal();
                }
            } else {
                console.error('handleMatchConfirmation function not available');
            }

            return true;
        }

        return false;
    } catch (error) {
        console.error('Error monitoring for confirmation:', error);
        return false;
    }
}
