// A proxy-only project needs explicit routing output even when it has no
// static pages or functions. An empty static output can deploy as READY/404.
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const root = new URL('./', import.meta.url);
const config = JSON.parse(await readFile(new URL('vercel.json', root), 'utf8'));
assert.equal(config.rewrites.length, 1);
assert.equal(config.rewrites[0].source, '/:path*');
assert.match(config.rewrites[0].destination, /^https:\/\/[a-z0-9.-]+\/bbmod-origin\/:path\*$/);
assert.equal(config.headers.length, 1);
assert.equal(config.headers[0].source, '/:path*');
const headers = Object.fromEntries(config.headers[0].headers.map(({ key, value }) => [key, value]));
assert.equal(headers['x-vercel-enable-rewrite-caching'], '0');
assert.equal(headers['Cache-Control'], 'private, no-store');
const output = {
  version: 3,
  routes: [{ src: '^/(.*)$', dest: config.rewrites[0].destination.replace(':path*', '$1'), headers }],
};
await mkdir(new URL('.vercel/output/static/', root), { recursive: true });
await writeFile(new URL('.vercel/output/config.json', root), JSON.stringify(output, null, 2) + '\n');
console.log('Built Vercel gateway: 1 external route, no functions, shared caching disabled.');
