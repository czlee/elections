<script>
	import { colour } from '#lib/parties.js';
	import { candidateName, votes as fmtVotes } from '#lib/format.js';
	import { electorateUrl } from '#lib/elections.js';

	/** @type {{data: any, official: string, initial?: number}} */
	let { data, official, initial = 10 } = $props();
	let all = $state(false);
	const rows = $derived(all ? data.electorates : data.electorates.slice(0, initial));
</script>

<div class="table-wrap">
	<table>
		<thead>
			<tr>
				<th>Electorate</th><th class="num">Margin</th><th class="num">%</th><th>Winner</th><th>Runner-up</th><th aria-label="Official results"></th>
			</tr>
		</thead>
		<tbody>
			{#each rows as r (r.id)}
				<tr>
					<td>{r.electorate}</td>
					<td class="num">{fmtVotes(r.margin)}</td>
					<td class="num">{r.margin_pct.toFixed(2)}</td>
					<td>
						<span class="swatch" style:background={colour(r.winner_party_id)}></span>{candidateName(r.winner)}
						<span class="muted small">· {r.winner_party_name} · {fmtVotes(r.winner_votes)}</span>
					</td>
					<td>
						<span class="swatch" style:background={colour(r.runner_up_party_id)}></span>{candidateName(r.runner_up)}
						<span class="muted small">· {r.runner_up_party_name} · {fmtVotes(r.runner_up_votes)}</span>
					</td>
					<td class="ext">
						<a href={electorateUrl(official, r.id)} target="electionresults" rel="noopener"
							aria-label="{r.electorate} on the Electoral Commission’s results site (opens in a new tab)"
							title="Electoral Commission results for {r.electorate}">official ↗</a>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
{#if data.electorates.length > initial}
	<p><button type="button" class="more" onclick={() => (all = !all)}>{all ? `Show the closest ${initial}` : `Show all ${data.electorates.length}`}</button></p>
{/if}

<style>
	.ext { white-space: nowrap; font-size: 0.85rem; }
	.more {
		font: inherit; font-size: 0.9rem; color: var(--text); background: var(--surface-2);
		border: 1px solid var(--border); border-radius: 6px; padding: 0.25em 0.9em; cursor: pointer;
	}
</style>
