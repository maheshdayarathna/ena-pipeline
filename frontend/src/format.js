// Small shared formatting helpers, used by the result components so every
// number is rounded the same way (1 decimal for rates, plain integers for counts).
export function formatPer1000(value) {
  return Number(value).toFixed(1);
}

export function formatCount(value) {
  return Number(value).toLocaleString();
}
