import { national, summaries } from '#lib/server/data.js';

export function load() {
	return { parties: national.parties, electorates: summaries() };
}
