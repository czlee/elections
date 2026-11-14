<script>
	// DM Sans, self-hosted via Fontsource (SIL Open Font License); latin and latin-ext subsets.
	import '@fontsource/dm-sans/400.css';
	import '@fontsource/dm-sans/500.css';
	import '@fontsource/dm-sans/600.css';
	import '@fontsource/dm-sans/700.css';
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import appleTouchIcon from '#lib/assets/apple-touch-icon.png';
	import { DRAFT } from '#lib/config.js';
	import { link } from '#lib/link.js';
	import { page } from '$app/state';

	/** @type {{children: import('svelte').Snippet}} */
	let { children } = $props();

	const nav = [
		{ href: '/', route: '/', label: 'Projection' },
		{ href: '/party-vote/', route: '/party-vote', label: 'Party vote' },
		{ href: '/electorates/', route: '/electorates', label: 'Electorates' }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} type="image/svg+xml" />
	<link rel="apple-touch-icon" href={appleTouchIcon} />
	{#if DRAFT}<meta name="robots" content="noindex, nofollow" />{/if}
</svelte:head>

{#if DRAFT}
	<div class="draft-banner" role="note">
		<strong>DRAFT</strong> · Work in progress: numbers, wording and layout may change. Not an official result.
	</div>
{/if}

<header>
	<nav>
		<a class="brand" href={link('/')}>2026 special votes projection{#if DRAFT}<span class="draft-tag">DRAFT</span>{/if}</a>
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
		Projection by Chuan-Zheng Lee. Not an official result. Based on 2023's special votes; see the
		<a href={link('/#limitations')}>limitations</a>.
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
	.draft-banner {
		background: #fab219; color: #1a1a19; font-size: 0.85rem; text-align: center; padding: 0.35em 16px;
	}
	.draft-tag {
		font-size: 0.65rem; font-weight: 700; letter-spacing: 0.05em; vertical-align: 0.2em; margin-left: 0.5em;
		padding: 0.1em 0.4em; border-radius: 3px; background: #fab219; color: #1a1a19;
	}
	nav, main, footer { max-width: 1040px; margin: 0 auto; padding: 0 16px; }
	nav { display: flex; flex-wrap: wrap; gap: 0.3em 1.2em; align-items: baseline; padding-block: 0.7em; }
	nav a { color: var(--text-2); text-decoration: none; }
	nav a[aria-current='page'] { color: var(--text); font-weight: 600; }
	nav .brand { color: var(--text); font-weight: 700; margin-right: auto; }
	main { padding-bottom: 3em; }
	footer { border-top: 1px solid var(--border); color: var(--text-3); font-size: 0.8rem; padding-block: 1em 2em; }
	footer a { color: var(--text-2); }
</style>
