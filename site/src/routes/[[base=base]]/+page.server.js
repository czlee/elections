import { baseOf } from '#lib/bases.js';
import { national as getNational, summaries } from '#lib/server/data.js';

export function load({ params }) {
	const base = baseOf(params.base);
	const { parties, seats, house, entitlement, estimate_2026, projected_specials, prelim_total, final_total } =
		getNational(base);
	return {
		national: { parties, seats, house, entitlement, base, estimate_2026, projected_specials, prelim_total, final_total },
		electorates: summaries(base)
	};
}
