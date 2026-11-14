<script>
	import Parliament from '#lib/components/Parliament.svelte';
	import GeoMap from '#lib/components/GeoMap.svelte';
	import Term from '#lib/components/Term.svelte';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { votes, points, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const nat = $derived(data.national);
	let view = $state(/** @type {'prelim' | 'projected'} */ ('projected'));
	// The footer links to #limitations; open the box when arriving that way.
	let limitsOpen = $state(false);
	$effect(() => {
		const check = () => { if (location.hash === '#limitations') limitsOpen = true; };
		check();
		addEventListener('hashchange', check);
		return () => removeEventListener('hashchange', check);
	});

	const names = $derived(Object.fromEntries(nat.parties.map((p) => [p.id, p.short])));
	const rows = $derived(
		nat.parties
			.filter((p) => nat.seats.prelim[p.id]?.total || nat.seats.projected[p.id]?.total)
			.map((p) => ({
				...p,
				prelim: nat.seats.prelim[p.id],
				projected: nat.seats.projected[p.id],
				change: nat.seats.projected[p.id].total - nat.seats.prelim[p.id].total
			}))
	);
	const seatCounts = $derived(
		Object.fromEntries(rows.map((r) => [r.id, { total: r[view].total, electorate: r[view].electorate }]))
	);
	// The other view's seats, so the chart can mark the seats that change hands.
	const otherCounts = $derived(
		Object.fromEntries(rows.map((r) => {
			const o = r[view === 'projected' ? 'prelim' : 'projected'];
			return [r.id, { total: o.total, electorate: o.electorate }];
		}))
	);
	const majority = $derived(Math.floor(nat.house[view] / 2) + 1);
	const flips = $derived(data.electorates.filter((e) => e.flips));
	const gains = $derived(rows.filter((r) => r.change > 0));
	const losses = $derived(rows.filter((r) => r.change < 0));
	const govt = ['national', 'act', 'nz-first'];
	const govtSeats = (/** @type {'prelim' | 'projected'} */ v) =>
		govt.reduce((a, p) => a + (nat.seats[v][p]?.total ?? 0), 0);
</script>

<svelte:head>
	<title>2026 special votes projection</title>
	<meta name="description" content="Projecting New Zealand’s 2026 final election result from the preliminary count, using 2023’s special votes, with every step shown." />
</svelte:head>

<h1>Projected final result, 2026 general election</h1>
<p class="byline">By Chuan-Zheng Lee<span class="credit">, with implementation by Claude</span></p>
<p class="lede">
	This projection applies the impact of the <strong>2023
	<Term tip="In a slight abuse of terminology, we’re using “special votes” to mean the difference between the preliminary and final counts. This also picks up any corrections to ordinary votes in the official count.">special votes</Term></strong>
	to the 2026 preliminary count.
</p>
<p class="lede">
	Under this projection:
	<strong
		>{#each [gains, losses] as group, g (g)}{g > 0 ? '; ' : ''}{#each group as r, i (r.id)}{i > 0 ? ', ' : ''}<span
					class="party-change" style:--c={colour(r.id)}>{r.short} {signed(r.change)}</span
				>{/each}{/each}</strong
	>.
	{#each flips as f (f.slug)}
		<a href={link(`/electorate/${f.slug}/`)}>{f.name}</a> flips from
		{f.prelim_winner_party ? names[f.prelim_winner_party] : 'other'} to
		{f.winner_party ? names[f.winner_party] : 'other'}.
	{/each}
	National, ACT and NZ First go from {govtSeats('prelim')} to {govtSeats('projected')} of
	{nat.house.projected} ({Math.floor(nat.house.projected / 2) + 1} for a majority).
</p>

<details class="limits" id="limitations" bind:open={limitsOpen}>
	<summary><strong>Before you believe this:</strong> Reasons this might not work (a.k.a. limitations)</summary>
	<ul>
		<li><strong>This is a mechanical projection, not a forecast.</strong></li>
		<li>
			Same-day enrolment and enrolment changes while voting no longer count as special votes in
			2026, which reportedly cut specials by about 30%. The 2023 mix of special voters may not carry
			over.
		</li>
		<li>
			When a 2023 party has no candidate in 2026, its special votes are effectively shared among
			everyone else in proportion, though in reality they’d lean to particular parties.
		</li>
		<li>
			Electorates are on new boundaries, so their 2023 results are rebuilt from population weights.
			These stand in for enrolled electors (and, for Māori electorates, for the Māori roll).
		</li>
	</ul>
</details>

<div class="toggle" role="group" aria-label="Count">
	<button aria-pressed={view === 'prelim'} onclick={() => (view = 'prelim')}>Preliminary count</button>
	<button aria-pressed={view === 'projected'} onclick={() => (view = 'projected')}>Projected final</button>
</div>

<div class="grid">
	<Parliament
		seats={seatCounts}
		{names}
		compare={otherCounts}
		highlightLabel={view === 'projected' ? 'gained with specials' : 'lost with specials'}
		{majority}
		overhang={nat.house[view] - 120}
	/>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party</th>
					<th class="num">Prelim</th>
					<th class="num">Projected</th>
					<th class="num">Elec.</th>
					<th class="num">List</th>
					<th class="num">Change</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.id)}
					<tr>
						<td><span class="swatch" style:background={colour(r.id)}></span>{r.short}</td>
						<td class="num">{r.prelim.total}</td>
						<td class="num"><strong>{r.projected.total}</strong></td>
						<td class="num muted">{r.projected.electorate}</td>
						<td class="num muted">{r.projected.list}</td>
						<td class="num">{r.change ? signed(r.change) : ''}</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{nat.house.prelim}</td>
					<td class="num">{nat.house.projected}</td>
					<td colspan="3"></td>
				</tr>
			</tfoot>
		</table>
		<p class="small muted">
			Projected party votes: {votes(nat.prelim_total)} preliminary + {votes(nat.projected_specials)}
			projected specials. <a href={link('/party-vote/')}>Why these seats change →</a>
		</p>
	</div>
</div>

<h2>Electorates</h2>
<p>
	Colour is the {view === 'prelim' ? 'preliminary' : 'projected'} leader in each electorate (switch
	with the toggle above). The hatched electorate flips with special votes. Boxes on the main map show
	the city insets.
</p>
<p class="muted small">
	Seats with the narrowest projected margins:
	{#each data.electorates.filter((e) => !e.omitted).toSorted((a, b) => a.margin_pct - b.margin_pct).slice(0, 5) as e, i (e.slug)}{i > 0 ? ', ' : ''}<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a> ({points(e.margin_pct, 1)}){/each}.
</p>
<GeoMap electorates={data.electorates} {names} {view} />
<p class="muted small">
	Click an electorate for its working, or <a href={link('/electorates/')}>see all electorates in a table →</a>
</p>

<style>
	.byline { margin-top: -0.4em; color: var(--text-2); font-size: 0.9rem; }
	.byline .credit { color: var(--text-3); }
	.lede { font-size: 1.05rem; }
	.lede + .lede { margin-top: 0.6em; }
	/* Party colour, pulled towards the text colour so light party colours stay readable. */
	.party-change { color: color-mix(in srgb, var(--c) 65%, var(--text)); white-space: nowrap; }
	.limits {
		border: 1px solid var(--warn-border); border-left-width: 4px; background: var(--warn-bg);
		border-radius: 4px; padding: 0.55em 0.9em; margin: 1em 0; max-width: 72ch;
	}
	.limits summary { cursor: pointer; color: var(--warn-text); }
	.limits[open] summary { margin-bottom: 0.3em; }
	.limits p, .limits ul { margin: 0.3em 0; }
	.limits ul { padding-left: 1.2em; }
	.limits li + li { margin-top: 0.25em; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0.8em 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
	.grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 1.5em; align-items: start; }
	@media (max-width: 760px) { .grid { grid-template-columns: minmax(0, 1fr); } }
</style>
