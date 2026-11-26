import { ogGet } from '#lib/server/og.js';

export const prerender = true;
export { entries } from '../+page.server.js';
export const GET = ogGet('/[[base=base]]/electorate/[slug]');
