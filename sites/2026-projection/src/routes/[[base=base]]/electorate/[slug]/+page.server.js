import { error } from '@sveltejs/kit';
import { DEFAULT_BASE, baseOf } from '#lib/bases.js';
import { electorateBases, electorates, national } from '#lib/server/data.js';

export function entries() {
	return electorateBases.flatMap((base) =>
		electorates(base).map((e) => ({ base: base === DEFAULT_BASE ? undefined : base, slug: e.slug }))
	);
}

export function load({ params }) {
	const base = baseOf(params.base);
	const electorate = electorates(base).find((e) => e.slug === params.slug);
	if (!electorate) error(404, 'No such electorate');
	const n = national(base);
	const names = Object.fromEntries([...n.parties, ...n.base_parties].map((p) => [p.id, p.short]));
	return { electorate, names, base };
}
