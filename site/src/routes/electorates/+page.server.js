import { national, summaries } from '#lib/server/data.js';

export function load() {
	return {
		parties: national.parties.map((p) => ({ id: p.id, short: p.short })),
		electorates: summaries()
	};
}
