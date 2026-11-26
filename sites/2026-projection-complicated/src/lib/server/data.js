// Build-time data access. Only server load functions import this, so each
// prerendered page gets just the data it needs, not the whole JSON.
import { BASES } from '#lib/bases.js';

/** @type {Record<string, any>} */
const nationalFiles = import.meta.glob('../data/*/national.json', { eager: true, import: 'default' });
/** @type {Record<string, any>} */
const electorateFiles = import.meta.glob('../data/*/electorates.json', { eager: true, import: 'default' });

for (const base of BASES) {
	if (!nationalFiles[`../data/${base}/national.json`]) throw new Error(`no data/${base}/national.json`);
}

/** The national projection for a base year. */
export function national(/** @type {string} */ base) {
	return nationalFiles[`../data/${base}/national.json`];
}

/** The electorate projections for a base year ([] if it has none). @returns {any[]} */
export function electorates(/** @type {string} */ base) {
	return electorateFiles[`../data/${base}/electorates.json`] ?? [];
}

/** Base years with electorate projections. */
export const electorateBases = BASES.filter((b) => national(b).has_electorates);

/** One row per electorate for the landing page's list. */
export function summaries(/** @type {string} */ base) {
	return electorates(base).map((/** @type {any} */ e) => {
		if (e.omitted) {
			return {
				slug: e.slug, name: e.name, roll: e.roll, omitted: true,
				winner_party: e.winner_party, winner_label: e.winner_label
			};
		}
		const rows = e.candidate.rows;
		const byKey = Object.fromEntries(rows.map((/** @type {any} */ r) => [r.key, r]));
		const w = byKey[e.winner], s = byKey[e.second], pw = byKey[e.prelim_winner];
		return {
			slug: e.slug, name: e.name, roll: e.roll, omitted: false, flips: e.flips,
			winner: w.candidate, winner_party: w.party, second: s.candidate, second_party: s.party,
			prelim_winner: pw.candidate, prelim_winner_party: pw.party,
			prelim_margin: e.prelim_margin, prelim_margin_pct: e.prelim_margin_pct,
			margin: e.margin, margin_pct: e.margin_pct,
			breakeven: e.breakeven
		};
	});
}
