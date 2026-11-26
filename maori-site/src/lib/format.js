import { format } from 'd3-format';

const int = format(',.0f');
/** Whole votes, e.g. 1,234. */
export const votes = (/** @type {number} */ v) => int(Math.round(v));
/** Signed whole votes, e.g. +1,234 or −56. */
export const signed = (/** @type {number} */ v) =>
	(Math.round(v) > 0 ? '+' : Math.round(v) < 0 ? '−' : '±') + int(Math.abs(Math.round(v)));
/** A share (0–1) as a percentage, e.g. 29.37%. */
export const pct = (/** @type {number} */ s, digits = 2) => (100 * s).toFixed(digits) + '%';
/** A margin between two shares (0–1) in percentage points, e.g. 12.34 pp. */
export const points = (/** @type {number} */ d, digits = 2) => (100 * d).toFixed(digits) + ' pp';
/** A change in share (0–1) in percentage points, e.g. +0.62 pp. */
export const pp = (/** @type {number} */ d, digits = 2) =>
	(d > 0 ? '+' : d < 0 ? '−' : '±') + Math.abs(100 * d).toFixed(digits) + ' pp';
/** A multiplier, e.g. 0.884. */
export const mult = (/** @type {number} */ m) => m.toFixed(3);
/** "SURNAME, Given" → "Given SURNAME", keeping the surname's case. */
export const candidateName = (/** @type {string} */ c) => {
	const i = c.indexOf(', ');
	return i < 0 ? c : c.slice(i + 2) + ' ' + c.slice(0, i);
};
