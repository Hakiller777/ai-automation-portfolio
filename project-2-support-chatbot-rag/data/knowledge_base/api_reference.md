# AcmeCRM — API Reference (Overview)

## Authentication

All API requests require an API key sent as a Bearer token:

```
Authorization: Bearer YOUR_API_KEY
```

Generate keys under Settings → Developer → API Keys. Keys are scoped to the
workspace and inherit the permissions of the user who created them.

## Base URL

```
https://api.acmecrm.example/v1
```

## Core endpoints

| Method | Path                | Description                     |
|--------|----------------------|----------------------------------|
| GET    | /contacts            | List contacts (paginated)       |
| POST   | /contacts            | Create a contact                |
| GET    | /deals                | List deals (paginated)          |
| POST   | /deals                | Create a deal                   |
| PATCH  | /deals/{id}           | Update a deal (e.g. stage)      |
| GET    | /pipelines            | List pipelines and stages       |

## Rate limits

100 requests per minute per API key. Exceeding the limit returns
`429 Too Many Requests` with a `Retry-After` header. Enterprise plans can
request a higher limit.

## Webhooks

Subscribe to events under Settings → Developer → Webhooks. Supported
events include `contact.created`, `deal.created`, `deal.stage_changed`, and
`deal.won`. Payloads are signed with an HMAC-SHA256 signature in the
`X-AcmeCRM-Signature` header — verify it before trusting the payload.

## Pagination

List endpoints return `{ "data": [...], "next_cursor": "..." }`. Pass
`next_cursor` as a query parameter to fetch the next page; a null
`next_cursor` means you've reached the last page.

## Errors

Errors return a JSON body: `{ "error": { "code": "...", "message": "..." } }`
with a matching HTTP status code (400 for validation errors, 401 for auth
failures, 404 for missing resources, 429 for rate limits, 500 for server
errors).
