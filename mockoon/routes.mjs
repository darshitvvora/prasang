import { readFileSync } from 'node:fs';

// Mockoon route table for the Prasang mock API. Consumed by build.mjs.
// Each route: { method, path, doc?, responses: [{ status, body? | file?, rules?, label? }] }
// Responses are tried in order; the LAST one is the default (no rules).
//
// Templating notes (verified on Mockoon 9.8):
//  - `{{#if (queryParam 'x')}}` is always truthy — use `(eq (queryParam 'x' '') '')`.
//  - Never emit `}}}}`; add a space: `{{{stringify x}}} }`.
//  - There is no `{{status}}` helper: pick status codes with response rules (params regex, header, global_var).
//  - `neq` does not exist and `or` does not return its operand — keep conditionals to `eq` or rules.
//  - Global vars (setGlobalVar/getGlobalVar) hold the new-user journey state; POST /_mock/reset clears them.

const err = (code, message, details = {}) => JSON.stringify({ error: { code, message, details } });

const hdr = (value) => ({ target: 'header', modifier: 'Authorization', value });
const ARTIST = hdr('Bearer mock-artist');
const PLANNER = hdr('Bearer mock-planner');
const NEW = hdr('Bearer mock-new');
const NO_AUTH = { target: 'header', modifier: 'Authorization', value: '', operator: 'null' };

const gvar = (name, regex) => ({ target: 'global_var', modifier: name, value: regex, operator: 'regex' });
const KNOWN_SLUGS = '^(' + JSON.parse(readFileSync(new URL('./data/artists.json', import.meta.url), 'utf8'))
  .map((a) => a.slug.replace(/[-]/g, '\\-')).join('|') + ')$';

const unauth = { status: 401, rules: [NO_AUTH], body: err('unauthenticated', 'Please sign in to continue') };
// mock-new before POST /artists: artist-scoped reads 404 like the real backend will.
const noProfileBody = err('artist_profile_not_found', 'Create your artist profile to continue');
// Before POST /me there is no Prasang user at all → profile_required (contract), then artist_profile_not_found until POST /artists.
const profileRequiredBody = err('profile_required', 'Complete your profile to continue');
const NO_USER_404 = { status: 404, rules: [NEW, { target: 'global_var', modifier: 'newRole', value: '^$', operator: 'regex' }], body: profileRequiredBody };
const NO_USER_404_UNSET = { status: 404, rules: [NEW, { target: 'global_var', modifier: 'newRole', value: '', operator: 'null' }], body: profileRequiredBody };
const NO_PROFILE_404 = { status: 404, rules: [NEW, { target: 'global_var', modifier: 'newSlug', value: '^$', operator: 'regex' }], body: noProfileBody };
const NO_PROFILE_404_UNSET = { status: 404, rules: [NEW, { target: 'global_var', modifier: 'newSlug', value: '', operator: 'null' }], body: noProfileBody };

const forbidden = (rules) => ({ status: 403, rules, rulesOperator: 'OR', body: err('forbidden', 'This action is not available for your account') });


// Page wrapper around a list held in template var @list.
const pageOf = (extra = '') =>
  `{"items": {{{stringify @list}}} , "total": {{len @list}}, "page": 1, "size": 20${extra}}`;

// Filter @list by `field` when query param `param` is non-empty.
const filterBy = (param, field) =>
  `{{#unless (eq (queryParam '${param}' '') '')}}{{setVar 'list' (filter @list (object ${field}=(queryParam '${param}')))}}{{/unless}}`;
const filterFlag = (param, field) =>
  `{{#if (eq (queryParam '${param}' '') 'true')}}{{setVar 'list' (filter @list (object ${field}=true))}}{{/if}}`;

const newUserMe =
  `{"id": "c0ffee00-0000-4000-8000-000000000001", "email": "new.user@gmail.com", ` +
  `"fullName": "{{getGlobalVar 'newName'}}", "phone": null, "role": "{{getGlobalVar 'newRole'}}", "avatarUrl": null, ` +
  `"artistSlug": ARTIST_SLUG, "createdAt": "2026-09-29T10:00:00Z"}`;

