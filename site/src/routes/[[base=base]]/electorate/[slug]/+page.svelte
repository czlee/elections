<script>
	import MarginBridge from '#lib/components/MarginBridge.svelte';
	import MultiplierBars from '#lib/components/MultiplierBars.svelte';
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, pct, pp, points, mult, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const e = $derived(data.electorate);
	const names = $derived(data.names);
	const base = $derived(data.base);
	/** 2023 sources making up less than this share of the 2026 electorate are shown faded. */
	const MINOR = 0.2;
	let tab = $state(/** @type {'candidate' | 'party'} */ ('candidate'));

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
		if (r.link === 'party vote') return `no ${base} ${party(r.party)} candidate here: uses ${party(r.party)}’s party-vote multiplier`;
		if (!r.link) return `no ${base} counterpart: multiplier 1`;
		if (r.base?.candidates?.length) return `${base}: ${r.base.candidates.map(candidateName).join(', ')}`;
		return r.link !== r.party ? `as ${party(r.link)} in ${base}` : '';
	}
	const srcLinks = (/** @type {any} */ s) => [
		s.links.prelim_base && { label: 'prelim', url: s.links.prelim_base.url },
		{ label: 'official', url: s.links.final_base.url },
		{ label: 'XML', url: s.links.final_base.xml }
	].filter(Boolean);
</script>

<svelte:head>
	<title>{e.name} · 2026 special votes projection</title>
