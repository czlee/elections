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
	/** Assumption 5: whether the 5% threshold is waived for Māori parties in the no-Māori-electorates count. */
	let waiver = $state(true);
	const noKey = $derived(waiver ? 'none' : 'none_no_waiver');
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
			.filter((/** @type {any} */ p) => nat.seats.counted[p.id]?.total || nat.seats[noKey][p.id]?.total)
			.map((/** @type {any} */ p) => {
				const c = nat.seats.counted[p.id] ?? { total: 0, electorate: 0, list: 0 };
				const n = nat.seats[noKey][p.id] ?? { total: 0, electorate: 0, list: 0 };
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
	const house = $derived(nat.house[view === 'none' ? noKey : view]);
	const majority = $derived(Math.floor(house / 2) + 1);
	/** The headline seat changes, with the threshold waived (the default): gains first, then the biggest losses. */
	const headlineChanges = $derived(
		nat.parties
			.map((/** @type {any} */ p) => ({ ...p, change: (nat.seats.none[p.id]?.total ?? 0) - (nat.seats.counted[p.id]?.total ?? 0) }))
			.filter((/** @type {any} */ r) => r.change)
			.toSorted((/** @type {any} */ a, /** @type {any} */ b) => Number(b.change > 0) - Number(a.change > 0) || (a.change > 0 ? b.change - a.change : a.change - b.change))
	);
	const waivedTpm = $derived(nat.seats.none['te-pati-maori']?.total ?? 0);
	/** The party that gets the seat Te Pāti Māori would have if the threshold isn't waived. */
	const seatGoesTo = $derived(
		nat.parties.find((/** @type {any} */ p) => (nat.seats.none_no_waiver[p.id]?.total ?? 0) > (nat.seats.none[p.id]?.total ?? 0))?.id
	);
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
			.map((/** @type {any} */ r) => {
				const ent = nat.entitlement[v === 'none' ? noKey : v][r.id] ?? 0;
				return { id: r.id, extra: r[v].total - ent, ent };
			})
			.filter((/** @type {any} */ x) => x.extra > 0 && rows.find((/** @type {any} */ r) => r.id === x.id)[v].list === 0);
	/** "Neither X nor Y would have an overhang": the parties with an overhang as counted, if there's none without Māori electorates. */
	const noOverhang = $derived.by(() => {
		const was = overhang('counted').map((/** @type {any} */ x) => name(x.id));
		if (!was.length || overhang('none').length) return '';
		return was.length === 1 ? `${was[0]} would not have an overhang.` : `Neither ${was.join(' nor ')} would have an overhang.`;
	});
	const winsOf = (/** @type {'counted' | 'none'} */ v, /** @type {string} */ id) => nat.seats[v][id]?.electorate ?? 0;
	/** A share as a percentage with at most one decimal, e.g. 12.3% or 50%. */
	const share = (/** @type {number} */ x) => `${Number((100 * x).toFixed(1))}%`;
	const labourGain = $derived(winsOf('none', 'labour') - winsOf('counted', 'labour'));

	const dropped = $derived(
		nat.moved.filter((/** @type {any} */ m) => m.how.startsWith('discarded'))
	);
	const droppedIndep = $derived(dropped.filter((/** @type {any} */ m) => m.party === null).reduce((a, m) => a + m.votes, 0));
	const droppedOther = $derived(dropped.filter((/** @type {any} */ m) => m.party !== null).reduce((a, m) => a + m.votes, 0));
	const maoriRoll = $derived(nat.maori_candidate_votes);
	const toBloc = $derived(nat.moved.find((/** @type {any} */ m) => m.how.startsWith('to bloc'))?.votes ?? 0);
	/** Votes by assumption and outcome. Small parties' own candidates are merged. */
	const tableRows = $derived.by(() => {
		const sum = (/** @type {any[]} */ xs) => xs.reduce((/** @type {number} */ a, /** @type {any} */ m) => a + m.votes, 0);
		const same = nat.moved.filter((/** @type {any} */ m) => m.how === 'same party');
		const big = same.filter((/** @type {any} */ m) => m.votes >= 5000);
		const ORDER = ['national', 'top', 'alcp', 'nz-loyal'];
		const rank = (/** @type {string} */ id) => (ORDER.includes(id) ? ORDER.indexOf(id) : ORDER.length);
		const small = same
			.filter((/** @type {any} */ m) => m.votes < 5000)
			.toSorted((/** @type {any} */ a, /** @type {any} */ b) => rank(a.party) - rank(b.party));
		return [
			{ a: 2, who: 'TPM+: Te Pāti Māori, Te Tai Tokerau and Tākuta Ferris', parties: ['te-pati-maori'], to: 'labour', votes: sum(nat.moved.filter((/** @type {any} */ m) => m.how === 'to Labour')) },
			...big.map((/** @type {any} */ m) => ({ a: 3, who: name(m.party), parties: [m.party], to: m.party, votes: m.votes })),
			{ a: 3, who: `Green, where there was no Green candidate`, parties: ['green'], to: 'labour', votes: toBloc },
			{ a: 3, who: `${small.map((/** @type {any} */ m) => name(m.party)).join(', ')}`, parties: small.map((/** @type {any} */ m) => m.party), to: 'own', votes: sum(small) },
			{ a: 4, who: 'Independents; parties with no candidate or bloc', parties: [null], to: null, votes: sum(nat.moved.filter((/** @type {any} */ m) => m.how.startsWith('discarded'))) }
		];
	});
	/** Votes from Te Pāti Māori, the Te Tai Tokerau Party and Tākuta Ferris, who all go to Labour. */
	const group = $derived(
		nat.moved.filter((/** @type {any} */ m) => m.how === 'to Labour').reduce((/** @type {number} */ a, /** @type {any} */ m) => a + m.votes, 0)
	);
	/** The narrowest new margins, for the limitations. */
	const close = $derived(data.electorates.toSorted((/** @type {any} */ a, /** @type {any} */ b) => a.margin - b.margin).slice(0, 3));
</script>

<h1>The 2026 election if there were no Māori electorates</h1>
<p class="byline">By Chuan-Zheng Lee<span class="credit">, with implementation by Claude</span></p>
<p class="lede">
	What would the 2026 <strong>electorate</strong> results have been if there were no Māori electorates, and
	every Māori-roll voter had voted in the general electorate for their area instead? This applies a few
	<a href="#assumptions">assumptions</a> to the 2026 <strong>preliminary count</strong>. The party vote
	stays as-is; only the electorates change.
</p>
<p class="lede">
	Under the <a href="#assumptions">assumptions</a>, <strong>{flips.length} of the {nat.general_electorates} general electorates would flip</strong>
	from {name(flipGroups[0].from)} to {name(flipGroups[0].to)}, for a net gain of {labourGain}
	electorate{labourGain === 1 ? '' : 's'} for {name('labour')}. {noOverhang} Overall seats:
	<strong
		>{#each headlineChanges as r, i (r.id)}{i > 0 ? ', ' : ''}<span
				class="party-change" style:--c={colour(r.id)}>{r.short} {signed(r.change)}</span
			>{/each}</strong
	>.
</p>
<p class="lede">
	If the 5% threshold is waived for {name('te-pati-maori')} (per the 1986
	<a href="https://elections.nz/democracy-in-nz/what-is-new-zealands-system-of-government/report-of-the-royal-commission-on-the-electoral-system" target="_blank" rel="noopener">Royal Commission</a><sup><a href="#fn-waiver" id="fnref-waiver">1</a></sup>), they keep
	{waivedTpm} list seat{waivedTpm === 1 ? '' : 's'}; otherwise, that seat goes to {name(seatGoesTo)}.
	<a href="#threshold">You can switch this below.</a>
</p>

<h2 id="assumptions">Assumptions</h2>
<p>
	{votes(maoriRoll)} votes were cast for Māori-electorate candidates. Each is counted in a general electorate as
	follows. <strong>TPM+</strong> is shorthand for voters for Te Pāti Māori, the Te Tai Tokerau Party and
	Tākuta Ferris.
</p>
<ol class="assumptions">
	<li>
		<strong>Voters follow their voting places.</strong> A Māori-roll vote cast at a voting place is counted in
		the general electorate that place is in. This isn’t exactly right (people vote away from home), but we have to assume something.
	</li>
	<li>
		<strong>TPM+ voters vote Labour.</strong> All {votes(group)} of them. This is the most favourable assumption
		for Labour: <a href="#sensitivity">see what happens if fewer do</a>.
	</li>
	<li>
		<strong>Everyone else votes for their party’s candidate there.</strong> If their party has no candidate, they
		vote for the major party of the same bloc.
	</li>
	<li>
		<strong>Some votes are dropped:</strong> other independents ({votes(droppedIndep)}), and voters for parties with no
		candidate there and no bloc ({votes(droppedOther)}). Even if all of them had gone to a runner-up, no result would change.
	</li>
</ol>
<details class="votes">
	<summary>Where the {votes(maoriRoll)} Māori-electorate votes went</summary>
	<div class="table-wrap">
	<table>
		<thead><tr><th>Assumption</th><th>Māori-electorate voters for</th><th>Counted for</th><th class="num">Votes</th></tr></thead>
		<tbody>
			{#each tableRows as r, i (i)}
				<tr>
					<td>{r.a}</td>
					<td>{#each r.parties as p, k (k)}<span class="swatch" style:background={colour(p)}></span>{/each}{r.who}</td>
					<td>{#if r.to === 'own'}Their own candidates{:else if r.to}<span class="swatch" style:background={colour(r.to)}></span>{name(r.to)}{:else}Dropped{/if}</td>
					<td class="num">{votes(r.votes)}</td>
				</tr>
			{/each}
		</tbody>
		<tfoot><tr><td></td><td>Total</td><td></td><td class="num">{votes(nat.moved.reduce((/** @type {number} */ a, /** @type {any} */ m) => a + m.votes, 0))}</td></tr></tfoot>
	</table>
	</div>
</details>

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
			campaigned for the party vote, which would see it get more list seats.
		</li>
		<li>
			<strong>Boundaries stay as they were.</strong> With no Māori electorates, the general electorates would have to
			be redrawn, especially in areas with large Māori-roll populations. For example, East Cape’s electoral population
			would rise by about 60% without a boundary change. As Māori-roll voters are more concentrated in the North
			Island, it would gain about four electorates, while the South Island is fixed by law at 16 electorates.
		</li>
		<li>
			The narrowest electorates are sensitive to the assumptions above:
			{#each close as e, i (e.slug)}{i > 0 ? ', ' : ''}<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a>
				({e.flips ? 'would flip to' : 'would stay'} {name(e.winner_party)} by {votes(e.margin)})
			{/each}.
		</li>
	</ul>
</details>

<div class="controls">
	<div class="toggle" role="group" aria-label="Count">
		<button aria-pressed={view === 'counted'} onclick={() => (view = 'counted')}>As counted (preliminary)</button>
		<button aria-pressed={view === 'none'} onclick={() => (view = 'none')}>No Māori electorates</button>
	</div>
	<div class="param" id="threshold">
		<span class="param-row">
			<button
				type="button"
				class="switch"
				role="switch"
				aria-checked={waiver}
				aria-labelledby="waiver-label"
				onclick={() => (waiver = !waiver)}
			><span class="thumb"></span></button>
			<span id="waiver-label">Waive the 5% threshold for Māori parties</span>
		</span>
		<span class="small muted">
			The 1986 <a href="https://elections.nz/democracy-in-nz/what-is-new-zealands-system-of-government/report-of-the-royal-commission-on-the-electoral-system" target="_blank" rel="noopener">Royal Commission on the
			Electoral System</a> suggested this when it proposed abolishing the Māori electorates, but it was never adopted.<sup><a href="#fn-waiver">1</a></sup>
		</span>
	</div>
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
		<table class="seats">
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
					<td class="num">{nat.house[noKey]}</td>
					<td colspan="3"></td>
				</tr>
			</tfoot>
		</table>
	</div>
</div>

<h2>Electorates</h2>
<p>
	Colour is the {view === 'counted' ? 'preliminary' : 'new'} leader in each of the {nat.general_electorates}
	general electorates (switch with the toggle above). {flips.length === 1 ? 'The hatched electorate would flip' : 'Hatched electorates would flip'}
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

<h2 id="sensitivity">What if fewer TPM+ voters voted Labour?</h2>
<p>
	Assumption 2 is the one that matters most: those {votes(group)} votes are far more than any other
	party’s here. This shows the result if only some share of them went to Labour, and the rest
	<Term tip="Not counted for anyone: they’d have voted for another candidate we can’t identify, or not voted at all.">went nowhere</Term>.
</p>
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th class="num">Share voting Labour</th>
				<th class="num">Electorates that would flip</th>
				<th>Would newly flip</th>
				<th class="num">Labour would win</th>
				<th class="num">National would win</th>
			</tr>
		</thead>
		<tbody>
			{#each nat.sensitivity as s (s.from)}
				<tr>
					<td class="num">{share(s.from)} to {share(s.to)}</td>
					<td class="num">{s.flips.length}</td>
					<td>{s.new.join(', ')}</td>
					<td class="num">{s.labour}</td>
					<td class="num">{s.national}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<p class="muted small">
	Each range starts where another electorate’s break-even is: Labour needs <em>more than</em> the lower figure to
	win it. “Would win” counts are among the {nat.general_electorates} general electorates. The “Labour needs” column on the
	<a href={link('/electorates/')}>electorates page</a> gives each electorate’s break-even.
</p>

<aside class="footnotes" aria-label="Footnotes">
	<p class="small muted" id="fn-waiver">
		<sup>1</sup> The Commission assumed a modified Sainte-Laguë method for allocating seats, under which a party
		representing Māori interests would win a seat with about 1.25% of the party vote. Te Pāti Māori, with 0.57%, would
		have fallen short. We use New Zealand’s current method, which would give it one. (See paragraphs 3.74–3.75 of the
		1986 <a href="https://elections.nz/democracy-in-nz/what-is-new-zealands-system-of-government/report-of-the-royal-commission-on-the-electoral-system" target="_blank" rel="noopener">Royal Commission’s report</a>.) <a href="#fnref-waiver" aria-label="Back to the text">↩</a>
	</p>
</aside>

<style>
	.footnotes { margin-top: 2em; padding-top: 0.6em; border-top: 1px solid var(--border); max-width: var(--measure); }
	sup a { text-decoration: none; }
	.byline { color: var(--text-2); margin: 0 0 1em; }
	.credit { color: var(--text-3); }
	.lede { font-size: 1.05rem; }
	.lede + .lede { margin-top: 0.6em; }
	/* Party colour, pulled towards the text colour so light party colours stay readable. */
	.party-change { color: color-mix(in srgb, var(--c) 65%, var(--text)); white-space: nowrap; }
	.limits {
		border: 1px solid var(--warn-border); border-left-width: 4px; background: var(--warn-bg);
		border-radius: 4px; padding: 0.55em 0.9em; margin: 1em 0; max-width: var(--measure);
	}
	.limits summary { cursor: pointer; color: var(--warn-text); }
	.limits[open] summary { margin-bottom: 0.3em; }
	.limits ul { margin: 0.3em 0; }
	.limits ul { padding-left: 1.2em; }
	.limits li + li { margin-top: 0.25em; }
	.assumptions { max-width: var(--measure); padding-left: 1.4em; }
	.assumptions li { margin: 0.6em 0; }
	/* A muted box, so the collapsed table is visible without competing with the limitations box. */
	.votes {
		border: 1px solid var(--border); border-radius: 4px; max-width: var(--measure);
		background: color-mix(in srgb, var(--surface-2) 55%, var(--surface));
		padding: 0.5em 0.9em; margin: 1em 0;
	}
	.votes summary { cursor: pointer; color: var(--text-2); font-size: 0.9rem; }
	.votes[open] summary { margin-bottom: 0.3em; }
	.controls { display: flex; flex-wrap: wrap; gap: 0.6em 1.5em; align-items: flex-start; margin: 0.8em 0; }
	.controls .toggle { margin: 0; }
	.param { display: flex; flex-direction: column; gap: 0.15em; max-width: 36rem; font-size: 0.9rem; }
	.param .small { font-size: 0.78rem; }
	.param-row { display: flex; align-items: center; gap: 0.6em; color: var(--text-2); }
	.switch {
		position: relative; flex: none; width: 2.4em; height: 1.35em; padding: 0; border: 0; border-radius: 1em;
		background: var(--text-3); cursor: pointer; transition: background 0.15s;
	}
	.switch[aria-checked='true'] { background: var(--party-green); }
	.switch .thumb {
		position: absolute; top: 0.15em; left: 0.15em; width: 1.05em; height: 1.05em; border-radius: 50%;
		background: #fff; transition: transform 0.15s;
	}
	.switch[aria-checked='true'] .thumb { transform: translateX(1.05em); }
	.switch:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
	.toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin: 0.8em 0; }
	.toggle button {
		font: inherit; font-size: 0.9rem; padding: 0.35em 0.9em; border: 0; background: transparent;
		color: var(--text-2); cursor: pointer;
	}
	.toggle button[aria-pressed='true'] { background: var(--text); color: var(--surface); }
	/* The horseshoe is at most 304px wide (Parliament.svelte), so its column is capped; the table gets the rest. */
	.grid { display: grid; grid-template-columns: minmax(0, 482px) minmax(0, 1fr); gap: 1.5em; align-items: start; }
	@media (max-width: 760px) { .grid { grid-template-columns: minmax(0, 1fr); } }
</style>
