<script>
	import Parliament from '#lib/components/Parliament.svelte';
	import { colour } from '#lib/parties.js';
	import { partyKey, seatsOf } from '#lib/elections.js';
	import { votes as fmtVotes, delta, pct } from '#lib/format.js';

	/** @type {{data: any}} */
	let { data } = $props();

	const nearParties = $derived(data.parties.filter((/** @type {any} */ p) => p.threshold?.near));
	const modes = $derived([
		{ id: 'gain', label: 'Gain a seat' },
		{ id: 'lose', label: 'Lose a seat' },
		...(nearParties.length ? [{ id: 'threshold', label: '5% threshold' }] : [])
	]);

	let mode = $state('gain');
	/** @type {string | null} Party key of the row under the pointer or focus. */
	let hovered = $state(null);
	/** @type {string | null} Party key of the row last clicked or tapped, which stays until another is chosen. */
	let pinned = $state(null);

	const rows = $derived.by(() => {
		if (mode === 'threshold') {
			return nearParties
				.map((/** @type {any} */ p) => ({ p, s: p.threshold }))
				.sort((/** @type {any} */ a, /** @type {any} */ b) => a.s.votes - b.s.votes);
		}
		// Smallest number of votes first; parties that can't change go last.
		return data.parties
			.filter((/** @type {any} */ p) => p.qualified)
			.map((/** @type {any} */ p) => ({ p, s: p[mode] }))
			.sort((/** @type {any} */ a, /** @type {any} */ b) => (a.s?.votes ?? Infinity) - (b.s?.votes ?? Infinity));
	});

	const key = (/** @type {any} */ p) => p.party;
	const activeKey = $derived(hovered ?? pinned);
	const active = $derived(rows.find((r) => key(r.p) === activeKey && r.s) ?? null);

	const names = $derived({
		independent: 'Independent',
		...Object.fromEntries(
			[...data.parties, ...data.house.parties].map((/** @type {any} */ p) => [partyKey(p), p.name])
		)
	});
	const actualSeats = $derived(seatsOf(data.house));
	const shown = $derived(active ? active.s.house : data.house);
	const houseSize = $derived(shown.house);

	/** Other parties' entitlement changes in a scenario, "*" for those that only move overhang. */
	function changes(/** @type {any} */ p, /** @type {any} */ s) {
		const before = new Map(data.house.parties.map((/** @type {any} */ h) => [h.party, h]));
		const out = [];
		for (const h of s.house.parties) {
			if (h.party === p.party) continue;
			const b = /** @type {any} */ (before.get(h.party));
			const d = h.entitlement - (b?.entitlement ?? 0);
			if (d) out.push({ id: partyKey(h), name: h.name, d, overhang: h.seats === (b?.seats ?? 0) });
		}
		for (const b of data.house.parties) {
			if (b.party === p.party || s.house.parties.some((/** @type {any} */ h) => h.party === b.party)) continue;
			if (b.entitlement) out.push({ id: partyKey(b), name: b.name, d: -b.entitlement, overhang: false });
		}
		return out;
	}

	const verb = (/** @type {any} */ s) => (s.direction === 'lose' || s.direction === 'drop below' ? 'loses' : 'gains');
	const anyOverhangOnly = $derived(rows.some((r) => r.s?.overhang_only || (r.s && changes(r.p, r.s).some((c) => c.overhang))));
</script>