</svelte:head>

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
			specials are projected here. From {base}, {who(W)}’s multiplier is
			{mult(W.multiplier)} and {who(S)}’s is {mult(S.multiplier)}. Specials are shared in proportion to
			preliminary share × multiplier, so {who(W)} gets {votes(e.bridge.specials_winner)} and
			{who(S)} {votes(e.bridge.specials_second)}: a net {signed(e.bridge.specials_winner - e.bridge.specials_second)}
			for {who(W)}.
		</p>
		<p>
			{#if e.breakeven.needed === null}
				{who(S)} couldn’t catch up even with every special vote.
			{:else}
				To tie, {who(S)} would have needed a multiplier of <strong>{mult(e.breakeven.needed)}</strong>
				(with everyone else’s unchanged); they got {mult(e.breakeven.had)}, which is
				{(e.breakeven.needed / e.breakeven.had).toFixed(2)}× short.
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

	<div class="toggle" role="group" aria-label="Vote">
		<button aria-pressed={tab === 'candidate'} onclick={() => (tab = 'candidate')}>Electorate vote</button>
		<button aria-pressed={tab === 'party'} onclick={() => (tab = 'party')}>Party vote</button>
	</div>

	{@const k = e[tab]}
	{@const kindWord = tab === 'candidate' ? 'electorate' : 'party'}
	{@const weightSum = k.rows.reduce((/** @type {number} */ a, /** @type {any} */ r) => a + r.prelim_share * r.multiplier, 0)}

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
	</p>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>{base} electorate</th>
					<th class="num" title="Share of the 2026 {e.name}’s population that came from this {base} electorate">% of 2026 {e.name}</th>
					<th class="num" title="Share of this {base} electorate’s population that’s inside the 2026 {e.name}: its votes are multiplied by this">Weight</th>
					<th class="num">Preliminary</th>
					<th class="num">Final</th>
					<th class="num">Weighted prelim</th>
					<th class="num">Weighted final</th>
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
							<td colspan="4" class="muted">left out (no {base} electorate vote)</td>
						{:else}
							<td class="num">{votes(s[tab].prelim)}</td>
							<td class="num">{votes(s[tab].final)}</td>
							<td class="num">{votes(s[tab].prelim * s.share_of_base)}</td>
							<td class="num">{votes(s[tab].final * s.share_of_base)}</td>
						{/if}
						<td class="sources">
							{#each srcLinks(s) as l, i (l.label)}{i > 0 ? ' · ' : ''}<a href={l.url}>{l.label}</a>{/each}
						</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Notional {e.name}</td>
					<td colspan="4"></td>
					<td class="num">{votes(k.base_rows.prelim)}</td>
					<td class="num">{votes(k.base_rows.final)}</td>
					<td></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<p class="small muted">
		Valid {kindWord} votes. Each party’s{tab === 'candidate' ? ' candidate' : ''} votes are weighted the
		same way. The {base} preliminary pages are Wayback Machine captures.
	</p>

	<h2>2. Each party’s {base} multiplier ({kindWord} vote)</h2>
	<p>
		Special votes = final − preliminary. Multiplier = share of the specials ÷ share of the
		preliminary count. Above 1, special voters here liked them more than election-night voters did.
	</p>
	<MultiplierBars
		rows={k.base_rows.rows.filter((/** @type {any} */ r) => r.prelim_share > 0.02 && r.multiplier).map((/** @type {any} */ r) => ({
			id: r.key, label: r.label, value: r.multiplier, party: r.party
		}))}
	/>
	<div class="table-wrap">
		<table class="wide-first">
			<thead>
				<tr>
					<th>{tab === 'candidate' ? `${base} candidate` : `${base} party`}</th>
					<th class="num">Preliminary</th>
					<th class="num">Final</th>
					<th class="num">Specials</th>
					<th class="num">Prelim share</th>
					<th class="num">Special share</th>
					<th class="num">Multiplier</th>
				</tr>
			</thead>
			<tbody>
				{#each k.base_rows.rows as r (r.key)}
					<tr>
						<td>
							<span class="swatch" style:background={colour(r.party)}></span>{r.party ? r.label : `${candidateName(r.label)} (independent)`}
							{#if r.candidates?.length}
								<div class="small note">
									{#each r.candidates as c, i (c.name)}{i > 0 ? ', ' : ''}<span class:minor={c.share < MINOR}
											title="{base} {c.share >= MINOR ? 'main' : 'minor'} source: {pct(c.share, 1)} of the 2026 {e.name}’s population"
											>{candidateName(c.name)}</span>{/each}
								</div>
							{/if}
						</td>
						<td class="num">{votes(r.prelim)}</td>
						<td class="num">{votes(r.final)}</td>
						<td class="num">{signed(r.specials)}</td>
						<td class="num">{pct(r.prelim_share)}</td>
						<td class="num">{pct(r.special_share)}</td>
						<td class="num"><strong>{r.multiplier === null ? '—' : mult(r.multiplier)}</strong></td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(k.base_rows.prelim)}</td>
					<td class="num">{votes(k.base_rows.final)}</td>
					<td class="num">{signed(k.base_rows.specials)}</td>
					<td colspan="3"></td>
				</tr>
			</tfoot>
		</table>
	</div>
	{#if tab === 'candidate'}
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
				<em>party-vote</em> multiplier in this area, worked out the same way from the notional {base}
				party vote:
			</p>
			<div class="table-wrap">
				<table class="wide-first">
					<thead>
						<tr>
							<th>{base} party (party vote)</th>
							<th class="num">Preliminary</th>
							<th class="num">Final</th>
							<th class="num">Specials</th>
							<th class="num">Prelim share</th>
							<th class="num">Special share</th>
							<th class="num">Multiplier</th>
						</tr>
					</thead>
					<tbody>
						{#each fallback as r (r.key)}
							<tr>
								<td><span class="swatch" style:background={colour(r.party)}></span>{r.label}</td>
								<td class="num">{votes(r.prelim)}</td>
								<td class="num">{votes(r.final)}</td>
								<td class="num">{signed(r.specials)}</td>
								<td class="num">{pct(r.prelim_share)}</td>
								<td class="num">{pct(r.special_share)}</td>
								<td class="num"><strong>{r.multiplier === null ? '—' : mult(r.multiplier)}</strong></td>
							</tr>
						{/each}
					</tbody>
					<tfoot>
						<tr>
							<td>All parties (party vote)</td>
							<td class="num">{votes(e.party.base_rows.prelim)}</td>
							<td class="num">{votes(e.party.base_rows.final)}</td>
							<td class="num">{signed(e.party.base_rows.specials)}</td>
							<td colspan="3"></td>
						</tr>
					</tfoot>
				</table>
			</div>
			<p class="small muted">
				A party new in 2026 has no {base} party vote either, so it gets 1. A party that was part of
				an umbrella party in {base} uses the umbrella’s multiplier.
			</p>
		{/if}
	{/if}

	<h2>3. How many special votes</h2>
	<p>
		In {base}, there were {votes(k.base_rows.specials)} specials here on {votes(k.base_rows.prelim)}
		preliminary votes, a ratio of <strong>{pct(k.ratio, 1)}</strong>. Every electorate’s ratio is
		multiplied by the same national factor, <strong>{k.scale.toFixed(3)}</strong>, so that the
		electorates’ party-vote specials add up to the <a href={link('/party-vote/')}>national
		projection</a> (fewer specials are expected in 2026). So:
		{votes(k.prelim_total)} preliminary × {pct(k.ratio, 1)} × {k.scale.toFixed(3)} =
		<strong>{votes(k.volume)}</strong> projected {kindWord}-vote specials.
	</p>

	<h2>4. Sharing out the 2026 specials</h2>
	<p>
		Each {tab === 'candidate' ? 'candidate' : 'party'}’s weight is their 2026 preliminary share × their
		party’s {base} multiplier. Their share of the {votes(k.volume)} specials is their weight ÷ the total
		weight ({weightSum.toFixed(4)}).
		{#if tab === 'candidate'}Independent candidates get a multiplier of 1.{/if}
	</p>
	<div class="table-wrap">
		<table class="wide-first">
			<thead>
				<tr>
					<th>{tab === 'candidate' ? 'Candidate' : 'Party'}</th>
					<th class="num">Preliminary</th>
					<th class="num">Share</th>
					<th class="num">× multiplier</th>
					<th class="num">= weight</th>
					<th class="num">Special share</th>
					<th class="num">+ specials</th>
					<th class="num">Projected</th>
					<th class="num">Share</th>
				</tr>
			</thead>
			<tbody>
				{#each k.rows as r (r.key)}
					<tr>
						<td>
							<span class="swatch" style:background={colour(r.party)}></span>{tab === 'candidate' ? who(r) : r.label}
							{#if tab === 'candidate'}<span class="muted small">{party(r.party)}</span>{/if}
							{#if source(r)}<div class="muted small note">{source(r)}</div>{/if}
						</td>
						<td class="num">{votes(r.prelim)}</td>
						<td class="num">{pct(r.prelim_share)}</td>
						<td class="num">{mult(r.multiplier)}</td>
						<td class="num">{(r.prelim_share * r.multiplier).toFixed(4)}</td>
						<td class="num">{pct(r.special_share)}</td>
						<td class="num">{signed(r.specials)}</td>
						<td class="num">{votes(r.final)}</td>
						<td class="num"><strong>{pct(r.final_share)}</strong></td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(k.prelim_total)}</td>
					<td></td><td></td>
					<td class="num">{weightSum.toFixed(4)}</td>
					<td></td>
					<td class="num">{signed(k.volume)}</td>
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
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 1.6em 0 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
</style>
