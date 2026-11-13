<script>
	import Parliament from '#lib/components/Parliament.svelte';
	import ElectorateList from '#lib/components/ElectorateList.svelte';
	import HexMap from '#lib/components/HexMap.svelte';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { votes, pct, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const nat = $derived(data.national);
	let view = $state(/** @type {'prelim' | 'projected'} */ ('projected'));

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
	// Ring the seats that change: gains in the projected view, losses in the preliminary view.
	const highlight = $derived(
		Object.fromEntries(
			rows.map((r) => [r.id, view === 'projected' ? Math.max(0, r.change) : Math.max(0, -r.change)])
		)
	);
	const majority = $derived(Math.floor(nat.house[view] / 2) + 1);
	const flips = $derived(data.electorates.filter((e) => e.flips));
	const gains = $derived(rows.filter((r) => r.change > 0));
	const losses = $derived(rows.filter((r) => r.change < 0));
	const govt = ['national', 'act', 'nz-first'];
	const govtSeats = (/** @type {'prelim' | 'projected'} */ v) =>
		govt.reduce((a, p) => a + (nat.seats[v][p]?.total ?? 0), 0);
	const list = (/** @type {typeof rows} */ rs) => rs.map((r) => `${r.short} ${signed(r.change)}`).join(', ');
</script>

<svelte:head>
	<title>2026 special votes projection</title>
	<meta name="description" content="Projecting New Zealand's 2026 final election result from the preliminary count, using 2023's special votes, with every step shown." />
</svelte:head>

<h1>Projected final result, 2026 general election</h1>
<p class="lede">
	Applying 2023's special-vote patterns to the 2026 preliminary count:
	<strong>{list(gains)}; {list(losses)}</strong>.
	{#each flips as f (f.slug)}
		<a href={link(`/electorate/${f.slug}/`)}>{f.name}</a> flips from
		{f.prelim_winner_party ? names[f.prelim_winner_party] : 'other'} to
		{f.winner_party ? names[f.winner_party] : 'other'}.
	{/each}
	National, ACT and NZ First go from {govtSeats('prelim')} to {govtSeats('projected')} of
	{nat.house.projected} ({Math.floor(nat.house.projected / 2) + 1} for a majority).
</p>

<div class="toggle" role="group" aria-label="Count">
	<button aria-pressed={view === 'prelim'} onclick={() => (view = 'prelim')}>Preliminary count</button>
	<button aria-pressed={view === 'projected'} onclick={() => (view = 'projected')}>Projected final</button>
</div>

<div class="grid">
	<Parliament
		seats={seatCounts}
		{names}
		{highlight}
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
			projected specials. <a href={link('/national/')}>Why these seats change →</a>
		</p>
	</div>
</div>

<h2>Electorates</h2>
<div class="map-row">
	<HexMap electorates={data.electorates} {names} {view} />
	<div>
		<p>
			One hexagon per electorate, all the same size, arranged roughly geographically. Colour is the
			{view === 'prelim' ? 'preliminary' : 'projected'} leader (switch with the toggle above). The
			outlined hexagon flips with special votes.
		</p>
		<p class="muted small">
			Seats with the narrowest projected margins:
			{#each data.electorates.filter((e) => !e.omitted).toSorted((a, b) => a.margin_pct - b.margin_pct).slice(0, 5) as e, i (e.slug)}{i > 0 ? ', ' : ''}<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a> ({pct(e.margin_pct, 1)}){/each}.
		</p>
	</div>
</div>
<p class="muted small">
	Sorted by projected margin. "Needs" is the special-vote multiplier the projected runner-up
	would have needed to tie, against the one they got from 2023. Click an electorate for its
	working.
</p>
<ElectorateList electorates={data.electorates} {names} />

<style>
	.lede { font-size: 1.05rem; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0.8em 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
	.grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 1.5em; align-items: start; }
	@media (max-width: 760px) { .grid { grid-template-columns: minmax(0, 1fr); } }
	.map-row { display: grid; grid-template-columns: minmax(0, 420px) minmax(0, 1fr); gap: 1.5em; align-items: start; }
	@media (max-width: 760px) { .map-row { grid-template-columns: minmax(0, 1fr); } }
</style>
