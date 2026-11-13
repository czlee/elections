<script>
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import { link } from '#lib/link.js';
	import { page } from '$app/state';

	/** @type {{children: import('svelte').Snippet}} */
	let { children } = $props();

	const nav = [
		{ href: '/', route: '/', label: 'Projection' },
		{ href: '/national/', route: '/national', label: 'National' },
		{ href: '/method/', route: '/method', label: 'Method' }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<header>
	<nav>
		<a class="brand" href={link('/')}>2026 special votes projection</a>
		{#each nav as item (item.href)}
			<a href={link(item.href)} aria-current={page.route.id === item.route ? 'page' : undefined}
				>{item.label}</a
			>
		{/each}
	</nav>
</header>

<main>
	{@render children()}
</main>

<footer>
	<p>
		Projection by Chuan-Zheng Lee. Not an official result. Based on 2023's special votes; see
		<a href={link('/method/')}>method</a> for assumptions and limitations.
	</p>
	<p>
		Data: <a href="https://www.electionresults.govt.nz/">Electoral Commission</a> (2023 and 2026
		results), <a href="https://web.archive.org/">Internet Archive</a> (2023 preliminary count),
		<a href="https://datafinder.stats.govt.nz/">Stats NZ</a> (2023 Census electoral population and
		2025 electorate boundaries, CC BY 4.0). Code:
		<a href="https://github.com/czlee/elections">czlee/elections</a>.
	</p>
</footer>

<style>
	header { border-bottom: 1px solid var(--border); }
	nav, main, footer { max-width: 1040px; margin: 0 auto; padding: 0 16px; }
	nav { display: flex; flex-wrap: wrap; gap: 0.3em 1.2em; align-items: baseline; padding-block: 0.7em; }
	nav a { color: var(--text-2); text-decoration: none; }
	nav a[aria-current='page'] { color: var(--text); font-weight: 600; }
	nav .brand { color: var(--text); font-weight: 700; margin-right: auto; }
	main { padding-bottom: 3em; }
	footer { border-top: 1px solid var(--border); color: var(--text-3); font-size: 0.8rem; padding-block: 1em 2em; }
	footer a { color: var(--text-2); }
</style>
