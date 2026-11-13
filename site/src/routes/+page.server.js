import { national, summaries } from '#lib/server/data.js';

export function load() {
	const { parties, seats, house, base, estimate_2026, projected_specials, prelim_total, final_total } = national;
	return {
		national: { parties, seats, house, base, estimate_2026, projected_specials, prelim_total, final_total },
		electorates: summaries()
	};
}
