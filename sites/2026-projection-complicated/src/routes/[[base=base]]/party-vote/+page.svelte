<script>
	import DeltaBars from '#lib/components/DeltaBars.svelte';
	import MultiplierBars from '#lib/components/MultiplierBars.svelte';
	import Sources from '#lib/components/Sources.svelte';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { votes, pct, pp, mult, signed } from '#lib/format.js';
	import { overhangParties, overhangSentence, slChanges } from '#lib/seats.js';

	let { data } = $props();
	const n = $derived(data.national);
	const src = $derived(n.sources);
	const pools = $derived(n.pools);
	const names = $derived(Object.fromEntries([...n.base_parties, ...n.parties].map((p) => [p.id, p.short])));
	// Parties shown in charts: those over 0.5% in either count; the rest are in the tables.
	const major = $derived(n.parties.filter((p) => p.prelim_share > 0.005 || p.final_share > 0.005));
	const baseMajor = $derived(n.base_parties.filter((p) => p.ordinary_share > 0.005));
	const changed = $derived(
		n.parties.filter((p) => (n.seats.projected[p.id]?.total ?? 0) !== (n.seats.prelim[p.id]?.total ?? 0))
	);
	const overhang = (/** @type {'prelim' | 'projected'} */ v) =>
		Object.entries(n.seats[v])
			.map(([p, s]) => [p, s.total - (n.entitlement[v][p] ?? 0)])
			.filter(([, d]) => +d > 0);
	// Seats (party, nth seat) allocated in one count but not the other, judged by
	// each party's whole Sainte-Laguë entitlement, not just the rows shown.
	const swapped = $derived.by(() => {
		const has = (/** @type {'prelim' | 'projected'} */ v, /** @type {any} */ r) => r.seat <= (n.entitlement[v][r.party] ?? 0);
		const rows = [...n.ladder.prelim, ...n.ladder.projected];
		return new Set(rows.filter((r) => has('prelim', r) !== has('projected', r)).map((r) => `${r.party}#${r.seat}`));
	});
	const sl = $derived(slChanges(n));
	const overhangNotes = $derived(overhangParties(n).map((a) => overhangSentence(a, names[a.id])));
	const lastIn =(/** @type {any[]} */ l) => l.filter((r) => r.allocated).at(-1);
	const firstOut = (/** @type {any[]} */ l) => l.find((r) => !r.allocated);
</script>

<h1>Party vote projection</h1>
<p>
	The party vote from the 2026 preliminary count, plus a projection of the special votes still
	to be counted. Overseas and domestic special votes are projected separately: each party gets the
	same share of each, relative to its share of ordinary votes, as it did in {n.base}.
</p>

<div class="steps">
	<div><span class="k">2026 preliminary</span><span class="v">{votes(n.prelim_total)}</span></div>
	<div><span class="k">+ projected specials</span><span class="v">{votes(n.projected_specials)}</span></div>
	<div><span class="k">= projected final</span><span class="v">{votes(n.final_total)}</span></div>
</div>

<h2>1. How many special votes</h2>
<p>
	The Electoral Commission estimated <strong>{votes(n.estimate_2026)}</strong> special votes in
	2026, including {votes(pools.overseas.estimate_2026)} overseas and dictation votes. What the official
	count adds to the preliminary count comes in three parts, each projected separately:
</p>
<ul>
	<li><strong>Overseas special votes.</strong> In {n.base}, {votes(pools.overseas.base_total)} were counted,
		against an election-night estimate of {votes(pools.overseas.estimate_base)}. The same ratio is applied to
		the 2026 estimate.</li>
	<li><strong>Domestic special votes</strong> (all the others), the same way, using the rest of each
		estimate.</li>
	<li><strong>Revisions:</strong> the official count’s corrections to ordinary votes. In {n.base}, final
		ordinary votes were {votes(pools.revisions.base_total)} more than the preliminary count
		({pct(pools.revisions.adjustment)} of it), so the 2026 preliminary count is scaled by the same
		share.</li>
