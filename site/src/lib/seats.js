/**
 * Parties whose Sainte-Laguë share changes between the preliminary and
 * projected counts, but whose seat total doesn't, because they won more
 * electorates than their share in both: the overhang absorbs the change.
 * @param {any} nat national.json (needs seats and entitlement)
 * @returns {{id: string, from: number, to: number, seats: number, electorates: number}[]}
 */
export function absorbedByOverhang(nat) {
	return Object.keys(nat.seats.projected)
		.map((id) => ({
			id,
			from: nat.entitlement.prelim[id] ?? 0,
			to: nat.entitlement.projected[id] ?? 0,
			seats: nat.seats.projected[id].total,
			electorates: nat.seats.projected[id].electorate,
			prelimSeats: nat.seats.prelim[id]?.total ?? 0
		}))
		.filter((p) => p.from !== p.to && p.seats === p.prelimSeats && p.seats === p.electorates)
		.map(({ prelimSeats, ...p }) => p);
}
