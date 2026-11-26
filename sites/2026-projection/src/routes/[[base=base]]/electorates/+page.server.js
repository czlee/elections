import { error } from '@sveltejs/kit';
import { baseOf } from '#lib/bases.js';
import { national, summaries } from '#lib/server/data.js';

export function load({ params }) {
	const base = baseOf(params.base);
	const n = national(base);
	if (!n.has_electorates) error(404, `No electorate projections from ${base}`);
	return {
		parties: n.parties.map((/** @type {any} */ p) => ({ id: p.id, short: p.short })),
		electorates: summaries(base)
	};
}
