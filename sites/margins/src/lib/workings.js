/**
 * The working for a party's "votes to gain" and "votes to lose": the same Sainte-Laguë logic as scripts/margins/margins.py,
 * but spelled out so a reader can follow it. Only the party's own votes change; every other party's quotients stay put.
 *
 * Seats go to the `to_allocate` (T) highest quotients. A party with n seats gains its (n+1)th if its next quotient beats
 * the (T − n)th highest quotient of the *other* parties (they're left with T − n − 1 seats). It loses its nth if that
 * quotient falls below the (T − n + 1)th highest of the others. The bar is an exact fraction, so votes are whole numbers.
 */

/**
 * @typedef {{ party: string, id: string | null, name: string, seat: number, votes: number, divisor: number }} Quotient
 * @typedef {{
 *   direction: 'gain' | 'lose', n: number, seat: number, divisor: number, rank: number, others: number,
 *   bar: Quotient, product: number, threshold: number, target: number, change: number
 * }} Working
 */

/** Other parties' quotients, highest first. Compared by cross-multiplying, so there's no rounding. */
function othersQuotients(/** @type {any} */ data, /** @type {any} */ p) {
	/** @type {Quotient[]} */
	const qs = [];
	for (const o of data.parties) {
		if (!o.qualified || o.party === p.party) continue;
		for (let s = 1; s <= data.to_allocate; s++) {
			qs.push({ party: o.party, id: o.id, name: o.name, seat: s, votes: o.votes, divisor: 2 * s - 1 });
		}
	}
	return qs.sort((a, b) => b.votes * a.divisor - a.votes * b.divisor);
}

/**
 * @param {any} data One election's JSON.
 * @param {any} p A qualified party in `data.parties`.
 * @param {'gain' | 'lose'} direction
 * @returns {Working | null} null if no number of votes does it (a party with no seat can't lose one).
 */
export function workings(data, p, direction) {
	const n = p.entitlement;
	const T = data.to_allocate;
	if (direction === 'lose' && n === 0) return null;
	const seat = direction === 'gain' ? n + 1 : n;
	const divisor = 2 * seat - 1;
	const rank = direction === 'gain' ? T - n : T - n + 1;
	const bar = othersQuotients(data, p)[rank - 1];
	if (!bar) return null;
	// The party's quotient is votes ÷ divisor, to be compared with bar.votes ÷ bar.divisor.
	const product = (bar.votes * divisor) / bar.divisor;
	if (direction === 'gain') {
		const target = Math.floor(product) + 1; // strictly more: equal is a tie, settled by lot
		return { direction, n, seat, divisor, rank, others: T - n - 1, bar, product, threshold: product, target, change: target - p.votes };
	}
	const target = Math.ceil(product) - 1; // strictly less
	return { direction, n, seat, divisor, rank, others: T - n + 1, bar, product, threshold: product, target, change: p.votes - target };
}
