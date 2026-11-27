import { DATA, ELECTIONS, DEFAULT_ID } from '#lib/elections.js';

/** The home page is the default election's page (2026), like the other sites' home pages. */
export function load() {
	return { election: ELECTIONS.find((e) => e.id === DEFAULT_ID), data: DATA[DEFAULT_ID] };
}
