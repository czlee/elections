<script>
	import { resolve } from '$app/paths';
	import { ELECTIONS, PAST } from '#lib/elections.js';
	const prelim = ELECTIONS.filter((e) => e.prelim);
</script>

<h1>2026 New Zealand election margins</h1>
<p class="callout">
	The final 2026 results will be here once they’re released: how many party votes it would take for each party to
	gain or lose a seat, and the closest electorates.
</p>

<h2>Earlier elections</h2>
<ul>
	{#each [...PAST].reverse() as e (e.id)}
		<li><a href={resolve(/** @type {any} */ (`/${e.id}/`))}>{e.year} election</a></li>
	{/each}
	{#each prelim as e (e.id)}
		<li>
			<a href={resolve(/** @type {any} */ (`/${e.id}/`))}>{e.year} election, preliminary count</a>
			<span class="muted">(what the page will look like)</span>
		</li>
	{/each}
</ul>
