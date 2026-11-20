<script>
	import MarginBridge from '#lib/components/MarginBridge.svelte';
	import MultiplierBars from '#lib/components/MultiplierBars.svelte';
	import Term from '#lib/components/Term.svelte';
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, pct, pp, points, mult, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const e = $derived(data.electorate);
	const names = $derived(data.names);
	const base = $derived(data.base);
	/** 2023 sources making up less than this share of the 2026 electorate are shown faded. */
	const MINOR = 0.2;
	/** Which vote the step 1 table shows; everything else is the electorate vote. */
	let step1 = $state(/** @type {'candidate' | 'party'} */ ('candidate'));

	const byKey = $derived(e.omitted ? {} : Object.fromEntries(e.candidate.rows.map((/** @type {any} */ r) => [r.key, r])));
	const W = $derived(byKey[e.winner]);
	const S = $derived(byKey[e.second]);
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'independent');
	const who = (/** @type {any} */ r) => (r.candidate ? candidateName(r.candidate) : r.label);
	const holds = $derived(!e.omitted && !e.flips);
	// Party-vote rows (base year) behind candidates that use their party's party-vote multiplier.
	const fallback = $derived.by(() => {
		if (e.omitted) return [];
		const parties = new Set(e.candidate.rows.filter((/** @type {any} */ r) => r.link === 'party vote').map((/** @type {any} */ r) => r.party));
		const links = Object.fromEntries(e.party.rows.map((/** @type {any} */ r) => [r.key, r.link]));
		const wanted = new Set([...parties].map((p) => links[p]).filter((l) => l && l !== 'party vote'));
		return e.party.base_rows.rows.filter((/** @type {any} */ r) => wanted.has(r.key));
	});
	const live = $derived(e.omitted ? [] : e.sources.filter((/** @type {any} */ s) => !s.omitted));
	/** Where a row's multiplier came from, in words. */
	function source(/** @type {any} */ r) {
		if (r.link === 'party vote') return `No ${base} candidate, uses party-vote multipliers`;
		if (!r.link) return r.party ? `No ${base} counterpart, uses multipliers of 1` : 'Independent, uses multipliers of 1';
		return r.link !== r.party ? `As ${party(r.link)} in ${base}` : '';
	}
	const srcLinks = (/** @type {any} */ s) => [
		{ label: 'official', url: s.links.final_base.url },
		{ label: 'XML', url: s.links.final_base.xml },
		{ label: 'CSV', url: s.links.final_base[step1 === 'candidate' ? 'candidate_csv' : 'party_csv'] }
	];
	/** A pool multiplier, or a dash if there isn't one (no ordinary votes). */
	const m = (/** @type {number | null | undefined} */ v) => (v == null ? '—' : mult(v));
	const share = (/** @type {number} */ v, /** @type {number} */ total) => (total ? v / total : 0);
	const POOLS = /** @type {const} */ ([['overseas', 'Overseas specials'], ['domestic', 'Domestic specials']]);
</script>

<p class="small"><a href={link('/electorates/')}>← All electorates</a></p>
<h1>{e.name} <span class="muted small">{e.roll === 'maori' ? 'Māori' : 'general'} electorate</span></h1>

