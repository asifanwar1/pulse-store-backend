# Banner Module — API Release Notes

**For:** Admin dashboard + web storefront + mobile app frontend teams
**Base URL:** `{API_HOST}/api/v1/banners` (admin + public banner endpoints), `{API_HOST}/api/v1/media` (image upload, already exists — reused here)
**Status:** Shipped on `main`. Migration `f3a8d4c9e271_add_banners_table` applied.
**v1.1 update:** `DELETE` now permanently removes the row (was soft-delete in the first cut). Active/inactive toggling has moved to its own endpoint — see §5.

---

## 1. What this is

Backend support for the Canva-style banner editor: admins design a promo banner on a canvas (react-konva) in the admin app, export a flattened PNG, and save it along with the editable design JSON so it can be reopened later. The storefront and mobile app read back only the flattened image + link metadata — they never see the editable design.

**The backend does not render, crop, or resize anything.** The PNG your canvas exports is exactly what gets shown to customers. `design_json` is stored as an opaque blob — round-trip it, don't parse it.

---

## 2. Auth

All `/api/v1/banners/*` routes require an admin bearer token **except** `GET /api/v1/banners/active`, which is public (no `Authorization` header, callable from the storefront/mobile app directly).

```
Authorization: Bearer <admin_access_token>
```

Same token/login flow as the rest of the admin dashboard (`/api/v1/auth`). No new auth mechanism was introduced.

| Situation | Response |
|---|---|
| Missing/invalid token on an admin route | `401 { "detail": "Unauthorized" }` |
| Valid token, non-admin user | `403 { "detail": "Admin access required" }` |

---

## 3. Image upload flow (important — read before building the save button)

There is **no multipart upload on the banner endpoints themselves.** Images go through the existing shared media endpoint first, and the banner is then created/updated with plain JSON referencing the resulting URL(s). This matches how category images already work in the admin app — same two-step pattern.

**Step 1 — upload the flattened PNG(s):**

```
POST /api/v1/media/upload
Content-Type: multipart/form-data
Authorization: Bearer <admin_access_token>

file:   <the exported PNG/JPEG blob>
folder: "banners"
```

Response `201`:

```ts
interface MediaUploadResponse {
  id: string;         // storage path, e.g. "banners/3f9a2c1e.png"
  url: string;        // public CDN URL — this is what you store on the banner
  file_name: string | null;
  bucket: string;
  path: string;
}
```

Call this **once for the desktop export**, and **again for the mobile export** if you're shipping a separate aspect ratio. Accepts JPEG or PNG only; the server sniffs the real file header, it does not trust the extension or declared MIME type.

**Step 2 — create/update the banner** with the URL(s) from step 1 in the JSON body (see §5).

**Re-editing:** `GET /api/v1/banners/{id}` returns `design_json` — feed it straight back into your Konva `Stage` to reconstruct the editable canvas. Don't attempt to derive design state from the flattened PNG.

---

## 4. TypeScript types

Drop this into your API client / types file:

```ts
export type LinkType = "product" | "category" | "url" | "none";

// Fixed set today. Treat as an open enum — the backend may add more
// placements over time without a migration, so don't hard-fail on an
// unrecognized value, just skip rendering that section.
export type Placement = "home_top" | "home_mid" | "category_page";

export interface Banner {
  id: number;
  title: string;                        // internal label, never shown to customers
  image_url: string;
  image_url_mobile: string | null;
  design_json: Record<string, unknown>; // opaque — round-trip only
  link_type: LinkType;
  link_value: string | null;            // product id / category id / raw URL, depending on link_type
  placement: Placement;
  position: number;                     // ascending sort within a placement
  is_active: boolean;
  start_date: string | null;            // ISO 8601, null = active immediately
  end_date: string | null;              // ISO 8601, null = no expiry
  created_at: string;
  updated_at: string | null;
  created_by: number | null;
}

// What the public /active endpoint returns — no design_json, ever.
export interface BannerPublic {
  id: number;
  image_url: string;
  image_url_mobile: string | null;
  link_type: LinkType;
  link_value: string | null;
  placement: Placement;
  position: number;
}

export interface BannerListResponse {
  data: Banner[];
  count: number; // total matching rows, not page size
}

export interface ActiveBannersListResponse {
  data: BannerPublic[];
  count: number;
}

export interface BannerCreatePayload {
  title: string;
  image_url: string;
  image_url_mobile?: string | null;
  design_json: Record<string, unknown>;  // must not be {}
  link_type: LinkType;
  link_value?: string | null;
  placement: Placement;
  position?: number;                     // default 0
  is_active?: boolean;                   // default true
  start_date?: string | null;
  end_date?: string | null;
}

// Same shape, everything optional — send only the fields you changed.
export type BannerUpdatePayload = Partial<BannerCreatePayload>;

// Body for the dedicated active/inactive toggle endpoint.
export interface BannerStatusUpdatePayload {
  is_active: boolean;
}

export interface MediaUploadResponse {
  id: string;
  url: string;
  file_name: string | null;
  bucket: string;
  path: string;
}
```

