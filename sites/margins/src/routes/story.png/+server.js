import { DEFAULT_ID } from '#lib/elections.js';
import { storyPng } from '#lib/server/og.js';

export const prerender = true;
// A 1080×1920 (9:16) version of the home page's card, for Instagram stories.
export const GET = () => storyPng(DEFAULT_ID);
