// Builds mockoon/prasang.json (a Mockoon environment) from:
//   - mockoon/data/*.json      datasets, inlined as data buckets (id = file name)
//   - derived buckets          artistCards / artistDetails / artistContacts from artists.json
//   - mockoon/routes.mjs       route table
//   - contracts/examples/**    bodies referenced by `file:` in routes
// Run: node mockoon/build.mjs   (paths are resolved relative to this file)
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { routes } from './routes.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const read = (p) => readFileSync(join(root, p), 'utf8');

// ---- data buckets ----
const buckets = {};
for (const f of readdirSync(join(here, 'data')).filter((f) => f.endsWith('.json'))) {
  buckets[basename(f, '.json')] = JSON.parse(read(`mockoon/data/${f}`));
}
const artists = buckets.artists;
buckets.artistCards = artists.map(({ media, contactPhone, whatsappNumber, ...card }) => card);
buckets.artistDetails = artists.map(({ contactPhone, whatsappNumber, ...detail }) => detail);
buckets.artistContacts = artists.map((a) => ({
  artistId: a.artistId, name: a.name, contactPhone: a.contactPhone, whatsappNumber: a.whatsappNumber, instagramHandle: a.instagramHandle,
}));

// Single-record buckets reuse the canonical examples.
buckets['artist-profile'] = JSON.parse(read('contracts/examples/artists/me.response.json'));
buckets['me-planner'] = JSON.parse(read('contracts/examples/me/post.response.json'));

const data = Object.entries(buckets).map(([id, value]) => ({
  uuid: randomUUID(), id, name: id, documentation: '', value: JSON.stringify(value),
}));

// ---- routes ----
const JSON_HEADERS = [{ key: 'Content-Type', value: 'application/json' }];
const toResponse = (r, i) => ({
  uuid: randomUUID(),
  label: r.label ?? '',
  statusCode: r.status,
  body: r.file ? read(`contracts/examples/${r.file}`) : (r.body ?? ''),
  bodyType: 'INLINE',
  headers: r.status === 204 ? [] : JSON_HEADERS,
  rules: (r.rules ?? []).map((rule) => ({ operator: 'equals', invert: false, ...rule })),
  rulesOperator: r.rulesOperator ?? 'AND',
  default: r.default ?? i === (r._count - 1),
  latency: 0,
  disableTemplating: false,
});

const mockRoutes = routes.map((route) => ({
  uuid: randomUUID(),
  type: 'http',
  documentation: route.doc ?? '',
  method: route.method,
  endpoint: route.path,
  // Last response is the default (no rules); earlier ones are matched by rules in order.
  responses: route.responses.map((r, i) => toResponse({ ...r, _count: route.responses.length }, i)),
  responseMode: null,
}));

const env = {
  uuid: 'b1d6a2e4-7c1f-4f3e-9a55-5c0e2f6d7a10',
  lastMigration: 33,
  name: 'Prasang API (mock)',
  endpointPrefix: 'api/v1',
  latency: 300,
  port: 3001,
  hostname: '',
  cors: true,
  headers: JSON_HEADERS,
  proxyMode: false,
  data,
  routes: mockRoutes,
  rootChildren: mockRoutes.map((r) => ({ type: 'route', uuid: r.uuid })),
  folders: [],
};

writeFileSync(join(here, 'prasang.json'), JSON.stringify(env, null, 2) + '\n');
console.log(`mockoon/prasang.json: ${mockRoutes.length} routes, ${data.length} data buckets`);
