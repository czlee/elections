<script>
	import DeltaBars from '#lib/components/DeltaBars.svelte';
	import MultiplierBars from '#lib/components/MultiplierBars.svelte';
	import Sources from '#lib/components/Sources.svelte';
	import { colour } from '#lib/parties.js';
	import { votes, pct, pp, mult, signed } from '#lib/format.js';

	let { data } = $props();
	const n = $derived(data.national);
	const src = $derived(n.sources);
	const names = $derived(Object.fromEntries([...n.base_parties, ...n.parties].map((p) => [p.id, p.short])));
	// Parties shown in charts: those over 0.5% in either count; the rest are in the tables.
	const major = $derived(n.parties.filter((p) => p.prelim_share > 0.005 || p.final_share > 0.005));
	const baseMajor = $derived(n.base_parties.filter((p) => p.prelim_share > 0.005));
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
	const lastIn = (/** @type {any[]} */ l) => l.filter((r) => r.allocated).at(-1);
	const firstOut = (/** @type {any[]} */ l) => l.find((r) => !r.allocated);
</script>

<svelte:head>
	<title>Party vote projection · 2026 special votes</title>
</svelte:head>

<h1>Party vote projection</h1>
<p>
	The party vote from the 2026 preliminary count, plus a projection of the special votes still
	to be counted. Each party gets the same share of the special votes, relative to its
	preliminary share, as it did in {n.base}.
</p>

<div class="steps">
	<div><span class="k">2026 preliminary</span><span class="v">{votes(n.prelim_total)}</span></div>
	<div><span class="k">+ projected specials</span><span class="v">{votes(n.projected_specials)}</span></div>
	<div><span class="k">= projected final</span><span class="v">{votes(n.final_total)}</span></div>
</div>

<h2>1. How many special votes</h2>
<p>
	The Electoral Commission estimated <strong>{votes(n.estimate_2026)}</strong> special votes in
	2026. In {n.base} it estimated {votes(n.estimate_base)}, and the official count ended up with
	{votes(n.base_totals.specials)} more valid party votes than the preliminary count
	({votes(n.base_totals.final)} − {votes(n.base_totals.prelim)}), a ratio of
	<strong>{n.adjustment.toFixed(4)}</strong>. Applying the same ratio:
	{votes(n.estimate_2026)} × {n.adjustment.toFixed(4)} = <strong>{votes(n.projected_specials)}</strong>
	projected special party votes.
</p>
<p class="small muted">
	"Special votes" here means final minus preliminary valid party votes, which also picks up any
	changes to ordinary votes in the official count. The estimate is of special votes cast; the
	count is of valid party votes, so the ratio also absorbs special votes that were disallowed or
	informal.
</p>
<Sources items={[src.release_2026, src.release_2023, src.prelim_2023, src.final_2023]} />

<h2>2. Each party's {n.base} multiplier</h2>
<p>
	A party's multiplier is its share of the {n.base} special votes divided by its share of the
	{n.base} preliminary count. Above 1, it did better among special voters.
</p>
<MultiplierBars rows={baseMajor.map((p) => ({ id: p.id, label: p.short, value: p.multiplier }))} />
<details>
	<summary>All {n.base} parties</summary>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party ({n.base})</th>
					<th class="num">Preliminary</th>
					<th class="num">Final</th>
					<th class="num">Specials</th>
					<th class="num">Prelim share</th>
					<th class="num">Special share</th>
					<th class="num">Multiplier</th>
				</tr>
			</thead>
			<tbody>
				{#each n.base_parties as p (p.id)}
					<tr>
						<td><span class="swatch" style:background={colour(p.id)}></span>{p.short}</td>
						<td class="num">{votes(p.prelim)}</td>
						<td class="num">{votes(p.final)}</td>
						<td class="num">{signed(p.specials)}</td>
						<td class="num">{pct(p.prelim_share)}</td>
						<td class="num">{pct(p.special_share)}</td>
						<td class="num"><strong>{mult(p.multiplier)}</strong></td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{votes(n.base_totals.prelim)}</td>
					<td class="num">{votes(n.base_totals.final)}</td>
					<td class="num">{signed(n.base_totals.specials)}</td>
					<td colspan="3"></td>
				</tr>
			</tfoot>
		</table>
	</div>
	<Sources items={[src.prelim_2023, src.final_2023]} />
</details>

<h2>3. Sharing out the 2026 specials</h2>
<p>
	Each 2026 party's share of the projected specials is its preliminary share times its multiplier,
	scaled so the shares add up to 100%. Parties that are new in 2026 get a multiplier of 1; a party
	that was part of an umbrella party in {n.base} uses the umbrella's multiplier.
</p>
<DeltaBars rows={major.map((p) => ({ id: p.id, label: p.short, from: p.prelim_share, to: p.final_share }))} />
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th>Party</th>
				<th class="num">Preliminary</th>
				<th class="num">Share</th>
				<th class="num">× multiplier</th>
				<th class="num">Special share</th>
				<th class="num">+ specials</th>
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
					<td class="num">{mult(p.multiplier)}</td>
					<td class="num">{pct(p.special_share)}</td>
					<td class="num">{signed(p.specials)}</td>
					<td class="num">{votes(p.final)}</td>
					<td class="num"><strong>{pct(p.final_share)}</strong></td>
					<td class="num">{pp(p.final_share - p.prelim_share)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<Sources items={[src.prelim_2026]} />

<h2>4. Seats</h2>
<p>
	The 120 seats are shared out by Sainte-Laguë among parties over 5% or with an electorate: each
	seat goes to the highest remaining quotient, votes ÷ (2s + 1), where s is the seats the party
	already has. Seat changes are decided at the margin, by which quotients land just above or below
	seat 120. Bold rows are seats that cross the line:
	{#each changed as p, i (p.id)}{i > 0 ? ', ' : ''}{p.short} {signed(
			n.seats.projected[p.id].total - n.seats.prelim[p.id].total
		)}{/each}.
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
<h3>Overhang</h3>
<p>
	A party keeps every electorate it wins, even beyond its share of the 120, and the House grows to
	fit:
	{#each overhang('projected') as [p, d], i (p)}{i > 0 ? '; ' : ''}{names[p]} wins
		{n.seats.projected[p].electorate} electorates against a Sainte-Laguë share of
		{n.entitlement.projected[p]} (+{d}){/each}. So the House has {n.house.projected} seats in both
	counts. Electorate winners here are the projected ones; see the electorate pages.
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
