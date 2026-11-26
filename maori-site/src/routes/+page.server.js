import { national, summaries } from '#lib/server/data.js';

export function load() {
	const { parties, seats, house, entitlement, moved, sensitivity, flips, tpm_party_share, maori_candidate_votes,
		voting_places, general_electorates, maori_electorates, party_vote_total } = national;
	return {
		national: { parties, seats, house, entitlement, moved, sensitivity, flips, tpm_party_share,
			maori_candidate_votes, voting_places, general_electorates, maori_electorates, party_vote_total },
		electorates: summaries()
	};
}