---

## 5. Endpoints

### `POST /api/v1/banners/` — create a banner
**Auth:** admin

Request body (`application/json`):

```json
{
  "title": "Summer Sale Hero",
  "image_url": "https://cdn.example.com/banners/1/abc.png",
  "image_url_mobile": "https://cdn.example.com/banners/1/abc-mobile.png",
  "design_json": { "elements": [{ "type": "text", "value": "50% OFF" }] },
  "link_type": "category",
  "link_value": "14",
  "placement": "home_top",
  "position": 1,
  "is_active": true,
  "start_date": null,
  "end_date": null
}
```

Response `201` — full `Banner` object (see §4), including generated `id`, `created_at`, `created_by`.

---

### `GET /api/v1/banners/` — list banners (admin)
**Auth:** admin

| Query param | Type | Default | Notes |
|---|---|---|---|
| `page` | number | `1` | 1-indexed |
| `limit` | number | `10` | max `100` |
| `placement` | `Placement` | — | optional filter |
| `is_active` | boolean | — | optional filter |

Ordered by `placement, position` (with `id` as a tiebreaker for equal `position` values). **This endpoint returns every banner regardless of status by default** — pass `?is_active=true` if you only want the live ones, or build an Active/Inactive toggle in the UI rather than assuming inactive banners are hidden here.

Response `200`:

```json
{
  "data": [ /* Banner[] — includes design_json */ ],
  "count": 37
}
```

---

### `GET /api/v1/banners/{id}` — get one banner (admin, for re-editing)
**Auth:** admin

Response `200` — full `Banner`, including `design_json`.
Response `404` — `{ "detail": "Banner not found" }`.

---

### `PUT /api/v1/banners/{id}` — update a banner (partial)
**Auth:** admin

Request body: any subset of `BannerUpdatePayload`. Omitted fields are left unchanged — you do **not** need to resend `image_url` if only changing `position`, for example. To replace the image, upload the new file via `/api/v1/media/upload` first and send the new `image_url`; the old storage object is not deleted automatically.

```json
{ "position": 5 }
```

Response `200` — full updated `Banner`.
Response `404` / `422` (see §6).

> This endpoint *can* still accept `is_active` in the body, but prefer `PATCH /{id}/status` below for a plain activate/deactivate toggle — it's a smaller payload and matches the same pattern used for review visibility elsewhere in the admin app.

---

### `PATCH /api/v1/banners/{id}/status` — activate / deactivate a banner
**Auth:** admin

Use this for the "Active/Inactive" toggle in the banner list UI — it does **not** delete anything, it only flips visibility. An inactive banner immediately stops appearing in the public `/active` endpoint but stays fully intact (including `design_json`) for admins and can be reactivated at any time.

Request body:

```json
{ "is_active": false }
```

Response `200` — full updated `Banner`.
Response `404` — `{ "detail": "Banner not found" }`.

---

### `DELETE /api/v1/banners/{id}` — permanently delete a banner
**Auth:** admin

**This is a hard delete** — the row is removed from the database and cannot be recovered. It does *not* flip `is_active`; use `PATCH /{id}/status` for that instead. The underlying image file in storage is **not** removed by this call (known follow-up, see §9) — only the `banners` row.

Response `204` — no body.
Response `404` — `{ "detail": "Banner not found" }` (also returned if you call delete twice on the same id).

