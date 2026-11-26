<script>
	import { colour } from '#lib/parties.js';
	import { votes as fmtVotes } from '#lib/format.js';
	import Term from '#lib/components/Term.svelte';
	import { workings } from '#lib/workings.js';

	/** @type {{data: any}} */
	let { data } = $props();
	const parties = $derived(data.parties.filter((/** @type {any} */ p) => p.qualified));
	const lastAllocated = $derived(data.ladder.findLast((/** @type {any} */ r) => r.allocated)?.rank);
	const first = $derived(data.to_allocate);

	/** A quotient is a party's nth seat; the divisor is 2n − 1. */
	const seatOf = (/** @type {number} */ divisor) => (divisor + 1) / 2;
	const keyOf = (/** @type {string} */ party, /** @type {number} */ seat) => `${party}|${seat}`;
	/** Whether the ranking's row is the one that last got in, or first missed out. */
	const isPick = (/** @type {any} */ r) => r.rank === first || r.rank === first + 1;
	/** Whether a party's last-in or next-out quotient is the last one in or first one out of the whole House. */
	const pickedCell = (/** @type {any} */ p, /** @type {'last' | 'next'} */ which) => {
		const q = p[which];
		if (!q) return false;
		const r = data.ladder.find((/** @type {any} */ r) => r.rank === first + (which === 'last' ? 0 : 1));
		return !!r && r.party === p.party && r.seat === seatOf(q.divisor);
	};

	/** Every party's last-in and next-out quotients: the other rows of the ranking are faded. */
	const relevant = $derived(
		new Set(
			parties.flatMap((/** @type {any} */ p) =>
				['last', 'next'].filter((w) => p[w]).map((w) => keyOf(p.party, seatOf(p[w].divisor)))
			)
		)
	);

	/** Key of the quotient under the pointer, in either table, so the other table can show it too. */
	let hovered = $state('');

	/**
	 * The "Last in" or "Next out" cell under the pointer (or last clicked or tapped), for the working underneath: the
	 * last seat in is what a party loses, and the next seat out is what it gains.
	 * @typedef {{ party: string, which: 'last' | 'next' }} Pick
	 */
	/** @type {Pick | null} */
	let hoveredCell = $state(/** @type {Pick | null} */ (null));
	/** @type {Pick | null} */
	let pinnedCell = $state(/** @type {Pick | null} */ (null));
	const shownCell = $derived(hoveredCell ?? pinnedCell);
	const shownParty = $derived(shownCell && parties.find((/** @type {any} */ p) => p.party === shownCell.party));
	const shownWorking = $derived(shownParty && shownCell ? workings(data, shownParty, shownCell.which === 'last' ? 'lose' : 'gain') : null);
	/** The left-table cell a ranking row is a party's last-in or next-out quotient for, if it is one. */
	const cellOf = (/** @type {any} */ r) => {
		const p = parties.find((/** @type {any} */ p) => p.party === r.party);
		/** @type {Pick | null} */
		let c = null;
		for (const which of /** @type {const} */ (['last', 'next'])) if (p?.[which] && seatOf(p[which].divisor) === r.seat) c = { party: r.party, which };
		return c;
	};
	const same = (/** @type {Pick | null} */ a, /** @type {Pick} */ b) => a?.party === b.party && a?.which === b.which;
	const toggle = (/** @type {Pick} */ c) => (pinnedCell = same(pinnedCell, c) ? null : c);

	const ordinal = (/** @type {number} */ n) => {
		const t = n % 100;
		const suffix = t >= 11 && t <= 13 ? 'th' : (['th', 'st', 'nd', 'rd'][n % 10] ?? 'th');
		return n + suffix;
	};
	const dec = new Intl.NumberFormat('en-NZ', { maximumFractionDigits: 1 });
</script>

