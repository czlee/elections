const int = new Intl.NumberFormat('en-NZ', { maximumFractionDigits: 0 });
/** Whole votes, e.g. 1,234. */
export const votes = (/** @type {number} */ v) => int.format(Math.round(v));
/** A signed seat change, e.g. +1 or −2. */
export const delta = (/** @type {number} */ d) => (d > 0 ? '+' : '−') + Math.abs(d);
/** A share (0–1) as a percentage, e.g. 29.37%. */
export const pct = (/** @type {number} */ s, digits = 2) => (100 * s).toFixed(digits) + '%';

/** "SURNAME, Given" → "Given Surname" (surnames come in capitals, sometimes with a Mc/Mac prefix). */
export function candidateName(/** @type {string} */ c) {
	const i = c.indexOf(',');
	if (i < 0) return c;
	const surname = c
		.slice(0, i)
		.trim()
		.toLowerCase()
		.replace(/(^|[\s'’-])(\p{L})/gu, (_, sep, ch) => sep + ch.toUpperCase())
		.replace(/^(Mc)(\p{L})/u, (_, mc, ch) => mc + ch.toUpperCase());
	return c.slice(i + 1).trim() + ' ' + surname;
}
