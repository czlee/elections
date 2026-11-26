/**
 * Parties whose seats are their electorates in both counts (they won more
 * electorates than their Sainte-Laguë share: overhang), where the share or
 * the electorates change. For these, a Sainte-Laguë change doesn't change
 * their seats; the overhang absorbs it.
 * @param {any} nat national.json (needs seats and entitlement)
 * @returns {{id: string, slFrom: number, slTo: number, elecFrom: number, elecTo: number}[]}
 */
export function overhangParties(nat) {
	return Object.keys(nat.seats.projected)
		.map((id) => {
			const p = nat.seats.prelim[id], f = nat.seats.projected[id];
			return {
				id,
				slFrom: nat.entitlement.prelim[id] ?? 0,
				slTo: nat.entitlement.projected[id] ?? 0,
				elecFrom: p?.electorate ?? 0,
				elecTo: f.electorate,
				overhang: p && p.total === p.electorate && f.total === f.electorate &&
					p.electorate > (nat.entitlement.prelim[id] ?? 0) && f.electorate > (nat.entitlement.projected[id] ?? 0)
			};
		})
		.filter((p) => p.overhang && (p.slFrom !== p.slTo || p.elecFrom !== p.elecTo))
		.map(({ overhang, ...p }) => p);
}

/**
 * One sentence on how the overhang absorbs an overhang party's changes.
 * @param {ReturnType<typeof overhangParties>[number]} a
 * @param {string} name the party's short name
 */
export function overhangSentence(a, name) {
	const share =
		a.slFrom === a.slTo
			? `${name}’s Sainte-Laguë share stays at ${a.slTo}`
			: `${name}’s Sainte-Laguë share ${a.slTo < a.slFrom ? 'drops' : 'rises'} from ${a.slFrom} to ${a.slTo}`;
	if (a.elecFrom === a.elecTo) {
		return `${share}, but it keeps its ${a.elecTo} seats because it won ${a.elecTo} electorates: the overhang ${
			a.slTo < a.slFrom ? 'grows' : 'shrinks'} instead.`;
	}
	return `${share}, but its seats follow its electorates, which are more than its share either way: it wins ${
		a.elecTo} electorates, ${a.elecTo < a.elecFrom ? 'down' : 'up'} from ${a.elecFrom}.`;
}

/**
 * Each party's change in Sainte-Laguë share of the 120 (before electorates
 * are taken into account), largest gains first then losses, as [id, change].
 * @param {any} nat
 * @returns {[string, number][]}
 */
export function slChanges(nat) {
	const ids = new Set([...Object.keys(nat.entitlement.prelim), ...Object.keys(nat.entitlement.projected)]);
	return [...ids]
		.map((id) => /** @type {[string, number]} */ ([id, (nat.entitlement.projected[id] ?? 0) - (nat.entitlement.prelim[id] ?? 0)]))
		.filter(([, d]) => d !== 0)
		.sort((a, b) => b[1] - a[1]);
}
