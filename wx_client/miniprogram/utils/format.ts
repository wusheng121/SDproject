export function formatTime(value?: string): string {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

export function formatPrice(value: number | string): string {
  return Number(value || 0).toFixed(2);
}
