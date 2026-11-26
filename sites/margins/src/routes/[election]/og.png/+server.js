import { ELECTIONS } from '#lib/elections.js';
import { ogGet } from '#lib/server/og.js';

export const prerender = true;
export const entries = () => ELECTIONS.map((e) => ({ election: e.id }));
export const GET = ogGet();