{#if e.omitted}
	<p>
		Not projected. Port Waikato had no electorate vote in the 2023 general election (a candidate
		died, so it went to a by-election), so there are no 2023 candidate special votes to project
		from. The seat is held at the preliminary leader,
		<strong>{candidateName(e.winner_label.replace(/ \(.*\)$/, ''))}</strong> ({party(e.winner_party)}).
	</p>
	<div class="table-wrap">
		<table>
			<thead><tr><th>Candidate</th><th class="num">Preliminary</th></tr></thead>
			<tbody>
				{#each e.candidate.rows as r (r.key)}
					<tr><td><span class="swatch" style:background={colour(r.party)}></span>{r.label}</td><td class="num">{votes(r.prelim)}</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
	<p class="sources">Source: <a href={e.links.prelim_2026.url}>2026 preliminary count</a> (<a href={e.links.prelim_2026.xml}>XML</a>)</p>
{:else}
	<p class="verdict">
		<span class="swatch" style:background={colour(W.party)}></span>
		<strong>{who(W)}</strong> ({party(W.party)}) {holds ? 'holds on' : 'overtakes'},
		projected to win by <strong>{votes(e.margin)}</strong> votes ({points(e.margin_pct)}) over
		{who(S)} ({party(S.party)}).
		{#if e.flips}<span class="badge flip">flips from {party(byKey[e.prelim_winner].party)}</span>{/if}
	</p>

	<div class="callout">
		<p>
			<strong>Why.</strong>
			In the preliminary count {e.bridge.prelim_lead >= 0 ? who(W) : who(S)} leads by
			{votes(Math.abs(e.bridge.prelim_lead))}. About {votes(e.candidate.volume)} electorate-vote
			specials are projected here: {votes(e.candidate.pools.overseas.volume)} overseas,
			{votes(e.candidate.pools.domestic.volume)} domestic and {votes(e.candidate.pools.revisions.volume)}
			in revisions. From {base}, {who(W)}’s multipliers are {m(W.pools.domestic.multiplier)} domestic and
			{m(W.pools.overseas.multiplier)} overseas; {who(S)}’s are {m(S.pools.domestic.multiplier)} and
			{m(S.pools.overseas.multiplier)}. Each kind of special vote is shared in proportion to preliminary
			share × multiplier, so {who(W)} gets {votes(e.bridge.specials_winner)} and {who(S)}
			{votes(e.bridge.specials_second)}: a net {signed(e.bridge.specials_winner - e.bridge.specials_second)}
			for {who(W)}.
		</p>
		<p>
			{#if e.breakeven.factor === null}
				{who(S)} couldn’t catch up even with every special vote.
			{:else}
				To tie, {who(S)} would have needed to do
				<strong>{pct(e.breakeven.needed_specials / e.breakeven.had_specials - 1, 1)} better</strong> in the
				special votes: {votes(e.breakeven.needed_specials)} instead of {votes(e.breakeven.had_specials)}, with
				both multipliers {e.breakeven.factor.toFixed(2)}× as high and everyone else’s unchanged.
			{/if}
		</p>
	</div>

	<h2>Margin</h2>
	<MarginBridge
		lead={e.bridge.prelim_lead}
		plus={e.bridge.specials_winner}
		minus={e.bridge.specials_second}
		winner={who(W)}
		second={who(S)}
		winnerParty={W.party}
		secondParty={S.party}
	/>

	{@const k = e.candidate}

	<h2>1. Notional {base} {e.name}</h2>
	<p>
		The 2026 {e.name} electorate is on 2025 boundaries. Its {base} numbers are built from the {base}
		electorates that overlap it. Each {base} electorate’s votes are multiplied by its
		<strong>weight</strong>: the share of its 2023 Census electoral population that falls inside the
		2026 {e.name}, worked out meshblock by meshblock. This assumes each {base} electorate’s votes were
		spread evenly across its population. (<strong>% of 2026 {e.name}</strong> is the other way round:
		how much of the 2026 {e.name}’s population came from that {base} electorate.)
		{#if e.omitted_share > 0}{pct(e.omitted_share, 1)} of its population was in Port Waikato,
			which is left out.{/if}
		The party vote is needed too, for the step 2 fallback and the step 3 scale factors.
	</p>
	<div class="toggle" role="group" aria-label="Votes shown in this table">
		<button aria-pressed={step1 === 'candidate'} onclick={() => (step1 = 'candidate')}>Electorate vote</button>
		<button aria-pressed={step1 === 'party'} onclick={() => (step1 = 'party')}>Party vote</button>
	</div>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>{base} electorate</th>
					<th class="num" title="Share of the 2026 {e.name}’s population that came from this {base} electorate">% of 2026 {e.name}</th>
					<th class="num" title="Share of this {base} electorate’s population that’s inside the 2026 {e.name}: its votes are multiplied by this">Weight</th>
					<th class="num">Ordinary</th>
					<th class="num">Overseas</th>
					<th class="num">Domestic</th>
					<th>Sources</th>
				</tr>
			</thead>
			<tbody>
				{#each e.sources as s (s.id)}
					<tr>
						<td>{s.name}</td>
						<td class="num">{pct(s.share_of_2026, 1)}</td>
						<td class="num">{pct(s.share_of_base, 1)}</td>
						{#if s.omitted}
							<td colspan="3" class="muted">left out (no {base} electorate vote)</td>
						{:else}
							<td class="num">{votes(s[step1].ordinary)}</td>
							<td class="num">{votes(s[step1].overseas)}</td>
							<td class="num">{votes(s[step1].domestic)}</td>
						{/if}
						<td class="sources">
							{#each srcLinks(s) as l, i (i)}{i > 0 ? ' · ' : ''}<a href={l.url}>{l.label}</a>{/each}
						</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Notional {e.name} (weighted)</td>
					<td colspan="2"></td>
					<td class="num">{votes(e[step1].base_rows.ordinary)}</td>
					<td class="num">{votes(e[step1].base_rows.pools.overseas)}</td>
					<td class="num">{votes(e[step1].base_rows.pools.domestic)}</td>
					<td></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<p class="small muted">
		Valid {step1 === 'candidate' ? 'electorate' : 'party'} votes in the {base} final count, split into
		ordinary votes and overseas and domestic special votes, from the results by voting place (Wayback
		Machine captures, as the live site blocks them). Each party’s{step1 === 'candidate' ? ' candidate' : ''}
		votes are weighted the same way.
	</p>

	<h2>2. Each party’s {base} multipliers (electorate vote)</h2>
	<p>
		Overseas multiplier = share of the overseas special votes ÷ share of the ordinary votes; domestic
		multiplier, the same with domestic special votes. Above 1, those special voters here liked them
		more than ordinary voters did.
	</p>
	<MultiplierBars
		rows={k.base_rows.rows.filter((/** @type {any} */ r) => r.ordinary_share > 0.02).map((/** @type {any} */ r) => ({
			id: r.key, label: r.label, party: r.party,
			domestic: r.pools.domestic.multiplier, overseas: r.pools.overseas.multiplier
		}))}
	/>
	{#snippet baseTable(/** @type {any} */ t, /** @type {any[]} */ rows, /** @type {string} */ heading, /** @type {string} */ totalLabel, /** @type {boolean} */ withCandidates)}
		<div class="table-wrap">
			<table class="wide-first">
				<thead>
					<tr>
						<th>{heading}</th>
						<th class="num">Ordinary</th>
						<th class="num">Overseas</th>
						<th class="num">Domestic</th>
						<th class="num">Ordinary share</th>
						<th class="num">Overseas share</th>
						<th class="num">Domestic share</th>
						<th class="num">Overseas mult.</th>
						<th class="num">Domestic mult.</th>
					</tr>
				</thead>
				<tbody>
					{#each rows as r (r.key)}
						<tr>
							<td>
								<span class="swatch" style:background={colour(r.party)}></span>{r.party ? r.label : `${candidateName(r.label)} (independent)`}
								{#if withCandidates && r.candidates?.length}
									<div class="small note">
										{#each r.candidates as c, i (i)}{i > 0 ? ', ' : ''}<span class:minor={c.share < MINOR}
												title="{base} {c.share >= MINOR ? 'main' : 'minor'} source: {pct(c.share, 1)} of the 2026 {e.name}’s population"
												>{candidateName(c.name)}</span>{/each}
									</div>
								{/if}
							</td>
							<td class="num">{votes(r.ordinary)}</td>
							<td class="num">{votes(r.pools.overseas.votes)}</td>
							<td class="num">{votes(r.pools.domestic.votes)}</td>
							<td class="num">{pct(r.ordinary_share)}</td>
							<td class="num">{pct(share(r.pools.overseas.votes, t.pools.overseas))}</td>
							<td class="num">{pct(share(r.pools.domestic.votes, t.pools.domestic))}</td>
							<td class="num"><strong>{m(r.pools.overseas.multiplier)}</strong></td>
							<td class="num"><strong>{m(r.pools.domestic.multiplier)}</strong></td>
						</tr>
					{/each}
				</tbody>
				<tfoot>
					<tr>
						<td>{totalLabel}</td>
						<td class="num">{votes(t.ordinary)}</td>
						<td class="num">{votes(t.pools.overseas)}</td>
						<td class="num">{votes(t.pools.domestic)}</td>
						<td colspan="5"></td>
					</tr>
				</tfoot>
			</table>
		</div>
	{/snippet}
	{@render baseTable(k.base_rows, k.base_rows.rows, `${base} candidate`, 'Total', true)}
	<p class="small muted">
		Candidates are matched to 2026 by party. Where several names are shown, the area took in parts of
		several {base} electorates; names in lighter text are from electorates that make up less than
		{pct(MINOR, 0)} of the 2026 {e.name}’s population.
	</p>
	{#if fallback.length}
		<h3>Party-vote multipliers, for candidates with no {base} counterpart</h3>
		<p>
			{fallback.map((/** @type {any} */ r) => r.label).join(', ')}
			had no {base} candidate here, so
			{fallback.length === 1 ? 'its candidate uses' : 'their candidates use'} the party’s
			<em>party-vote</em> multipliers in this area, worked out the same way from the notional {base}
			party vote:
		</p>
		{@render baseTable(e.party.base_rows, fallback, `${base} party (party vote)`, 'All parties (party vote)', false)}
		<p class="small muted">
			A party new in 2026 has no {base} party vote either, so it gets 1. A party that was part of
			an umbrella party in {base} uses the umbrella’s multipliers.
		</p>
	{/if}

	<h2>3. How many special votes</h2>
	<p>
		For overseas and domestic special votes, each electorate’s {base} ratio of special votes to ordinary
		votes is multiplied by a national factor for that kind of special vote, so that the electorates’
		party-vote specials add up to the <a href={link('/party-vote/')}>national projection</a> (fewer
		domestic specials are expected in 2026). Revisions, the official count’s corrections to ordinary
		votes, are the same share of the preliminary count in every electorate.
	</p>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th></th>
					<th class="num">{base} ratio</th>
					<th class="num">× national factor</th>
					<th class="num">× 2026 preliminary</th>
					<th class="num">= projected</th>
				</tr>
			</thead>
			<tbody>
				{#each POOLS as [key, label] (key)}
					{@const p = k.pools[key]}
					<tr>
						<td>{label}</td>
						<td class="num" title="{votes(k.base_rows.pools[key])} ÷ {votes(k.base_rows.ordinary)} ordinary votes">{pct(p.ratio, 1)}</td>
						<td class="num">{p.scale.toFixed(3)}</td>
						<td class="num">{votes(k.prelim_total)}</td>
						<td class="num">{votes(p.volume)}</td>
					</tr>
				{/each}
				<tr>
					<td>Revisions</td>
					<td class="num">{pct(k.pools.revisions.ratio, 2)}<span class="muted">*</span></td>
					<td class="num">—</td>
					<td class="num">{votes(k.prelim_total)}</td>
					<td class="num">{signed(k.pools.revisions.volume)}</td>
				</tr>
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td colspan="3"></td>
					<td class="num"><strong>{votes(k.volume)}</strong></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<p class="small muted">
		* The national ratio, not this electorate’s own. Revisions are mostly one-off corrections: an
		electorate can change by several percent in one official count and barely at all in the next.
		Between 2017 and 2023, on today’s boundaries, electorates’ revision rates were barely correlated
		(0.22), so an electorate’s past revisions say little about its next ones. Māori electorates are
		a partial exception: theirs have been consistently higher (+1.5% in 2017 and +2.2% in 2023,
		against +0.1% and +0.5% in general electorates), but that isn’t modelled. Figures are rounded, so
		the rows may not add up exactly.
	</p>

	<h2>4. Sharing out the 2026 specials</h2>
	<p>
		Each kind of special vote is shared out separately. A candidate’s share of the overseas specials is
		their 2026 preliminary share × their party’s {base} overseas multiplier, divided by the total of
		that over all candidates; the same for domestic specials. Revisions are shared like the
		preliminary count.
	</p>
	<div class="table-wrap">
		<table class="wide-first">
			<thead>
				<tr>
					<th>Candidate</th>
					<th class="num">Preliminary</th>
					<th class="num">Share</th>
					<th class="num">Overseas mult.</th>
					<th class="num">Domestic mult.</th>
					<th class="num">+ overseas</th>
					<th class="num">+ domestic</th>
					<th class="num">+ revisions</th>
					<th class="num">Projected</th>
					<th class="num">Share</th>
				</tr>
			</thead>
			<tbody>
				{#each k.rows as r (r.key)}
					<tr>
						<td>
							<span class="swatch" style:background={colour(r.party)}></span>{who(r)}
							<span class="muted small">{party(r.party)}</span>
						</td>
						<td class="num">{votes(r.prelim)}</td>
						<td class="num">{pct(r.prelim_share)}</td>
						{#each ['overseas', 'domestic'] as key (key)}
							<td class="num">{#if source(r)}<Term tip={source(r)}>{mult(r.pools[key].multiplier)}</Term>{:else}{mult(r.pools[key].multiplier)}{/if}</td>
						{/each}
						<td class="num">{signed(r.pools.overseas.specials)}</td>
						<td class="num">{signed(r.pools.domestic.specials)}</td>
						<td class="num">{signed(r.pools.revisions.specials)}</td>
						<td class="num">{votes(r.final)}</td>
						<td class="num"><strong>{pct(r.final_share)}</strong></td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(k.prelim_total)}</td>
					<td colspan="3"></td>
					<td class="num">{signed(k.pools.overseas.volume)}</td>
					<td class="num">{signed(k.pools.domestic.volume)}</td>
					<td class="num">{signed(k.pools.revisions.volume)}</td>
					<td class="num">{votes(k.prelim_total + k.volume)}</td>
					<td></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<p class="sources">
		2026 source: <a href={e.links.prelim_2026.url}>preliminary count</a>
		(<a href={e.links.prelim_2026.xml}>XML</a>).
	</p>
{/if}

<style>
	.verdict { font-size: 1.1rem; }
	.flip { color: var(--text); margin-left: 0.4em; }
	.note { max-width: 32ch; white-space: normal; color: var(--text-2); }
	.note .minor { color: var(--text-3); opacity: 0.75; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0 0 0.6em; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
</style>
