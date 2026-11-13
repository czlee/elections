<script>
	/** @type {{items: {label: string, url?: string, xml?: string}[]}} */
	let { items } = $props();
</script>

<p class="sources">
	Sources:
	{#each items as s, i (i)}
		{#if i > 0}; {/if}
		{#if s.url}<a href={s.url}>{s.label}</a>{:else}{s.label}{/if}{#if s.xml}{' '}(<a href={s.xml}>XML</a>){/if}
	{/each}
</p>