{#snippet div()}<Term tip="Divisor">Div.</Term>{/snippet}

<p class="muted">
	A party’s nth seat has quotient votes ÷ (2n − 1). The {data.to_allocate} highest quotients get the Sainte-Laguë seats
	({data.total_seats}, less electorates won by independents or parties without a list). The {data.to_allocate}th is the last seat in and
	the {data.to_allocate + 1}th the first one out. Each party’s last seat in and next seat out are on the left; the ranking around the
	cutoff is on the right.
</p>
<div class="pair">
	<div class="left">
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party</th><th class="num">Party votes</th><th class="num">Seats</th>
					<th class="num">Last in</th><th class="num muted">{@render div()}</th><th class="num">Next out</th><th class="num muted">{@render div()}</th>
				</tr>
			</thead>
			<tbody onmouseleave={() => (hoveredCell = null)} role="presentation">
				{#each parties as p (p.party)}
					<tr>
						<td><span class="swatch" style:background={colour(p.id)}></span>{p.name}</td>
						<td class="num">{fmtVotes(p.votes)}</td>
						<td class="num">{p.entitlement}</td>
						{#each ['last', 'next'] as which (which)}
							{@const q = p[which]}
							{#if q}
								{@const k = keyOf(p.party, seatOf(q.divisor))}
								{@const cell = { party: p.party, which: /** @type {'last' | 'next'} */ (which) }}
								{@const on = same(shownCell, cell)}
								{@const enter = () => { hovered = k; hoveredCell = cell; }}
								{@const leave = () => { hovered = ''; }}
								<td class="num q" class:pick={pickedCell(p, /** @type {any} */ (which))} class:linked-l={hovered === k} class:working-l={on}
									tabindex="0" onmouseenter={enter} onmouseleave={leave} onfocus={enter} onblur={() => { leave(); hoveredCell = null; }}
									onclick={() => toggle(cell)}
									onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(cell); } }}>{fmtVotes(q.quotient)}</td>
								<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
								<td class="num q muted" class:linked-r={hovered === k} class:working-r={on}
									onmouseenter={enter} onmouseleave={leave} onclick={() => toggle(cell)}>{q.divisor}</td>
							{:else}
								<td class="num">–</td><td class="num">–</td>
							{/if}
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	{#snippet working(/** @type {any} */ w, /** @type {any} */ p)}
		{@const gain = w.direction === 'gain'}
		{@const barRank = data.ladder.find((/** @type {any} */ r) => r.party === w.bar.party && r.seat === w.bar.seat)?.rank}
		{@const expected = gain ? first : first + 1}
		<h4>Votes to {gain ? 'gain' : 'lose'} for {p.name} to {gain ? 'gain' : 'lose'} a seat: {fmtVotes(w.change)}</h4>
		<ul>
			<li>{p.name}’s {ordinal(w.seat)} quotient {gain ? 'would be' : 'is'} {fmtVotes(p.votes)} ÷ {w.divisor} = {dec.format(p.votes / w.divisor)}.</li>
			<li>
				{#if barRank === expected}The current {ordinal(barRank)} quotient{:else}The next quotient that isn’t {p.name}’s{/if}
				is {w.bar.name}’s, on {dec.format(w.bar.votes / w.bar.divisor)}.
			</li>
			<li>
				For {p.name} to {gain ? `gain a seat from ${w.bar.name}, its ${ordinal(w.seat)} quotient would have to rise above`
					: `lose a seat to ${w.bar.name}, its ${ordinal(w.seat)} quotient would have to sink below`} that.
			</li>
			<li>
				This happens when {gain ? 'its party vote rises above' : 'its party vote falls below'}
				{dec.format(w.bar.votes / w.bar.divisor)} × {w.divisor} = {dec.format(w.product)}, i.e. {gain ? `to ${fmtVotes(w.target)} or more` : `to ${fmtVotes(w.target)} or fewer`}.
			</li>
			<li>{gain ? `${fmtVotes(w.target)} − ${fmtVotes(p.votes)}` : `${fmtVotes(p.votes)} − ${fmtVotes(w.target)}`} = <strong>{fmtVotes(w.change)}</strong></li>
		</ul>
	{/snippet}
	<div class="working" aria-live="polite">
		{#if shownParty && shownCell}
			{#if shownWorking}
				{@render working(shownWorking, shownParty)}
				{#if shownParty.overhang > 0 || shownParty[shownWorking.direction]?.overhang_only}
					<p class="muted small">This calculation is for seats in the party vote allocation, before taking into account any overhang.</p>
				{/if}
			{:else}
				<h4>Votes to lose</h4>
				<p class="muted">{shownParty.name} has no seat to lose from its party vote.</p>
			{/if}
		{:else}
			<p class="muted small">Hover over a “Last in” or “Next out” quotient to see the working for “votes to lose” or “votes to gain”.</p>
		{/if}
	</div>
	</div>
	<div class="table-wrap">
		<table>
			<thead>
				<tr><th class="num">Rank</th><th>Party</th><th class="num">Its seat</th><th class="num muted">{@render div()}</th><th class="num">Quotient</th></tr>
			</thead>
			<tbody onmouseleave={() => { hovered = ''; hoveredCell = null; }} role="presentation">
				{#each data.ladder as r (r.rank)}
					{@const k = keyOf(r.party, r.seat)}
					{@const cell = cellOf(r)}
					<tr class:faded={!relevant.has(k)} class:pick={isPick(r)} class:linked={hovered === k} class:cut={r.rank === lastAllocated}
						class:clickable={!!cell} onmouseenter={() => { hovered = k; hoveredCell = cell; }} onclick={() => cell && toggle(cell)}>
						<td class="num">{r.rank}</td>
						<td><span class="swatch" style:background={colour(r.id)}></span>{r.name}</td>
						<td class="num">{r.seat}</td>
						<td class="num muted">{2 * r.seat - 1}</td>
						<td class="num">{fmtVotes(r.quotient)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<style>
	.pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 0 2em; align-items: start; }
	/* The last quotient in and the first one out. */
	.pick { background: color-mix(in srgb, var(--highlight) 32%, transparent); font-weight: 600; }
	tr.faded td { color: var(--text-3); opacity: 0.6; }
	tr.faded.linked td { opacity: 1; }
	/* The quotient under the pointer, or its counterpart in the other table. */
	tr.linked { background: var(--surface-2); box-shadow: inset 0 0 0 2px var(--accent); }
	/* In the left table the quotient and its divisor are outlined together, with no line between them. */
	.linked-l { box-shadow: inset 2px 0 0 var(--accent), inset 0 2px 0 var(--accent), inset 0 -2px 0 var(--accent); }
	.linked-r { box-shadow: inset -2px 0 0 var(--accent), inset 0 2px 0 var(--accent), inset 0 -2px 0 var(--accent); }
	tr.cut td { border-bottom: 2px solid var(--text-2); }
	td.q, tr.clickable { cursor: pointer; }
	td.q:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
	/* The cell whose working is shown underneath. */
	.working-l { box-shadow: inset 2px 0 0 var(--accent), inset 0 2px 0 var(--accent), inset 0 -2px 0 var(--accent); }
	.working-r { box-shadow: inset -2px 0 0 var(--accent), inset 0 2px 0 var(--accent), inset 0 -2px 0 var(--accent); }
	/* Under the left table, which is shorter than the ranking beside it. */
	.working { margin-top: 1em; padding: 0.2em 1em 0.6em; background: var(--surface-2); border-radius: 6px; font-size: 0.9rem; min-height: 4em; }
	.working h4 { margin: 0.6em 0 0.2em; }
	.working ul { margin: 0; padding-left: 1.2em; }
	.working li { margin: 0.35em 0; }</style>
