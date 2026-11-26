<script>
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, pct, points, signed, candidateName } from '#lib/format.js';

	let { data } = $props();
	const e = $derived(data.electorate);
	const names = $derived(Object.fromEntries(data.parties.map((/** @type {any} */ p) => [p.id, p.short])));
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'Independent');
	const who = (/** @type {any} */ c) => candidateName(c.candidate);
	const W = $derived(e.candidates[0]);
	const S = $derived(e.candidates[1]);
	const prelimTotal = $derived(e.candidates.reduce((/** @type {number} */ a, /** @type {any} */ c) => a + c.prelim, 0));
	const newTotal = $derived(e.candidates.reduce((/** @type {number} */ a, /** @type {any} */ c) => a + c.total, 0));
	const prelimWinner = $derived(e.candidates.find((/** @type {any} */ c) => c.party === e.winner_prelim && c.prelim === Math.max(...e.candidates.map((/** @type {any} */ x) => x.prelim))) ?? e.candidates[0]);
	const labour = $derived(e.candidates.find((/** @type {any} */ c) => c.party === 'labour'));
	const b = $derived(e.labour_breakeven);
	const rival = $derived(labour ? e.candidates.filter((/** @type {any} */ c) => c !== labour).reduce((/** @type {any} */ a, /** @type {any} */ c) => (c.total > a.total ? c : a)) : null);
	const dropped = $derived(e.added_rows.filter((/** @type {any} */ r) => r.to === null).reduce((/** @type {number} */ a, /** @type {any} */ r) => a + r.votes, 0));
	const HOW = /** @type {Record<string, string>} */ ({
		'to Labour': 'Counted for Labour',
		'same party': 'Same party’s candidate',
		'to bloc major party (no candidate there)': 'Counted for Labour (no candidate for their party)',
		'discarded: independent': 'Dropped (independent)',
		'discarded: no candidate there and no bloc': 'Dropped (no candidate, no bloc)'
	});
	// Added votes grouped by Māori electorate, then the rows in order.
	const origins = $derived.by(() => {
		/** @type {Map<string, number>} */
		const m = new Map();
		for (const r of e.added_rows) m.set(r.from, (m.get(r.from) ?? 0) + r.votes);
		return [...m.entries()].toSorted((a, b2) => b2[1] - a[1]);
	});
</script>

<p class="small"><a href={link('/electorates/')}>← All electorates</a></p>
<h1>{e.name} <span class="muted small">general electorate</span></h1>

<p class="verdict">
	<span class="swatch" style:background={colour(W.party)}></span>
	<strong>{who(W)}</strong> ({party(W.party)}) {e.flips ? 'would overtake' : 'would hold on'},
	winning by <strong>{votes(e.margin_new)}</strong> votes ({points(e.margin_new_pct)}) over
	{who(S)} ({party(S.party)}).
	{#if e.flips}<span class="badge flip">would flip from {party(e.winner_prelim)}</span>{/if}
</p>

<div class="callout">
	<p>
		<strong>Why.</strong>
		{votes(e.added_total)} Māori-roll votes from {origins.length} Māori
		electorate{origins.length === 1 ? '' : 's'} were cast at voting places in {e.name}
		({#each origins as [from, n], i (from)}{i > 0 ? ', ' : ''}{from} {votes(n)}{/each}).
		{#if e.flips}
			In the preliminary count {who(prelimWinner)} led by {votes(e.margin_prelim)}; with the Māori-roll votes
			{who(W)} would win by {votes(e.margin_new)}.
		{:else}
			In the preliminary count {who(W)} led by {votes(e.margin_prelim)}; now they lead by {votes(e.margin_new)}.
		{/if}
	</p>
	{#if labour}
		<p>
			{#if b === null}
				No TPM+ voters cast votes at voting places here.
			{:else if b <= 0}
				Labour’s candidate would win here even if <strong>none</strong> of the {votes(e.tpm_votes)} TPM+
				voters here vote for them (the other Māori-roll votes are enough).
			{:else if b <= 1}
				Labour’s candidate would win if more than <strong>{pct(b, 0)}</strong> of the {votes(e.tpm_votes)} TPM+
				voters here vote for them (the rest counted for no one, everything else as above).
				{#if e.winner_new === 'labour'}Below that, {who(rival)} would win.{:else}Above that, they would overtake {who(rival)}.{/if}
			{:else}
				Labour’s candidate wouldn’t win here even if <strong>all</strong> {votes(e.tpm_votes)} TPM+
				voters here vote for them: they’d still be {votes(Math.round((b - 1) * e.tpm_votes))} votes behind {who(rival)}.
			{/if}
			<span class="muted small">(TPM+ is Te Pāti Māori, Te Tai Tokerau Party and Tākuta Ferris voters.)</span>
		</p>
	{/if}
</div>

<h2>Electorate votes</h2>
<div class="table-wrap">
	<table class="wide-first">
		<thead>
			<tr>
				<th>Candidate</th>
				<th class="num">Preliminary</th>
				<th class="num">+ Māori-roll</th>
				<th class="num">Total</th>
				<th class="num">Share</th>
			</tr>
		</thead>
		<tbody>
			{#each e.candidates as c (c.candidate)}
				<tr>
					<td><span class="swatch" style:background={colour(c.party)}></span>{who(c)}
						<span class="muted small">{party(c.party)}</span></td>
					<td class="num">{votes(c.prelim)}</td>
					<td class="num">{c.added ? signed(c.added) : ''}</td>
					<td class="num"><strong>{votes(c.total)}</strong></td>
					<td class="num">{pct(c.total / newTotal)}</td>
				</tr>
			{/each}
		</tbody>
		<tfoot>
			<tr>
				<td>Total counted</td>
				<td class="num">{votes(prelimTotal)}</td>
				<td class="num">{signed(newTotal - prelimTotal)}</td>
				<td class="num">{votes(newTotal)}</td>
				<td></td>
			</tr>
		</tfoot>
	</table>
</div>
{#if dropped > 0}
	<p class="muted small">{votes(dropped)} Māori-roll votes here were dropped and aren’t in the total.</p>
{/if}

<h2>Where the Māori-roll votes came from</h2>
<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th>Māori electorate</th>
				<th>Voted for</th>
				<th>Counted as</th>
				<th class="num">Votes</th>
			</tr>
		</thead>
		<tbody>
			{#each e.added_rows as r, i (i)}
				<tr>
					<td>{r.from}</td>
					<td><span class="swatch" style:background={colour(r.party)}></span>{party(r.party)}</td>
					<td>{HOW[r.how] ?? r.how}</td>
					<td class="num">{votes(r.votes)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<p class="sources">
	2026 source: <a href={e.links.prelim_2026.url}>preliminary count</a>
	(<a href={e.links.prelim_2026.xml}>XML</a>), including the voting place results.
</p>

<style>
	.verdict { font-size: 1.1rem; }
	.flip { color: var(--text); margin-left: 0.4em; }
</style>
