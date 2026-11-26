import { error } from '@sveltejs/kit';
import { electorates, national } from '#lib/server/data.js';

export function entries() {
	return electorates.map((e) => ({ slug: e.slug }));
}

export function load({ params }) {
	const electorate = electorates.find((e) => e.slug === params.slug);
	if (!electorate) error(404, 'No such electorate');
	return { electorate, parties: national.parties, sources: national.sources };
}