export const routes = [
  // ---------- mock control ----------
  { method: 'post', path: '_mock/reset', doc: 'Clears new-user journey state',
    responses: [{ status: 200, body: `{{setGlobalVar 'newRole' ''}}{{setGlobalVar 'newName' ''}}{{setGlobalVar 'newSlug' ''}}{"ok": true}` }] },
  { method: 'put', path: '_mock/upload/:key', doc: 'Stands in for the presigned R2 upload URL',
    responses: [{ status: 200, body: '{"ok": true}' }] },

  // ---------- me ----------
  { method: 'get', path: 'me', responses: [
    unauth,
    { status: 200, rules: [PLANNER], file: 'me/post.response.json' },
    { status: 200, rules: [NEW, gvar('newRole', '^(artist|planner)$'), gvar('newSlug', '.+')], body: newUserMe.replace('ARTIST_SLUG', `"{{getGlobalVar 'newSlug'}}"`) },
    { status: 200, rules: [NEW, gvar('newRole', '^(artist|planner)$')], body: newUserMe.replace('ARTIST_SLUG', 'null') },
    { status: 404, rules: [NEW], body: err('profile_required', 'Complete your profile to continue') },
    { status: 200, rules: [ARTIST], file: 'me/get.response.json' },
    { status: 401, body: err('unauthenticated', 'Your session has expired. Please sign in again.') },
  ] },
  { method: 'post', path: 'me', responses: [
    unauth,
    { status: 201, rules: [NEW], body:
      `{{setGlobalVar 'newRole' (body 'role')}}{{setGlobalVar 'newName' (body 'fullName')}}` +
      `{"id": "c0ffee00-0000-4000-8000-000000000001", "email": "new.user@gmail.com", "fullName": "{{body 'fullName'}}", ` +
      `"phone": {{#if (eq (body 'phone' '') '')}}null{{else}}"{{body 'phone'}}"{{/if}}, "role": "{{body 'role'}}", ` +
      `"avatarUrl": null, "artistSlug": null, "createdAt": "2026-09-29T10:00:00Z"}` },
    { status: 409, body: err('profile_exists', 'Your profile already exists') },
  ] },
  { method: 'patch', path: 'me', responses: [
    unauth,
    { status: 200, rules: [PLANNER], body:
      `{{setVar 'm' (dataRaw 'me-planner')}}{{{replace (stringify @m) (concat '"fullName": "' @m.fullName '"') (concat '"fullName": "' (body 'fullName' @m.fullName) '"')}}}` },
    { status: 200, file: 'me/get.response.json' },
  ] },

  // ---------- auth providers (which sign-in methods the UI should offer) ----------
  { method: 'get', path: 'auth/providers', responses: [{ status: 200, file: 'auth/providers.response.json' }] },
  { method: 'get', path: 'site-info', responses: [{ status: 200, file: 'site/info.response.json' }] },
  { method: 'post', path: 'contact', responses: [{ status: 201, file: 'site/contact.response.json' }] },

  // ---------- public ----------
  { method: 'get', path: 'locations', responses: [{ status: 200, body: `{{{stringify (dataRaw 'locations')}}}` }] },
  { method: 'get', path: 'search/suggestions', responses: [{ status: 200, file: 'search/suggestions.response.json' }] },
  { method: 'get', path: 'search/artists', doc: 'Mock filters: artistType, city, area, featuredOnly, verifiedOnly (exact match). Others accepted, ignored.',
    responses: [{ status: 200, body:
      `{{setVar 'list' (dataRaw 'artistCards')}}` +
      filterBy('artistType', 'artistType') + filterBy('city', 'locationCity') + filterBy('area', 'locationArea') +
      filterFlag('featuredOnly', 'isFeatured') + filterFlag('verifiedOnly', 'isVerified') +
      pageOf(`, "facets": {"artistType": [], "city": []}`) }] },
  { method: 'get', path: 'artists/featured', responses: [{ status: 200, body:
    `{{setVar 'list' (filter (dataRaw 'artistCards') (object isFeatured=true))}}{"items": {{{stringify @list}}} }` }] },

  // ---------- artist self (must precede artists/:slug) ----------
  { method: 'get', path: 'artists/me', responses: [
    unauth,
    forbidden([PLANNER]),
    { status: 200, rules: [NEW, gvar('newSlug', '.+')], body: `{{{stringify (dataRaw 'artist-profile')}}}` },
    NO_USER_404, NO_USER_404_UNSET,
    { status: 404, rules: [NEW], body: err('artist_profile_not_found', 'Create your artist profile to continue') },
    { status: 200, body: `{{{stringify (dataRaw 'artist-profile')}}}` },
  ] },
  { method: 'post', path: 'artists', responses: [
    unauth,
    forbidden([PLANNER]),
    { status: 201, rules: [NEW], body: `{{setGlobalVar 'newSlug' 'arjun-malhotra-magic'}}{{{stringify (dataRaw 'artist-profile')}}}` },
    { status: 409, body: err('artist_exists', 'You already have an artist profile') },
  ] },
  { method: 'patch', path: 'artists/me', responses: [unauth, forbidden([PLANNER]), { status: 200, body: `{{{stringify (dataRaw 'artist-profile')}}}` }] },
  { method: 'get', path: 'artists/me/dashboard', responses: [unauth, forbidden([PLANNER]), NO_USER_404, NO_USER_404_UNSET, NO_PROFILE_404, NO_PROFILE_404_UNSET, { status: 200, file: 'artists/dashboard.response.json' }] },
  { method: 'get', path: 'artists/me/media', responses: [unauth, NO_USER_404, NO_USER_404_UNSET, NO_PROFILE_404, NO_PROFILE_404_UNSET, { status: 200, file: 'media/list.response.json' }] },
  { method: 'post', path: 'artists/me/media/upload-url', responses: [unauth, { status: 200, body:
    `{{setVar 'id' (faker 'string.alphanumeric' 12)}}` +
    `{"uploadUrl": "http://localhost:3001/api/v1/_mock/upload/{{@id}}", "storageKey": "artists/art-001/{{@id}}.jpg", ` +
    `"expiresAt": "{{dateTimeShift date=(now) minutes=5 format="yyyy-MM-dd'T'HH:mm:ss'Z'"}}", "headers": {"Content-Type": "{{body 'contentType'}}"} }` }] },
  { method: 'post', path: 'artists/me/media', responses: [unauth,
    { status: 201, rules: [{ target: 'body', modifier: 'kind', value: 'youtube' }], file: 'media/create-youtube.response.json' },
    { status: 201, body:
    `{"id": "med-{{faker 'string.alphanumeric' 6}}", "kind": "{{body 'kind'}}", ` +
    `"url": "{{#if (eq (body 'url' '') '')}}/artists/magician.png{{else}}{{body 'url'}}{{/if}}", "embedUrl": null, "thumbnailUrl": null, ` +
    `"caption": {{#if (eq (body 'caption' '') '')}}null{{else}}"{{body 'caption'}}"{{/if}}, "displayOrder": 9}` }] },
  { method: 'post', path: 'artists/me/avatar', responses: [unauth, { status: 200, body: '{"profileImageUrl": "/artists/magician.png"}' }] },
  { method: 'delete', path: 'artists/me/media/:id', responses: [unauth, { status: 204, body: '' }] },
  { method: 'put', path: 'artists/me/media/order', responses: [unauth, { status: 200, file: 'media/order.response.json' }] },

  // ---------- public artist by slug ----------
  { method: 'get', path: 'artists/:slug/reviews', responses: [{ status: 200, body:
    `{{setVar 'list' (dataRaw 'reviews')}}${pageOf()}` }] },
  { method: 'get', path: 'artists/:slug/similar', doc: 'Same artistType; mock may include the artist itself (UI filters it out).',
    responses: [{ status: 200, body:
      `{{setVar 'a' (find (dataRaw 'artistCards') (object slug=(urlParam 'slug')))}}` +
      `{{#if @a}}{{setVar 'list' (filter (dataRaw 'artistCards') (object artistType=@a.artistType))}}{{else}}{{setVar 'list' (array)}}{{/if}}` +
      `{"items": {{{stringify @list}}} }` }] },
  { method: 'post', path: 'artists/:slug/contact-click', responses: [{ status: 204, body: '' }] },
  { method: 'get', path: 'artists/:slug', responses: [
    { status: 200, rules: [{ target: 'params', modifier: 'slug', value: KNOWN_SLUGS, operator: 'regex' }], body:
      `{{{stringify (find (dataRaw 'artistDetails') (object slug=(urlParam 'slug')))}}}` },
    { status: 404, body: err('artist_not_found', 'No artist found for this link') },
  ] },

  // ---------- leads ----------
  { method: 'post', path: 'leads', responses: [
    unauth,
    forbidden([ARTIST]),
    { status: 201, body:
      `{{setVar 'c' (find (dataRaw 'artistContacts') (object artistId=(body 'artistId')))}}` +
      `{"leadId": "lead-{{faker 'string.numeric' 4}}", "artist": {"name": "{{@c.name}}", "contactPhone": "{{@c.contactPhone}}", ` +
      `"whatsappNumber": {{#if @c.whatsappNumber}}"{{@c.whatsappNumber}}"{{else}}null{{/if}}, ` +
      `"instagramHandle": {{#if @c.instagramHandle}}"{{@c.instagramHandle}}"{{else}}null{{/if}} } }` },
  ] },
  { method: 'get', path: 'leads/artist', responses: [unauth, forbidden([PLANNER]), NO_USER_404, NO_USER_404_UNSET, NO_PROFILE_404, NO_PROFILE_404_UNSET, { status: 200, body:
    `{{setVar 'list' (dataRaw 'artist-leads' 'items')}}${filterBy('status', 'status')}` +
    pageOf(`, "counts": {{{stringify (dataRaw 'artist-leads' 'counts')}}} , "plan": {{{stringify (dataRaw 'artist-leads' 'plan')}}} `) }] },
  { method: 'patch', path: 'leads/:id/planner-answer', responses: [unauth, forbidden([ARTIST]), { status: 200, file: 'leads/planner-answer.response.json' }] },
  { method: 'patch', path: 'leads/:id', responses: [unauth, { status: 200, body:
    `{{setVar 'l' (find (dataRaw 'artist-leads' 'items') (object id=(urlParam 'id')))}}` +
    `{{{replace (stringify @l) (concat '"status": "' @l.status '"') (concat '"status": "' (body 'status') '"')}}}` }] },
  { method: 'get', path: 'leads/planner', responses: [unauth, forbidden([ARTIST]), { status: 200, body:
    `{{setVar 'list' (dataRaw 'planner-inquiries' 'items')}}${filterBy('status', 'status')}` +
    pageOf(`, "counts": {{{stringify (dataRaw 'planner-inquiries' 'counts')}}} , "summary": {{{stringify (dataRaw 'planner-inquiries' 'summary')}}} `) }] },

  // ---------- subscriptions ----------
  { method: 'get', path: 'subscriptions/plans', responses: [{ status: 200, body: `{"items": {{{stringify (dataRaw 'plans')}}} }` }] },
  { method: 'get', path: 'subscriptions/me/payments', responses: [unauth, forbidden([PLANNER]), { status: 200, file: 'subscriptions/payments.response.json' }] },
  { method: 'get', path: 'subscriptions/me', responses: [
    unauth,
    { status: 200, rules: [NEW], body:
      '{"plan": {"tier": "free", "name": "Free", "status": "free", "leadLimitMonthly": 3, "leadsUsedThisMonth": 0, "leadsRemaining": 3, "periodEnd": null, "trialEndsAt": null, "trialAvailable": true}, "subscription": null}' },
    { status: 200, file: 'subscriptions/me.response.json' },
  ] },
  { method: 'post', path: 'subscriptions/trial', responses: [
    unauth,
    { status: 200, rules: [NEW], body:
      `{"tier": "{{body 'tier'}}", "name": "{{capitalize (body 'tier')}}", "status": "trial", "leadLimitMonthly": {{#if (eq (body 'tier') 'basic')}}15{{else}}-1{{/if}}, ` +
      `"leadsUsedThisMonth": 0, "leadsRemaining": {{#if (eq (body 'tier') 'basic')}}15{{else}}null{{/if}}, "periodEnd": null, ` +
      `"trialEndsAt": "{{dateTimeShift date=(now) days=7 format='yyyy-MM-dd'}}", "trialAvailable": false}` },
    { status: 409, body: err('trial_used', 'You have already used your free trial') },
  ] },
  { method: 'post', path: 'subscriptions', responses: [unauth, { status: 201, body:
    `{"subscriptionId": "sub-{{faker 'string.alphanumeric' 4}}", "checkout": {"keyId": "rzp_test_mock", ` +
    `"razorpaySubscriptionId": "sub_mock{{faker 'string.alphanumeric' 10}}", "name": "Prasang", ` +
    `"description": "{{capitalize (body 'tier')}} plan — {{body 'billingCycle'}}", ` +
    `"prefill": {"name": "Arjun Malhotra", "email": "arjun.malhotra@gmail.com", "contact": "9820011001"} } }` }] },
  { method: 'post', path: 'subscriptions/verify', responses: [unauth, { status: 200, file: 'subscriptions/verify.response.json' }] },
  { method: 'post', path: 'subscriptions/cancel', responses: [unauth, { status: 200, file: 'subscriptions/cancel.response.json' }] },
  { method: 'post', path: 'subscriptions/webhook', responses: [{ status: 200, body: '{"ok": true}' }] },
];