</ul>
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th></th>
				<th class="num">{n.base} count</th>
				<th class="num">÷ {n.base} estimate</th>
				<th class="num">= ratio</th>
				<th class="num">× 2026 estimate</th>
				<th class="num">= projected</th>
			</tr>
		</thead>
		<tbody>
			{#each [['overseas', 'Overseas specials'], ['domestic', 'Domestic specials']] as [key, label] (key)}
				{@const p = pools[key]}
				<tr>
					<td>{label}</td>
					<td class="num">{votes(p.base_total)}</td>
					<td class="num">{votes(p.estimate_base)}</td>
					<td class="num">{p.adjustment.toFixed(4)}</td>
					<td class="num">{votes(p.estimate_2026)}</td>
					<td class="num">{votes(p.volume)}</td>
				</tr>
			{/each}
			<tr>
				<td>Revisions</td>
				<td class="num">{signed(pools.revisions.base_total)}</td>
				<td class="num" title="{n.base} preliminary count">{votes(pools.revisions.base_prelim)}<span class="muted">*</span></td>
				<td class="num">{pct(pools.revisions.adjustment)}</td>
				<td class="num" title="2026 preliminary count">{votes(n.prelim_total)}<span class="muted">*</span></td>
				<td class="num">{signed(pools.revisions.volume)}</td>
			</tr>
		</tbody>
		<tfoot>
			<tr>
				<td>Total</td>
				<td class="num">{votes(n.base_totals.specials)}</td>
				<td class="num">{votes(n.estimate_base)}</td>
				<td></td>
				<td class="num">{votes(n.estimate_2026)}</td>
				<td class="num"><strong>{votes(n.projected_specials)}</strong></td>
			</tr>
		</tfoot>
	</table>
</div>
<p class="small muted">
	* For revisions, preliminary counts instead of estimates. The estimates are of special votes cast;
	the counts are of valid party votes, so the ratios also absorb special votes that were disallowed
	or informal. The overseas estimates include dictation votes, which the official count records as
	domestic, so the overseas ratio tends to be a little under 1 and the domestic one a little over.
	Rounded, so the rows may not add up exactly.
</p>
<Sources items={[src.release_2026, src.release_base, src.prelim_base, src.final_base]} />

<h2>2. Each party’s {n.base} multipliers</h2>
<p>
	A party’s <strong>overseas multiplier</strong> is its share of the {n.base} overseas special votes
	divided by its share of the {n.base} ordinary votes; its <strong>domestic multiplier</strong>, the
	same with domestic special votes. Above 1, it did better among those special voters than among
	ordinary voters. Ordinary votes are from the final count, not the preliminary count, so that the
	official count’s corrections don’t leak into the multipliers.
</p>
<MultiplierBars rows={baseMajor.map((p) => ({ id: p.id, label: p.short,
	domestic: p.pools.domestic.multiplier, overseas: p.pools.overseas.multiplier }))} />
<details>
	<summary>All {n.base} parties</summary>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party ({n.base})</th>
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
				{#each n.base_parties as p (p.id)}
					<tr>
						<td><span class="swatch" style:background={colour(p.id)}></span>{p.short}</td>
						<td class="num">{votes(p.ordinary)}</td>
						<td class="num">{votes(p.pools.overseas.votes)}</td>
						<td class="num">{votes(p.pools.domestic.votes)}</td>
						<td class="num">{pct(p.ordinary_share)}</td>
						<td class="num">{pct(p.pools.overseas.share)}</td>
						<td class="num">{pct(p.pools.domestic.share)}</td>
						<td class="num"><strong>{mult(p.pools.overseas.multiplier)}</strong></td>
						<td class="num"><strong>{mult(p.pools.domestic.multiplier)}</strong></td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(n.base_totals.ordinary)}</td>
					<td class="num">{votes(pools.overseas.base_total)}</td>
					<td class="num">{votes(pools.domestic.base_total)}</td>
					<td colspan="5"></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<p class="small muted">
		Final count {votes(n.base_totals.final)} = ordinary {votes(n.base_totals.ordinary)} + overseas
		{votes(pools.overseas.base_total)} + domestic {votes(pools.domestic.base_total)}. The preliminary count was
		{votes(n.base_totals.prelim)}, so revisions were {signed(pools.revisions.base_total)}.
	</p>
	<Sources items={[src.prelim_base, src.final_base]} />
</details>

<h2>3. Sharing out the 2026 specials</h2>
<p>
	Each pool is shared out separately. A 2026 party’s share of the projected overseas specials is
	its preliminary share times its overseas multiplier, scaled so the shares add up to 100%; the
	same for domestic specials. Revisions are shared like the preliminary count. Parties that are
	new in 2026 get multipliers of 1; a party that was part of an umbrella party in {n.base} uses the
	umbrella’s.
</p>
<DeltaBars rows={major.map((p) => ({ id: p.id, label: p.short, from: p.prelim_share, to: p.final_share }))} />
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th>Party</th>
				<th class="num">Preliminary</th>
				<th class="num">Share</th>
				<th class="num">Overseas mult.</th>
				<th class="num">Domestic mult.</th>
				<th class="num">+ overseas</th>
				<th class="num">+ domestic</th>
				<th class="num">+ revisions</th>
				<th class="num">Projected final</th>
				<th class="num">Share</th>
				<th class="num">Change</th>
			</tr>
		</thead>
		<tbody>
			{#each n.parties as p (p.id)}
				<tr>
					<td>
						<span class="swatch" style:background={colour(p.id)}></span>{p.short}
						{#if !p.link}<span class="muted small" title="No {n.base} counterpart">(new)</span>
						{:else if p.link !== p.id}<span class="muted small">(as {names[p.link] ?? p.link})</span>{/if}
					</td>
					<td class="num">{votes(p.prelim)}</td>
					<td class="num">{pct(p.prelim_share)}</td>
					<td class="num">{mult(p.pools.overseas.multiplier)}</td>
					<td class="num">{mult(p.pools.domestic.multiplier)}</td>
					<td class="num">{signed(p.pools.overseas.specials)}</td>
					<td class="num">{signed(p.pools.domestic.specials)}</td>
					<td class="num">{signed(p.pools.revisions.specials)}</td>
					<td class="num">{votes(p.final)}</td>
					<td class="num"><strong>{pct(p.final_share)}</strong></td>
					<td class="num">{pp(p.final_share - p.prelim_share)}</td>
				</tr>
			{/each}
		</tbody>
		<tfoot>
			<tr>
				<td>Total</td>
				<td class="num">{votes(n.prelim_total)}</td>
				<td colspan="3"></td>
				<td class="num">{signed(pools.overseas.volume)}</td>
				<td class="num">{signed(pools.domestic.volume)}</td>
				<td class="num">{signed(pools.revisions.volume)}</td>
				<td class="num">{votes(n.final_total)}</td>
				<td colspan="2"></td>
			</tr>
		</tfoot>
	</table>
</div>
<Sources items={[src.prelim_2026]} />

<h2>4. Seats</h2>
<p>
	The 120 seats are shared out by Sainte-Laguë among parties over 5% or with an electorate: each
	seat goes to the highest remaining quotient, votes ÷ (2s + 1), where s is the seats the party
	already has. Changes are decided at the margin, by which quotients land just above or below seat
	120. This step is only about the 120 Sainte-Laguë seats; electorates come in under
	<a href="#overhang">Overhang</a>, below. Bold rows are the Sainte-Laguë seats that change hands:
	{sl.map(([p, d]) => `${names[p]} ${signed(d)}`).join(', ')}.
</p>
<div class="ladders">
	{#each [['prelim', 'Preliminary count'], ['projected', 'Projected final']] as [key, title] (key)}
		{@const ladder = n.ladder[key]}
		<div>
			<h3>{title}</h3>
			<div class="table-wrap">
				<table class="ladder">
					<thead>
						<tr><th class="num">Rank</th><th>Party</th><th class="num">Its seat</th><th class="num">Quotient</th></tr>
					</thead>
					<tbody>
						{#each ladder as r (r.rank)}
							<tr class:out={!r.allocated} class:cut={r.rank === n.ladder.allocated[key]}
								class:swap={swapped.has(`${r.party}#${r.seat}`)}>
								<td class="num">{r.rank}</td>
								<td><span class="swatch" style:background={colour(r.party)}></span>{names[r.party]}</td>
								<td class="num">{r.seat}</td>
								<td class="num">{votes(r.quotient)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="small muted">
				Last seat in: {names[lastIn(ladder).party]} #{lastIn(ladder).seat}. First out:
				{names[firstOut(ladder).party]} #{firstOut(ladder).seat}.
			</p>
		</div>
	{/each}
</div>
<h3 id="overhang">Overhang</h3>
<p>
	A party keeps every electorate it wins, even beyond its share of the 120, and the House grows to
	fit. In the projected final,
	{overhang('projected').map(([p, d]) => `${names[p]} wins ${n.seats.projected[p].electorate} electorates against a Sainte-Laguë share of ${n.entitlement.projected[p]} (+${d})`).join('; ')}.
	{overhangNotes.join(' ')}
	{#if n.house.projected === n.house.prelim}So the House has {n.house.projected} seats in both counts.
	{:else}So the House has {n.house.prelim} seats in the preliminary count and {n.house.projected} in the
		projected final.{/if}
	Net seat changes:
	{changed
		.map((p) => /** @type {[string, number]} */ ([p.short, n.seats.projected[p.id].total - n.seats.prelim[p.id].total]))
		.toSorted((a, b) => b[1] - a[1])
		.map(([s, d]) => `${s} ${signed(d)}`)
		.join(', ')}.
	{#if n.has_electorates}Electorate winners here are the projected ones; see the
		<a href={link('/electorates/')}>electorate pages</a>.
	{:else}Electorates aren’t projected from {n.base}, so both counts use the preliminary count’s
		electorate winners.{/if}
</p>

<style>
	.steps { display: flex; flex-wrap: wrap; gap: 0.5em 2em; margin: 1em 0; }
	.steps div { display: flex; flex-direction: column; }
	.steps .k { font-size: 0.8rem; color: var(--text-2); }
	.steps .v { font-size: 1.4rem; font-weight: 700; font-variant-numeric: tabular-nums; }
	.ladders { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0 2em; }
	.ladder tr.out td { color: var(--text-3); }
	.ladder tr.cut td { border-bottom: 2px solid var(--text); }
	.ladder tr.swap td { font-weight: 700; color: var(--text); background: var(--surface-2); }
	details { margin: 0.8em 0; }
	summary { cursor: pointer; color: var(--link); }
</style>
