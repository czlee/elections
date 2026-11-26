import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Served from https://czlee.nz/elections/margins/ (GitHub Pages for czlee/elections,
// with the build copied into a margins/ folder).
const base = process.env.BASE_PATH ?? '/elections/margins';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ strict: true }),
			paths: { base }
		})
	]
});
