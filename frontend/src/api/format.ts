// Display formatters shared by pages. Money is integer rupees (contract rule).

export function formatPrice(n: number): string {
  if (n < 1000) return `₹${n}`;
  const k = n / 1000;
  return `₹${Number.isInteger(k) ? k : k.toFixed(1)}K`;
}

export function formatBudget(min: number, max: number | null): string {
  return max === null ? `${formatPrice(min)}+` : `${formatPrice(min)} – ${formatPrice(max)}`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-01-05" → "Jan 5, 2026". Parsed by parts so no timezone shift. */
export function formatDate(d: string): string {
  const [y, m, day] = d.split('-').map(Number);
  return `${MONTHS[m - 1]} ${day}, ${y}`;
}

export function relativeTime(iso: string, now: Date = new Date()): string {
  const seconds = Math.round((now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const units: [number, string][] = [[60 * 60 * 24, 'day'], [60 * 60, 'hour'], [60, 'minute']];
  for (const [size, name] of units) {
    const n = Math.floor(seconds / size);
    if (n >= 1) return `${n} ${name}${n === 1 ? '' : 's'} ago`;
  }
  return 'just now';
}
