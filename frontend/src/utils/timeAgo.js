// Friendly relative times for post cards, e.g. "5 minutes ago", "yesterday".
// Older than a week falls back to the date.
const UNITS = [
  ['year', 365 * 24 * 60 * 60],
  ['month', 30 * 24 * 60 * 60],
  ['week', 7 * 24 * 60 * 60],
  ['day', 24 * 60 * 60],
  ['hour', 60 * 60],
  ['minute', 60],
];

const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

export const timeAgo = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const secondsAgo = (Date.now() - date.getTime()) / 1000;
  if (secondsAgo < 60) {
    return 'just now';
  }
  if (secondsAgo > 7 * 24 * 60 * 60) {
    return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }
  const [unit, seconds] = UNITS.find(([, unitSeconds]) => secondsAgo >= unitSeconds);
  return relativeFormat.format(-Math.floor(secondsAgo / seconds), unit);
};

// Full date and time, shown when hovering over a relative time
export const fullDate = (value) => new Date(value).toLocaleString();
