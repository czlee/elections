import { DEFAULT_ID } from '#lib/elections.js';
import { squarePng } from '#lib/server/og.js';

export const prerender = true;
// A 1080×1080 version of the home page's card, e.g. for posting to Twitter.
export const GET = () => squarePng(DEFAULT_ID);
