<script>
	import Parliament from '#lib/components/Parliament.svelte';
	import GeoMap from '#lib/components/GeoMap.svelte';
	import Term from '#lib/components/Term.svelte';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { votes, pct, points, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const nat = $derived(data.national);
	let view = $state(/** @type {'counted' | 'none'} */ ('none'));
	// The footer links to #limitations; open the box when arriving that way.
	let limitsOpen = $state(false);
	$effect(() => {
		const check = () => { if (location.hash === '#limitations') limitsOpen = true; };
		check();
		addEventListener('hashchange', check);
		return () => removeEventListener('hashchange', check);
	});

	const names = $derived(Object.fromEntries(nat.parties.map((/** @type {any} */ p) => [p.id, p.short])));
	const name = (/** @type {string | null} */ id) => (id ? names[id] ?? id : 'Independent');
	const rows = $derived(
		nat.parties
			.filter((/** @type {any} */ p) => nat.seats.counted[p.id]?.total || nat.seats.none[p.id]?.total)
			.map((/** @type {any} */ p) => {
				const c = nat.seats.counted[p.id] ?? { total: 0, electorate: 0, list: 0 };
				const n = nat.seats.none[p.id] ?? { total: 0, electorate: 0, list: 0 };
				return { ...p, counted: c, none: n, change: n.total - c.total };
			})
			.toSorted((/** @type {any} */ a, /** @type {any} */ b) => b.none.total - a.none.total || b.counted.total - a.counted.total)
	);
	const seatCounts = $derived(
		Object.fromEntries(rows.map((/** @type {any} */ r) => [r.id, { total: r[view].total, electorate: r[view].electorate }]))
	);
	const otherCounts = $derived(
		Object.fromEntries(rows.map((/** @type {any} */ r) => {
			const o = r[view === 'none' ? 'counted' : 'none'];
			return [r.id, { total: o.total, electorate: o.electorate }];
		}))
	);
	const house = $derived(nat.house[view]);
	const majority = $derived(Math.floor(house / 2) + 1);
	const gains = $derived(rows.filter((/** @type {any} */ r) => r.change > 0));
	const losses = $derived(rows.filter((/** @type {any} */ r) => r.change < 0));
	const flips = $derived(data.electorates.filter((/** @type {any} */ e) => e.flips));
	/** Flips grouped by "from → to", as [{from, to, list}]. */
	const flipGroups = $derived.by(() => {
		/** @type {Map<string, any>} */
		const m = new Map();
		for (const f of flips) {
			const key = `${f.prelim_winner_party}>${f.winner_party}`;
			if (!m.has(key)) m.set(key, { from: f.prelim_winner_party, to: f.winner_party, list: [] });
			m.get(key).list.push(f);
		}
		return [...m.values()];
	});
	/** Overhang in a count: seats above Sainte-Laguë share for parties whose electorates exceed it. */
	const overhang = (/** @type {'counted' | 'none'} */ v) =>
		rows
			.map((/** @type {any} */ r) => ({ id: r.id, extra: r[v].total - (nat.entitlement[v][r.id] ?? 0), ent: nat.entitlement[v][r.id] ?? 0 }))
			.filter((/** @type {any} */ x) => x.extra > 0 && rows.find((/** @type {any} */ r) => r.id === x.id)[v].list === 0);
	const overhangSentence = (/** @type {'counted' | 'none'} */ v) => {
		const o = overhang(v);
		if (!o.length) return `With no Māori electorates there’s no overhang: the House has ${nat.house[v]} seats.`;
		return `As counted, ${o.map((/** @type {any} */ x) => `${name(x.id)} has ${x.extra} overhang seat${x.extra === 1 ? '' : 's'} (${x.ent} by share, ${x.ent + x.extra} electorates)`).join(' and ')}, so the House has ${nat.house[v]} seats.`;
	};
	const winsOf = (/** @type {'counted' | 'none'} */ v, /** @type {string} */ id) => nat.seats[v][id]?.electorate ?? 0;

	/** @type {Record<string, string>} */
	const HOW = {
		'to Labour': 'Labour’s candidate (assumption 2)',
		'same party': 'The same party’s candidate (assumption 3)',
		'to bloc major party (no candidate there)': 'Labour’s candidate: no Green candidate there (assumption 3)',
		'discarded: independent': 'Dropped (assumption 4)',
		'discarded: no candidate there and no bloc': 'Dropped: no candidate there, no bloc (assumption 4)'
	};
	const dropped = $derived(
		nat.moved.filter((/** @type {any} */ m) => m.how.startsWith('discarded'))
	);
	const droppedIndep = $derived(dropped.filter((/** @type {any} */ m) => m.party === null).reduce((a, m) => a + m.votes, 0));
	const droppedOther = $derived(dropped.filter((/** @type {any} */ m) => m.party !== null).reduce((a, m) => a + m.votes, 0));
	const maoriRoll = $derived(nat.maori_candidate_votes);
	/** The narrowest new margins, for the limitations. */
	const close = $derived(data.electorates.toSorted((/** @type {any} */ a, /** @type {any} */ b) => a.margin - b.margin).slice(0, 3));
</script>

<h1>The 2026 election with no Māori electorates</h1>
<p class="byline">By Chuan-Zheng Lee<span class="credit">, with implementation by Claude</span></p>
<p class="lede">
	What would the 2026 <strong>electorate</strong> results have been if there were no Māori electorates, and
	every Māori-roll voter had voted in the general electorate for their area instead? This applies a few
	<a href="#assumptions">assumptions</a> to the 2026 <strong>preliminary count</strong>. The party vote
	doesn’t distinguish between rolls, so it stays as it was; only the electorates change.
</p>
<p class="lede">
	Under these assumptions, <strong>{flips.length} of the {nat.general_electorates} general electorates flip</strong>:
	{#each flipGroups as g, k (k)}{k > 0 ? '; ' : ''}{#each g.list as f, i (f.slug)}{i > 0 ? (i === g.list.length - 1 ? ' and ' : ', ') : ''}<a href={link(`/electorate/${f.slug}/`)}>{f.name}</a>{/each} from {name(g.from)} to {name(g.to)}{/each}.
	Electorate wins (all {nat.general_electorates + nat.maori_electorates.length} electorates as counted, the {nat.general_electorates} general ones after) go from
	{#each ['national', 'labour'] as id, i (id)}{i > 0 ? ' and ' : ''}{name(id)} {winsOf('counted', id)} to {winsOf('none', id)}{/each},
	with {name('green')} and {name('act')} unchanged, and
	{name('te-pati-maori')} losing the {winsOf('counted', 'te-pati-maori')} electorates it won.
	Seats:
	<strong
		>{#each [gains, losses] as group, g (g)}{g > 0 && gains.length ? '; ' : ''}{#each group as r, i (i)}{i > 0 ? ', ' : ''}<span
					class="party-change" style:--c={colour(r.id)}>{r.short} {signed(r.change)}</span
				>{/each}{/each}</strong
	>. {name('te-pati-maori')} would have no seats because it got {pct(nat.tpm_party_share)} of the party vote,
	under the 5% threshold, and no electorates.
</p>

<h2 id="assumptions">What this assumes</h2>
<p>
	{votes(maoriRoll)} votes were cast for Māori electorate candidates across {nat.voting_places.toLocaleString('en-NZ')}
	voting-place results. Each is moved to a general electorate as follows. These are assumptions, not findings.
</p>
<ol class="assumptions">
	<li>
		<strong>Voters follow their voting places.</strong> A Māori-roll vote cast at a voting place is counted in
		the general electorate that place is in. This isn’t exactly right (people vote away from home, at
		advance voting places and with mobile teams), but we have to assume something, and every
		voting place that took Māori-electorate votes has a general electorate it belongs to.
	</li>
	<li>
		<strong>Every Te Pāti Māori voter would have voted for the Labour candidate.</strong> So would every
		Te Tai Tokerau Party voter (a Māori-electorate-only party in the same bloc). This is the most
		favourable assumption for Labour: the <a href="#sensitivity">table below</a> shows what happens if
		fewer of them do.
	</li>
	<li>
		<strong>Everyone else votes for their party’s candidate in that general electorate.</strong> If their
		party has no candidate there, the vote goes to the major party of the same bloc: Labour for Green
		(this applies to {votes(nat.moved.find((/** @type {any} */ m) => m.how.startsWith('to bloc'))?.votes ?? 0)} votes). The
		same rule would send New Zealand First and ACT voters to National, but no right-bloc party stood in
		a Māori electorate other than National itself, so it was never needed.
	</li>
	<li>
		<strong>Some votes are dropped.</strong> Independents’ votes ({votes(droppedIndep)}) are dropped. So are
		{votes(droppedOther)} votes for Legalise Cannabis, Opportunity, NZ Loyal and Your PIC Party in
		electorates where those parties had no candidate, and which have no bloc to fall back on. Even if all of them had gone to a general electorate’s runner-up, no result would change.
	</li>
</ol>
<div class="table-wrap">
	<table>
		<thead><tr><th>Māori-electorate vote for</th><th>Counted for</th><th class="num">Votes</th></tr></thead>
		<tbody>
			{#each nat.moved as m, i (i)}
				<tr>
					<td>{#if m.party}<span class="swatch" style:background={colour(m.party)}></span>{/if}{name(m.party)}</td>
					<td>{HOW[m.how] ?? m.how}</td>
					<td class="num">{votes(m.votes)}</td>
				</tr>
			{/each}
		</tbody>
		<tfoot><tr><td>Total</td><td></td><td class="num">{votes(nat.moved.reduce((/** @type {number} */ a, /** @type {any} */ m) => a + m.votes, 0))}</td></tr></tfoot>
	</table>
</div>

<details class="limits" id="limitations" bind:open={limitsOpen}>
	<summary><strong>Before you believe this:</strong> Reasons this might not work (a.k.a. limitations)</summary>
	<ul>
		<li><strong>This is a thought experiment, not a forecast.</strong> Campaigns, candidates and tactical voting would all have been different with no Māori electorates.</li>
		<li>
			It uses the <strong>preliminary count</strong> only, on both sides: neither the general nor the Māori
			roll has its special votes, which will change both.
		</li>
		<li>
			The <strong>party vote is left as it was</strong>. In reality, Te Pāti Māori would probably have
			campaigned (and been voted for) differently without its electorates, which could change who gets
			list seats.
		</li>
		<li>
			<strong>Boundaries stay as they were.</strong> With the Māori electorates gone, the general
			electorates would have been redrawn to be bigger, so these aren’t the seats there would have been.
		</li>
		<li>
			The narrowest electorates are sensitive to the assumptions above:
			{#each close as e, i (e.slug)}{i > 0 ? ', ' : ''}<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a>
				({e.flips ? 'flips' : 'stays'} {name(e.winner_party)} by {votes(e.margin)})
			{/each}.
		</li>
	</ul>
</details>

<div class="toggle" role="group" aria-label="Count">
	<button aria-pressed={view === 'counted'} onclick={() => (view = 'counted')}>As counted (preliminary)</button>
	<button aria-pressed={view === 'none'} onclick={() => (view = 'none')}>No Māori electorates</button>
</div>
<div class="grid">
	<Parliament
		seats={seatCounts}
		{names}
		compare={otherCounts}
		highlightLabel={view === 'none' ? 'gained without Māori electorates' : 'lost without Māori electorates'}
		{majority}
		overhang={house - 120}
	/>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party</th>
					<th class="num">As counted</th>
					<th class="num">No Māori elec.</th>
					<th class="num">Elec.</th>
					<th class="num">List</th>
					<th class="num">Change</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.id)}
					<tr>
						<td><span class="swatch" style:background={colour(r.id)}></span>{r.short}</td>
						<td class="num">{r.counted.total}</td>
						<td class="num"><strong>{r.none.total}</strong></td>
						<td class="num muted">{r.none.electorate}</td>
						<td class="num muted">{r.none.list}</td>
						<td class="num">{r.change ? signed(r.change) : ''}</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<td>Total</td>
					<td class="num">{nat.house.counted}</td>
					<td class="num">{nat.house.none}</td>
					<td colspan="3"></td>
				</tr>
			</tfoot>
		</table>
		<p class="small muted">
			Seats are allocated from the preliminary party vote ({votes(nat.party_vote_total)} valid votes) and the
			electorates each party wins in that count. Elec. and List are for the “No Māori elec.” column.
			{overhangSentence('counted')}{overhang('none').length ? '' : ' With no Māori electorates, nobody has any.'}
		</p>
	</div>
</div>

<h2>Electorates</h2>
<p>
	Colour is the {view === 'counted' ? 'preliminary' : 'new'} leader in each of the {nat.general_electorates}
	general electorates (switch with the toggle above). {flips.length === 1 ? 'The hatched electorate flips' : 'Hatched electorates flip'}
	when the Māori-roll votes are added. Boxes on the main map show the city insets.
</p>
<p class="muted small">
	Seats with the narrowest new margins:
	{#each data.electorates.toSorted((/** @type {any} */ a, /** @type {any} */ b) => a.margin_pct - b.margin_pct).slice(0, 5) as e, i (i)}{i > 0 ? ', ' : ''}<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a> ({points(e.margin_pct, 1)}){/each}.
</p>
<GeoMap electorates={data.electorates} {names} {view} />
<p class="muted small">
	Click an electorate for its working, or <a href={link('/electorates/')}>see all electorates in a table →</a>
</p>

<h2 id="sensitivity">What if fewer Te Pāti Māori voters voted Labour?</h2>
<p>
	Assumption 2 is the one that matters most: Te Pāti Māori’s votes ({votes(nat.moved.find((/** @type {any} */ m) => m.party === 'te-pati-maori')?.votes ?? 0)})
	are far more than any other party’s here. This shows the result if only some share of them went to Labour, and the rest
	<Term tip="Not counted for anyone: they’d have voted for another candidate we can’t identify, or not voted at all.">went nowhere</Term>.
</p>
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th class="num">Share to Labour</th>
				<th class="num">Electorates flipping</th>
				<th>Which</th>
				<th class="num">Labour wins</th>
				<th class="num">National wins</th>
			</tr>
		</thead>
		<tbody>
			{#each nat.sensitivity as s (s.share)}
				<tr>
					<td class="num">{pct(s.share, 0)}</td>
					<td class="num">{s.flips.length}</td>
					<td>{s.flips.join(', ')}</td>
					<td class="num">{s.labour}</td>
					<td class="num">{s.national}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<p class="muted small">
	“Wins” are among the {nat.general_electorates} general electorates. The “Labour needs” column on the
	<a href={link('/electorates/')}>electorates page</a> gives the exact share each electorate needs.
</p>

<style>
	.byline { color: var(--text-2); margin: 0 0 1em; }
	.credit { color: var(--text-3); }
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
	.limits ul { margin: 0.3em 0; }
	.limits ul { padding-left: 1.2em; }
	.limits li + li { margin-top: 0.25em; }
	.assumptions { max-width: 72ch; padding-left: 1.4em; }
	.assumptions li { margin: 0.6em 0; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0.8em 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
	.grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 1.5em; align-items: start; }
	@media (max-width: 760px) { .grid { grid-template-columns: minmax(0, 1fr); } }
</style>