---

### `GET /api/v1/banners/active` — public: fetch banners to display
**Auth:** none — safe to call from the storefront and mobile app directly.

| Query param | Type | Required | Notes |
|---|---|---|---|
| `placement` | `Placement` | **yes** | one call per homepage section, e.g. `?placement=home_top` |

Filters applied server-side: `is_active = true`, matching `placement`, and the current time falls inside `[start_date, end_date]` (either bound being `null` means unbounded on that side). Ordered by `position` ascending.

**`design_json` is never present in this response** — it's a structurally different schema (`BannerPublic`), not just a stripped-down `Banner`.

Response `200`:

```json
{
  "data": [
    {
      "id": 1,
      "image_url": "https://cdn.example.com/banners/1/abc.png",
      "image_url_mobile": "https://cdn.example.com/banners/1/abc-mobile.png",
      "link_type": "category",
      "link_value": "14",
      "placement": "home_top",
      "position": 1
    }
  ],
  "count": 1
}
```

Response `422` if `placement` is omitted or isn't one of the known values.

**Rendering the click target:**

| `link_type` | `link_value` holds | Suggested handling |
|---|---|---|
| `product` | product id | navigate to product detail |
| `category` | category id | navigate to category listing |
| `url` | a raw URL | open it (internal route or external link) |
| `none` | `null` | non-clickable, decorative banner |

---

## 6. Validation & error responses to handle

| Case | Result |
|---|---|
| `design_json` is `{}` or missing on create | `422` — must have been built in the editor |
| `start_date` after `end_date` | `422 { "detail": "start_date must be before end_date" }` (or FastAPI's structured validation error on create — see below) |
| `placement` / `link_type` not one of the known enum values | `422`, FastAPI validation error |
| `link_type: "product"` / `"category"` with a `link_value` that doesn't match any real row | **Not** an error — the banner still saves (product/category may not exist yet). Backend logs a warning server-side only. |
| `position` collisions within a placement | Allowed — sort is stable via `id` |
| `DELETE` on an id that's already gone | `404`, safe to treat as "already deleted" in the UI |

Standard FastAPI validation error shape (create-time / body validators):

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "design_json"],
      "msg": "Value error, design_json must not be empty",
      "input": {}
    }
  ]
}
```

Recommend validating `design_json` non-emptiness and the date ordering client-side too, so the editor can surface these before round-tripping to the API.

---

## 7. Suggested admin editor flow

1. Build the banner in the react-konva canvas.
2. On save: export the flattened image(s) (`stage.toDataURL()` / `toBlob()` for desktop, and again for mobile if you support a separate export ratio).
3. `POST /api/v1/media/upload` (multipart, `folder: "banners"`) for each image → get back `url`.
4. Serialize the canvas state as `design_json` (whatever shape your Konva setup already produces — the backend does not care).
5. `POST /api/v1/banners/` (new) or `PUT /api/v1/banners/{id}` (editing) with `image_url` / `image_url_mobile` / `design_json` / metadata fields together as one JSON body.
6. To reopen for editing later: `GET /api/v1/banners/{id}`, feed `design_json` back into the Stage.
7. For the list view's Active/Inactive switch, call `PATCH /api/v1/banners/{id}/status` — don't call `PUT` for this and don't call `DELETE`.

## 8. Suggested storefront/mobile consumption

- One call per homepage section: `GET /api/v1/banners/active?placement=home_top`, `?placement=home_mid`, etc.
- Render `image_url_mobile` when present on small viewports, otherwise fall back to `image_url`.
- No polling needed today — banners change infrequently. If traffic grows, response caching (60s in-memory or Redis) is a planned follow-up, not yet implemented.

---

## 9. Known follow-ups (not blocking v1)

- `DELETE` removes the DB row but does not remove the image from storage — same for replacing an image via `PUT`. Acceptable for now, may want a cleanup job later.
- No response caching on `/active` yet — fine at current traffic, revisit if homepage load becomes a bottleneck.
- `Placement` values may grow (e.g. `checkout_page`, `search_results`) — these are plain strings on the backend precisely so new ones can ship without a migration; frontend should treat unknown placements gracefully rather than crashing.
