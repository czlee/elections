import { error } from '@sveltejs/kit';
import { DATA, ELECTIONS } from '#lib/elections.js';

export const entries = () => ELECTIONS.map((e) => ({ election: e.id }));

export function load({ params }) {
	const data = DATA[params.election];
	if (!data) error(404, 'No such election');
	return { election: ELECTIONS.find((e) => e.id === params.election), data };
}