<div class="layout">
	<div class="left">
		<div class="seg" role="group" aria-label="Show">
			{#each modes as m (m.id)}
				<button type="button" aria-pressed={mode === m.id} onclick={() => { mode = m.id; pinned = null; hovered = null; }}>{m.label}</button>
			{/each}
		</div>
		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th>Party</th>
						<th class="num">Party votes</th>
						{#if mode === 'threshold'}
							<th class="num">Share</th>
						{:else}
							<th class="num">Entitle&shy;ment</th>
						{/if}
						<th class="num votes">{mode === 'gain' ? 'Votes to gain' : mode === 'lose' ? 'Votes to lose' : 'Votes to cross'}</th>
						<th>{mode === 'gain' ? 'Gain from' : mode === 'lose' ? 'Lose from' : 'Seat changes'}</th>
					</tr>
				</thead>
				<tbody onmouseleave={() => (hovered = null)} role="presentation">
					{#each rows as { p, s } (key(p))}
						<tr
							class:active={active && key(active.p) === key(p)}
							class:inert={!s}
							tabindex={s ? 0 : undefined}
							onmouseenter={() => (hovered = s ? key(p) : null)}
							onfocus={() => (hovered = s ? key(p) : null)}
							onblur={() => (hovered = null)}
							onclick={() => { if (s) pinned = pinned === key(p) ? null : key(p); }}
							onkeydown={(e) => { if (s && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); pinned = pinned === key(p) ? null : key(p); } }}
						>
							<td><span class="swatch" style:background={colour(p.id)}></span>{p.name}</td>
							<td class="num">{fmtVotes(p.votes)}</td>
							{#if mode === 'threshold'}
								<td class="num">{pct(p.share)}</td>
							{:else}
								<td class="num">{p.entitlement}</td>
							{/if}
							{#if s}
								<td class="num votes">{s.overhang_only ? '*' : ''}{mode === 'threshold' ? (s.direction === 'reach' ? '+' : '−') : ''}{fmtVotes(s.votes)}</td>
								<td class="chgs">
									{#each changes(p, s) as c (c.id)}
										<span class="chg"><span class="swatch" style:background={colour(c.id)}></span>{c.name} {delta(c.d)}{c.overhang ? '*' : ''}</span>
									{/each}
								</td>
							{:else}
								<td class="num muted" title="No number of party votes does this">–</td>
								<td></td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<p class="muted small">
			{#if mode === 'threshold'}
				Parties with no electorate seat, within {100 * data.near} percentage points of the {100 * data.threshold}% threshold: the party
				votes they’d need to gain or lose to qualify (or stop qualifying), and the change in everyone’s entitlement when they do.
			{:else}
				Extra (or fewer) party votes for that party alone, everyone else unchanged, at which its seat count changes.
				{#if rows.some((r) => !r.s)}– means no number of party votes does it (a party with no seat can’t lose one).{/if}
			{/if}
		</p>
		{#if anyOverhangOnly}
			<p class="muted small">
				* Only changes the overhang: the party won more electorates than its party vote entitlement, so its seats don’t change,
				but it may change the size of the House.
			</p>
		{/if}
	</div>

	<aside class="right">
		<div class="chart-title" aria-live="polite">
			{#if active}
				<h3>If {active.p.name} {verb(active.s)} {fmtVotes(active.s.votes)} votes</h3>
				{#if mode === 'threshold'}
					<p class="muted small">{active.s.direction === 'reach' ? `reaching the ${100 * data.threshold}% threshold` : `dropping below the ${100 * data.threshold}% threshold`}</p>
				{/if}
			{:else}
				<h3>Actual result</h3>
			{/if}
		</div>
		<Parliament
			seats={seatsOf(shown)}
			{names}
			compare={active ? actualSeats : {}}
			highlightLabel="seat gained"
			majority={Math.floor(houseSize / 2) + 1}
			overhang={Math.max(0, houseSize - data.total_seats)}
		/>
	</aside>
</div>

<style>
	.layout { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 0 2em; align-items: start; }
	.right { position: sticky; top: 1em; order: 2; }
	.chart-title { min-height: 3.2em; }
	.chart-title h3 { margin: 0.2em 0 0; text-align: center; }
	.chart-title p { margin: 0; text-align: center; }
	@media (max-width: 800px) {
		.layout { grid-template-columns: minmax(0, 1fr); }
		.right { position: static; order: -1; }
	}

	.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 999px; padding: 2px; background: var(--surface-2); margin: 0.4em 0; }
	.seg button {
		font: inherit; font-size: 0.9rem; border: 0; background: transparent; color: var(--text-2);
		padding: 0.25em 1em; border-radius: 999px; cursor: pointer;
	}
	.seg button[aria-pressed='true'] { background: var(--accent); color: var(--surface); font-weight: 600; }
	.seg button:focus-visible, tbody tr:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

	td.votes, th.votes { font-weight: 600; }
	tbody tr { cursor: pointer; }
	tbody tr.inert { cursor: default; }
	tbody tr.inert:hover { background: none; }
	tbody tr.active { background: var(--surface-2); box-shadow: inset 3px 0 0 var(--accent); }
	.chg { white-space: nowrap; margin-right: 0.9em; display: inline-block; }
</style>
