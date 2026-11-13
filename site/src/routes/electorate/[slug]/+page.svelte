<script>
	import MarginBridge from '#lib/components/MarginBridge.svelte';
	import MultiplierBars from '#lib/components/MultiplierBars.svelte';
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, pct, pp, mult, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const e = $derived(data.electorate);
	const names = $derived(data.names);
	const base = $derived(data.base);
	let tab = $state(/** @type {'candidate' | 'party'} */ ('candidate'));

	const byKey = $derived(e.omitted ? {} : Object.fromEntries(e.candidate.rows.map((/** @type {any} */ r) => [r.key, r])));
	const W = $derived(byKey[e.winner]);
	const S = $derived(byKey[e.second]);
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'independent');
	const who = (/** @type {any} */ r) => (r.candidate ? candidateName(r.candidate) : r.label);
	const holds = $derived(!e.omitted && !e.flips);
	const live = $derived(e.omitted ? [] : e.sources.filter((/** @type {any} */ s) => !s.omitted));
	/** Where a row's multiplier came from, in words. */
	function source(/** @type {any} */ r) {
		if (r.link === 'party vote') return `no ${base} ${party(r.party)} candidate here: uses ${party(r.party)}'s party-vote multiplier`;
		if (!r.link) return `no ${base} counterpart: multiplier 1`;
		if (r.base?.candidates?.length) return `${base}: ${r.base.candidates.map(candidateName).join(', ')}`;
		return r.link !== r.party ? `as ${party(r.link)} in ${base}` : '';
	}
	const srcLinks = (/** @type {any} */ s) => [
		s.links.prelim_2023 && { label: 'prelim', url: s.links.prelim_2023.url },
		{ label: 'official', url: s.links.final_2023.url },
		{ label: 'XML', url: s.links.final_2023.xml }
	].filter(Boolean);
</script>

<svelte:head>
	<title>{e.name} · 2026 special votes projection</title>
</svelte:head>

<p class="small"><a href={link('/')}>← All electorates</a></p>
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
		projected to win by <strong>{votes(e.margin)}</strong> votes ({pct(e.margin_pct)}) over
		{who(S)} ({party(S.party)}).
		{#if e.flips}<span class="badge flip">flips from {party(byKey[e.prelim_winner].party)}</span>{/if}
	</p>

	<div class="callout">
		<p>
			<strong>Why.</strong>
			In the preliminary count {e.bridge.prelim_lead >= 0 ? who(W) : who(S)} leads by
			{votes(Math.abs(e.bridge.prelim_lead))}. About {votes(e.candidate.volume)} electorate-vote
			specials are projected here. From {base}, {who(W)}'s multiplier is
			{mult(W.multiplier)} and {who(S)}'s is {mult(S.multiplier)}. Specials are shared in proportion to
			preliminary share × multiplier, so {who(W)} gets {votes(e.bridge.specials_winner)} and
			{who(S)} {votes(e.bridge.specials_second)}: a net {signed(e.bridge.specials_winner - e.bridge.specials_second)}
			for {who(W)}.
		</p>
		<p>
			{#if e.breakeven.needed === null}
				{who(S)} couldn't catch up even with every special vote.
			{:else}
				To tie, {who(S)} would have needed a multiplier of <strong>{mult(e.breakeven.needed)}</strong>
				(with everyone else's unchanged); they got {mult(e.breakeven.had)}, which is
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
	<h2>{tab === 'candidate' ? 'Candidates' : 'Party vote'}, step by step</h2>
	<p>
		Multiplier: the party's share of the notional {base} {tab === 'candidate' ? 'electorate' : 'party'}-vote
		specials in this area, divided by its share of the notional {base} preliminary count (below).
		Projected specials = preliminary share × multiplier, scaled to add up to
		{votes(k.volume)} ({pct(k.ratio, 1)} of the preliminary count, the area's {base} ratio, scaled to
		the national total).
	</p>
	<MultiplierBars
		rows={k.rows.filter((/** @type {any} */ r) => r.prelim_share > 0.02).map((/** @type {any} */ r) => ({
			id: r.key, label: tab === 'candidate' ? who(r) : r.label, value: r.multiplier, party: r.party,
			short: tab === 'candidate' ? who(r).split(' ').at(-1) : undefined
		}))}
	/>
	<div class="table-wrap">
		<table class="wide-first">
			<thead>
				<tr>
					<th>{tab === 'candidate' ? 'Candidate' : 'Party'}</th>
					<th class="num">Preliminary</th>
					<th class="num">Share</th>
					<th class="num" title="Notional {base} preliminary share → special share">{base} prelim → specials</th>
					<th class="num">Multiplier</th>
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
						<td class="num">{r.base ? `${pct(r.base.prelim_share)} → ${pct(r.base.special_share)}` : '—'}</td>
						<td class="num"><strong>{mult(r.multiplier)}</strong></td>
						<td class="num">{signed(r.specials)}</td>
						<td class="num">{votes(r.final)}</td>
						<td class="num">{pct(r.final_share)}</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(k.prelim_total)}</td>
					<td></td><td></td><td></td>
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

	<h2>Notional {base} {e.name}</h2>
	<p>
		{e.name} is on 2025 boundaries. Its {base} numbers are built from the {base} electorates that
		overlap it, each weighted by the share of that electorate's 2023 Census electoral population
		that falls inside {e.name}.
		{#if e.omitted_share > 0}{pct(e.omitted_share, 1)} of its population was in Port Waikato,
			which is left out.{/if}
	</p>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>{base} electorate</th>
					<th class="num">Share of {e.name}</th>
					<th class="num">Weight</th>
					<th class="num">{who(W).split(' ').at(-1)}'s party</th>
					<th class="num">{who(S).split(' ').at(-1)}'s party</th>
					<th class="num">All</th>
					<th>Sources</th>
				</tr>
			</thead>
			<tbody>
				{#each e.sources as s (s.id)}
					<tr>
						<td>{s.name}</td>
						<td class="num">{pct(s.share_of_2026, 1)}</td>
						<td class="num" title="Share of {s.name}'s population inside {e.name}">{pct(s.share_of_2023, 1)}</td>
						{#if s.omitted}
							<td colspan="3" class="muted">left out (no {base} electorate vote)</td>
						{:else}
							{#each [W, S] as r (r.key)}
								{@const v = r.base ? s[tab].by_key[r.base.key] : null}
								<td class="num" title="preliminary → final">{v ? `${votes(v[0])} → ${votes(v[1])}` : '—'}</td>
							{/each}
							<td class="num" title="preliminary → final">{votes(s[tab].prelim)} → {votes(s[tab].final)}</td>
						{/if}
						<td class="sources">
							{#each srcLinks(s) as l, i (l.label)}{i > 0 ? ' · ' : ''}<a href={l.url}>{l.label}</a>{/each}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	<p class="small muted">
		Columns show each {base} electorate's whole count (preliminary → final), before weighting.
		The {base} preliminary pages are Wayback Machine captures.
	</p>
{/if}

<style>
	.verdict { font-size: 1.1rem; }
	.flip { color: var(--text); margin-left: 0.4em; }
	.note { max-width: 32ch; white-space: normal; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 1.6em 0 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
</style>
