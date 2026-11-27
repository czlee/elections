<script>
	import { resolve } from '$app/paths';
	import { ELECTIONS, PAST } from '#lib/elections.js';
	const prelim = ELECTIONS.filter((e) => e.prelim);
	const earlier = PAST.filter((e) => e.year !== '2026');
</script>

<h1>2026 New Zealand election margins</h1>
<p class="callout">
	How many party votes it would take for each party to gain or lose a seat, and the closest electorates, from the
	<a href={resolve(/** @type {any} */ ('/2026/'))}>final 2026 results</a>.
</p>

<h2>Earlier elections</h2>
<ul>
	{#each [...earlier].reverse() as e (e.id)}
		<li><a href={resolve(/** @type {any} */ (`/${e.id}/`))}>{e.year} election</a></li>
	{/each}
	{#each prelim as e (e.id)}
		<li>
			<a href={resolve(/** @type {any} */ (`/${e.id}/`))}>{e.year} election, preliminary count</a>
			<span class="muted">(superseded by the final results)</span>
		</li>
	{/each}
</ul>
