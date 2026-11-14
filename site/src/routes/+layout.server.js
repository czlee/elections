import { BASES, baseOf } from '#lib/bases.js';
import { electorateBases, national } from '#lib/server/data.js';

export function load({ params }) {
	const base = baseOf(/** @type {any} */ (params).base);
	return {
		base,
		hasElectorates: national(base).has_electorates,
		/** Every base year, for the switcher. */
		bases: BASES.map((b) => ({ base: b, hasElectorates: electorateBases.includes(b) }))
	};
}
