<script>
	// Figtree, self-hosted via Fontsource (SIL Open Font License); latin and latin-ext subsets.
	import '@fontsource/figtree/400.css';
	import '@fontsource/figtree/500.css';
	import '@fontsource/figtree/600.css';
	import '@fontsource/figtree/700.css';
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import appleTouchIcon from '#lib/assets/apple-touch-icon.png';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ELECTIONS, DEFAULT_ID, electionPath } from '#lib/elections.js';

	/** @type {{children: import('svelte').Snippet, data: any}} */
	let { children, data } = $props();
	const href = (/** @type {string} */ path) => resolve(/** @type {any} */ (path));
	const isCurrent = (/** @type {string} */ id) => (page.params.election ?? DEFAULT_ID) === id && page.route.id !== null;

	/** The menu entries: one per year, with a dropdown when that year has a preliminary count as well as a final one. */
	const years = $derived(
		ELECTIONS.filter((e) => !e.prelim || !ELECTIONS.some((x) => x.year === e.year && !x.prelim)).map((e) => ({
			main: e,
			sub: e.prelim ? [] : ELECTIONS.filter((x) => x.year === e.year && x.prelim)
		}))
	);
</script>

<svelte:head>
	<link rel="icon" href={favicon} type="image/svg+xml" />
	<link rel="apple-touch-icon" href={appleTouchIcon} />
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href={data.meta.url} />
	<meta property="og:type" content="website" />
	<meta property="og:locale" content="en_NZ" />
	<meta property="og:site_name" content={data.meta.siteName} />
	<meta property="og:title" content={data.meta.title} />
	<meta property="og:description" content={data.meta.description} />
	<meta property="og:url" content={data.meta.url} />
	<meta property="og:image" content={data.meta.image} />
	<meta property="og:image:type" content="image/png" />
	<meta property="og:image:width" content={String(data.meta.imageWidth)} />
	<meta property="og:image:height" content={String(data.meta.imageHeight)} />
	<meta property="og:image:alt" content={data.meta.description} />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<header>
	<nav>
		<a class="brand" href={href('/')}>New Zealand election margins</a>
		<span class="elections" role="group" aria-label="Election">
			{#each years as { main, sub } (main.id)}
				{#if sub.length}
					<span class="dropdown">
						<a href={href(electionPath(main.id))}
							aria-current={[main, ...sub].some((x) => isCurrent(x.id)) ? 'page' : undefined}>{main.year}</a>
						<span class="menu">
							{#each [{ e: main, name: 'Final' }, ...sub.map((e) => ({ e, name: 'Preliminary' }))] as { e, name } (e.id)}
								<a href={href(electionPath(e.id))} aria-current={isCurrent(e.id) ? 'page' : undefined}>{name}</a>
							{/each}
						</span>
					</span>
				{:else}
					<a href={href(electionPath(main.id))} aria-current={isCurrent(main.id) ? 'page' : undefined}>{main.label}</a>
				{/if}
			{/each}
		</span>
	</nav>
</header>

<main>
	{@render children()}
</main>

<footer>
	<p>
		By Chuan-Zheng Lee. Not an official result. The method and design decisions are mine; the code, including the
		data processing and this website, was largely written by <a href="https://claude.ai/">Claude</a>, under my
		direction.
	</p>
	<p>
		Data: <a href="https://www.electionresults.govt.nz/">Electoral Commission</a>. Code:
		<a href="https://github.com/czlee/elections">czlee/elections</a>.
	</p>
</footer>

<style>
	header { border-bottom: 1px solid var(--border); }
	nav, main, footer { max-width: 1040px; margin: 0 auto; padding: 0 16px; }
	nav { display: flex; flex-wrap: wrap; gap: 0.3em 1.2em; align-items: baseline; padding-block: 0.7em; }
	nav a { color: var(--text-2); text-decoration: none; }
	nav .brand { color: var(--text); font-weight: 700; margin-right: auto; }
	.elections { display: inline-flex; flex-wrap: wrap; gap: 0.15em; font-size: 0.9rem; }
	.elections a { padding: 0.05em 0.5em; border-radius: 4px; border: 1px solid transparent; }
	.elections a:hover { color: var(--text); }
	.elections a[aria-current='page'] { color: var(--text); font-weight: 600; border-color: var(--border); }
	.dropdown { position: relative; display: inline-flex; }
	.menu {
		display: none; position: absolute; top: 100%; left: 0; z-index: 10; min-width: 100%;
		flex-direction: column; padding: 0.25em; background: var(--surface); border: 1px solid var(--border); border-radius: 4px;
	}
	.dropdown:hover .menu, .dropdown:focus-within .menu { display: flex; }
	.menu a { white-space: nowrap; }
	.menu a:hover { background: var(--surface-2); }
	main { padding-bottom: 3em; }
	footer { border-top: 1px solid var(--border); color: var(--text-3); font-size: 0.8rem; padding-block: 1em 2em; }
	footer a { color: var(--text-2); }
</style>
