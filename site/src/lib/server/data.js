// Build-time data access. Only server load functions import this, so each
// prerendered page gets just the data it needs, not the whole JSON.
import nationalJson from '#lib/data/2023/national.json';
import electoratesJson from '#lib/data/2023/electorates.json';

/** @type {any} */
export const national = nationalJson;
/** @type {any[]} */
export const electorates = electoratesJson;
/** One row per electorate for the landing page's list. */
export function summaries() {
	return electorates.map((/** @type {any} */ e) => {
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
