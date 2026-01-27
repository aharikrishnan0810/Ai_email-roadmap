/**
 * AI Placement Email Platform - Shared Logic
 */

// Helper to format dates
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

console.log("🚀 AI Intelligence UI Initialized");
