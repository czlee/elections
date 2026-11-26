/** The data (margins.json from scripts/margins/margins.py) for every election, keyed by its directory name. */
const files = /** @type {Record<string, any>} */ (
	import.meta.glob('./data/*.json', { eager: true, import: 'default' })
);

/** @type {Record<string, any>} */
export const DATA = Object.fromEntries(
	Object.entries(files).map(([path, d]) => [path.replace(/^.*\/(.*)\.json$/, '$1'), d])
);

/** Election pages, oldest first. A "-prelim" directory is that election's preliminary count. */
export const ELECTIONS = Object.keys(DATA)
	.sort()
	.map((id) => {
		const year = id.slice(0, 4);
		const prelim = id.endsWith('-prelim');
		const official = `https://www.electionresults.govt.nz/electionresults_${year}${prelim ? '_preliminary' : ''}/`;
		return { id, year, prelim, label: prelim ? `${year} (preliminary)` : year, official };
	});

/** The Electoral Commission's page for an electorate (by its id), under an election's official results site. */
export const electorateUrl = (/** @type {string} */ official, /** @type {number} */ id) =>
	`${official}electorate-details-${String(id).padStart(2, '0')}.html`;

/** Elections that have a final result, for the placeholder's links. */
export const PAST = ELECTIONS.filter((e) => !e.prelim);

/** A party's key for colours and seat charts: its party_id, or "independent" for no party. */
export const partyKey = (/** @type {{id?: string | null}} */ p) => p.id ?? 'independent';

/**
 * A House (from margins.json) as the Parliament chart takes it: seats by party key.
 * @param {{parties: any[], other_electorates: number}} house
 */
export function seatsOf(house) {
	/** @type {Record<string, {total: number, electorate: number}>} */
	const seats = {};
	for (const p of house.parties) seats[partyKey(p)] = { total: p.seats, electorate: p.electorates };
	if (house.other_electorates) seats.independent = { total: house.other_electorates, electorate: house.other_electorates };
	return seats;
}
