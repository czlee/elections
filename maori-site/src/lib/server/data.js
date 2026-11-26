// Build-time data access, for server load functions only, so each
// prerendered page gets just the data it needs.
import nationalData from '../data/national.json';
import electorateData from '../data/electorates.json';

/** @type {any} */
export const national = nationalData;
/** @type {any[]} */
export const electorates = electorateData;

/** One row per general electorate, for the landing page's map and the list. */
export function summaries() {
	return electorates.map((e) => {
		const byParty = (/** @type {string | null} */ p) => e.candidates.find((/** @type {any} */ c) => c.party === p);
		const top = e.candidates; // sorted by new total
		const prelimSorted = e.candidates.toSorted((/** @type {any} */ a, /** @type {any} */ b) => b.prelim - a.prelim);
		return {
			slug: e.slug, name: e.name, flips: e.flips,
			prelim_winner: prelimSorted[0].candidate, prelim_winner_party: prelimSorted[0].party,
			prelim_second: prelimSorted[1].candidate, prelim_second_party: prelimSorted[1].party,
			prelim_margin: e.margin_prelim, prelim_margin_pct: e.margin_prelim_pct,
			winner: top[0].candidate, winner_party: top[0].party,
			second: top[1].candidate, second_party: top[1].party,
			margin: e.margin_new, margin_pct: e.margin_new_pct,
			added_total: e.added_total, tpm_votes: e.tpm_votes, breakeven: e.labour_breakeven,
			labour: byParty('labour')?.candidate ?? null
		};
	});
}
