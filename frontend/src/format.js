// Small shared formatting helpers, used by the result components so every
// number is rounded the same way (1 decimal for rates, plain integers for counts).
export function formatPer1000(value) {
  return Number(value).toFixed(1);
}

export function formatCount(value) {
  return Number(value).toLocaleString();
}

// Renders an ISO timestamp (e.g. from the backend's created_at) in the
// user's locale, or "-" if it's missing/unparseable.
export function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}
