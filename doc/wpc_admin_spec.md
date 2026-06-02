# WPC Projekt Adminisztrátor — Claude Code Spec
**Version:** 2.0 | **Updated:** 2026-06-02

---

## 1. Purpose & Context

WPC (Wood-Plastic Composite) terrace installation management tool for Nagy Zsolt's business.
Replaces a Google Spreadsheet (~80 executed jobs/year, 100+ in pipeline, 4 active crews).
Hungarian UI. Multi-user: Zsolt + 1 admin + crews viewing PDFs on phones on-site.

---

## 2. Unified Design System

### 2.1 Why unified

Both the **Admin module** (this spec) and the **WPC Planner** (already built in Claude Code)
must share one design system so they can merge in Phase 2 without a redesign.

**Resolution: Admin adopts the Planner's design system.**
- Design TOKENS → from `wpc_planner_mockup.html` (canonical)
- Layout / UX PATTERNS → from `wpc-projekt-admin.html` (sidebar + table + detail panel)

### 2.2 Canonical Design Tokens

```css
:root {
  --paper:    #f4efe6;
  --paper-2:  #ece5d8;
  --card:     #fbf8f1;
  --sunk:     #e9e2d4;
  --ink:      #1c1a17;
  --ink-2:    #46423b;
  --ink-3:    #8b8479;
  --ink-4:    #b4ad9f;
  --rule:     #ddd5c5;
  --rule-2:   #c8bfac;
  --clay:     #bb5b34;   /* primary CTA, active states */
  --clay-soft:#f0d9cd;
  --clay-ink: #9c4827;
  --moss:     #5c7a4a;   /* kész / success */
  --amber:    #c8902f;   /* betervezve / warning */
  --sky:      #3f6e8c;   /* lebeszélve / info */
  --mono:   'IBM Plex Mono', ui-monospace, monospace;
  --serif:  'DM Serif Display', Georgia, serif;
  --sans:   'IBM Plex Sans', system-ui, sans-serif;
  --shadow: 0 1px 0 var(--rule), 0 8px 30px rgba(40,30,15,.06);
}
[data-theme="dark"] {
  --paper:#16140f; --paper-2:#1c1a14; --card:#1f1c16; --sunk:#100e0a;
  --ink:#ece6d8; --ink-2:#b8b1a1; --ink-3:#7d776a; --ink-4:#544f45;
  --rule:#2c281f; --rule-2:#3c3729;
  --clay:#d97a4f; --clay-soft:#3a241a; --clay-ink:#e9956c;
  --moss:#8fb073; --amber:#d9aa54; --sky:#6fa3c2;
  --shadow:0 1px 0 var(--rule),0 10px 40px rgba(0,0,0,.4);
}
```

Google Fonts import (same as Planner):
```html
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

### 2.3 Status Badge Colors

```
felmérendő  → --ink-3  (grey)
lebeszélve  → --sky    (blue)
betervezve  → --amber  (amber)
folyamatban → --clay   (clay/orange)
kész        → --moss   (green)
```

### 2.4 App Shell Layout

From the Admin POC — keep this layout, apply Planner tokens:

```
┌──────────────────────────────────────────────────────────────┐
│  TOPBAR: [W] WPC Planner | project chip | theme | help       │ 60px
├──────────┬───────────────────────────────┬───────────────────┤
│          │                               │                   │
│ SIDEBAR  │   MAIN STAGE                 │  DETAIL PANEL     │
│ 228px    │   stat strip (4 KPIs)        │  332px            │
│          │   filter bar                 │  HTMX slide-in    │
│ nav      │   search input               │                   │
│ items    │   data table                 │  on row click     │
│          │                               │                   │
└──────────┴───────────────────────────────┴───────────────────┘
```

- Sidebar: `var(--card)` bg, `2px solid var(--clay)` left border on active item
- Topbar: `var(--card)` bg, `1px solid var(--rule)` bottom
- Brand mark: 30px square, `var(--ink)` bg, `var(--paper)` text, `var(--mono)` font, "W"
- Brand name: `var(--serif)` 19px — "WPC Planner"
- Brand sub: `var(--mono)` 10px uppercase — "MDLR Flow · belső eszköz"

### 2.5 Typography Rules

- Section labels: `var(--mono)` 10px, 0.14em letter-spacing, uppercase, `var(--ink-3)`
- Table headers: `var(--mono)` 10px, 0.06em letter-spacing, uppercase, `var(--ink-3)`
- KPI stat values: `var(--mono)` 23px, font-weight 600, tabular-nums
- Body text: `var(--sans)` 14px
- Mono values (prices, dates, codes): `var(--mono)`

### 2.6 Reusable Component CSS

**Pill badge:**
```css
.pill { display:inline-flex; align-items:center; gap:6px; font-family:var(--mono);
  font-size:10px; letter-spacing:.05em; text-transform:uppercase; padding:3px 9px;
  border-radius:99px; border:1px solid currentColor; line-height:1.5; }
.pill::before { content:''; width:5px; height:5px; border-radius:50%; background:currentColor; }
.pill.clay{color:var(--clay)} .pill.moss{color:var(--moss)}
.pill.amber{color:var(--amber)} .pill.sky{color:var(--sky)} .pill.muted{color:var(--ink-3)}
```

**Buttons:**
```css
.btn { font-family:var(--mono); font-size:12px; padding:11px 16px; border-radius:9px;
  border:1px solid var(--ink); background:var(--ink); color:var(--paper); cursor:pointer; }
.btn.ghost { background:transparent; color:var(--ink-2); border-color:var(--rule-2); }
```

**Form fields:**
```css
.field label { font-family:var(--mono); font-size:10px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--ink-3); }
.field input, .field select { font-family:var(--sans); font-size:13.5px; padding:9px 11px;
  border:1px solid var(--rule-2); background:var(--paper); color:var(--ink);
  border-radius:7px; width:100%; }
.field input:focus, .field select:focus {
  border-color:var(--clay); box-shadow:0 0 0 3px var(--clay-soft); outline:none; }
```

---

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python + FastAPI | |
| DB | SQLite via SQLModel | ~10MB/year at this scale |
| Frontend | Jinja2 + HTMX | No build step, no npm |
| Styling | Plain CSS with tokens above | One `style.css` |
| Hosting | Fly.io free → Hetzner CX11 | Must be network-accessible for crews |
| PDF export | WeasyPrint | Phase 1 only; placeholder button in Phase 0 |

**No React. No npm.** Run with:
```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
`0.0.0.0` = reachable on local network immediately (crews on same WiFi).

---

## 4. Data Models

Derived from `WPC_System_Specification.md` and actual xlsx data.

### `Project` (core — maps to Munkák sheets)
```python
id: int                      # PK auto
created_at: datetime
updated_at: datetime

# Client (denormalized for Phase 0; normalize in Phase 2)
client_name: str
address: str | None
phone: str | None
email: str | None
invoice_type: enum["cég", "magánszemély"]

# Job metadata
status: enum["felmérendő", "lebeszélve", "betervezve", "folyamatban", "kész"]
job_type: enum["Terasz","Kerítés","Korlát","Falburkolat","Lépcső","Javítás/garancia","Vegyes"]
distributor: enum["Royal","Royal Buda","Royal Óbuda","Woopla","Guru","Global","Exotic","Márka-Mix","Saját","Egyéb"]
crew: enum["Laci","Jenő","Csaba","Dani","Alex","Nincs hozzárendelve"]
crew_confirmed: bool = False
phase: str | None            # "I. ütem", "II. ütem" etc.
priority: enum["Normal","Sürgős","Halasztható"] = "Normal"

# Dates
survey_date: date | None
ideal_start_date: date | None
planned_start_date: date | None
planned_work_days: int | None
actual_start_date: date | None
actual_end_date: date | None  # triggers warranty clock

# Flags
welding_required: bool = False
covered_area: bool = False
vat_invoice: bool = False

# Material stub (Phase 2: links to Planner project)
color: str | None
area_m2: float | None
planner_project_id: str | None  # Phase 2 hook — FK to Planner

notes: str | None
```

### `ProjectCost` (1:1)
```python
project_id: int  # FK
labor_fee: int = 0              # Munkadíj nettó Ft
travel_fee: int = 0             # Kiszállási díj
distributor_commission: int = 0 # Forgalmazói jutalék
materials_fee: int = 0          # Segédanyag díja
```

### `ProjectLogistics` (1:1)
```python
project_id: int  # FK
key_code: str | None           # Kulcskód / bejutás
power_access: str | None       # Áramvétel helye
arrival_time: str | None
parking: str | None
materials_to_bring: str | None # Zsolt viszi (szintezők, speciális csavarok)
special_requests: str | None
```

### Computed properties (Python, not DB columns)
```python
@property
def total_net(self):
    c = self.cost
    return c.labor_fee + c.travel_fee + c.distributor_commission + c.materials_fee

@property
def total_gross(self):
    return round(self.total_net * 1.27) if self.vat_invoice else self.total_net

@property
def warranty_expires(self):
    from datetime import timedelta
    return self.actual_end_date + timedelta(days=730) if self.actual_end_date else None
```

---

## 5. Routes & Views

### `GET /`  — Projekt lista

**Stat strip (4 cells, 2-column grid):**
- Összes projekt / Folyamatban / Betervezve / Havi bevétel nettó

**Filter pills:** Mind · Felmérendő · Lebeszélve · Betervezve · Folyamatban · Kész
**Search:** `hx-get="/" hx-trigger="keyup changed delay:300ms"` on client_name / address

**Table columns:**
Megrendelő / Helyszín | Típus | Csapat | Státusz | Tervezett kezdés | Munkadíj nettó | →

Row click: `hx-get="/projects/{id}/detail" hx-target="#detail-panel" hx-swap="innerHTML"`

### `GET /projects/{id}/detail` (HTMX partial)
Returns HTML fragment only — no base template.

**Sections:**
1. Projekt adatok — client, address, type, distributor, crew, phase, dates, flags
2. Díjbontás — cost table + nettó / bruttó total
3. Logisztika — key code, power, parking, materials to bring
4. Különleges kérések — notes + special_requests

**Sticky footer (3 buttons):**
- `PDF letöltés` → toast "Hamarosan elérhető" (Phase 1)
- `Kiosztási terv →` → toast if no planner_project_id; real link in Phase 2
- `Szerkesztés` → href to edit form

### `GET /projects/new` + `POST /projects/new`
Full-page form. 6 sections matching detail view. POST → save → redirect `/`

### `GET /projects/{id}/edit` + `POST /projects/{id}/edit`
Same form pre-filled. POST → save → redirect `/`

### `GET /projects/{id}/delete` + `POST /projects/{id}/delete`
Simple confirm page. POST → soft-delete (status = "törölt") → redirect `/`

---

## 6. File Structure

```
wpc_admin/
├── main.py                 # FastAPI, all routes
├── models.py               # SQLModel: Project, ProjectCost, ProjectLogistics
├── database.py             # engine, create_tables(), get_session()
├── seed.py                 # Seed real data from xlsx (run once)
├── requirements.txt
├── static/
│   └── style.css           # All CSS — tokens + layout + components
└── templates/
    ├── base.html           # Topbar + sidebar + main grid + detail panel slot
    ├── projects.html       # List view (extends base)
    ├── project_detail.html # HTMX partial (no base extension)
    ├── project_form.html   # New + edit form (extends base)
    └── confirm_delete.html # (extends base)
```

`requirements.txt`:
```
fastapi
uvicorn[standard]
sqlmodel
jinja2
python-multipart
```

---

## 7. Build Steps

Complete and test each step before moving on.

**Step 1 — Scaffold**
`models.py`, `database.py`, `main.py` (health check only), `requirements.txt`.
`uvicorn main:app --host 0.0.0.0 --port 8000 --reload` runs clean.

**Step 2 — Design system**
`static/style.css` with all tokens, layout shell, pills, buttons, form fields.
`base.html` renders topbar + sidebar + grid. Dark/light toggle works (JS, no reload).

**Step 3 — Project list**
`/` route with real DB query, stat strip, table, status badges.
Seed 8 projects manually for testing.

**Step 4 — HTMX detail panel**
Row click → detail panel injects. Close button clears panel. No page reload.

**Step 5 — New project form**
All fields in 6 sections. POST saves all 3 models. Redirect works.

**Step 6 — Edit + Delete**
Pre-filled edit form. Confirm delete. Soft-delete only.

**Step 7 — Search + filter**
Filter pills and search → HTMX table re-render. 300ms debounce on search.

**Step 8 — Real seed data**
`seed.py` parses Munkák 2025 + 2026 sheets from xlsx and imports them.

---

## 8. Planner Integration Hooks (Phase 2 prep — build stubs now)

### Sidebar nav (future merged state):
```html
<!-- base.html sidebar -->
<nav class="rail">
  <div class="rail__cap">Modulok</div>
  <a class="step {% if module=='admin' %}active{% endif %}" href="/">
    <div class="step__no">A</div>
    <div class="step__tx"><b>Projektek</b><span>Admin & ütemezés</span></div>
  </a>
  <a class="step {% if module=='planner' %}active{% endif %}" href="/planner">
    <div class="step__no">P</div>
    <div class="step__tx"><b>Kiosztások</b><span>Tervező & anyag</span></div>
  </a>
</nav>
```

### Detail panel "Kiosztási terv" button stub:
```html
{% if project.planner_project_id %}
  <a href="/planner/projects/{{ project.planner_project_id }}" class="btn ghost">
    Kiosztási terv →
  </a>
{% else %}
  <button class="btn ghost" onclick="toast('Nincs csatolva kiosztási terv')">
    Kiosztási terv →
  </button>
{% endif %}
```

---

## 9. Deployment

| Stage | Option | Cost |
|---|---|---|
| Dev | Local 0.0.0.0:8000 | Free |
| Prod v1 | Fly.io free tier | Free (sleeps after 15min idle — acceptable) |
| Prod v2 | Hetzner CX11 | €4/mo — recommended after Planner merge |

For Fly.io, SQLite must be on a mounted volume:
```toml
# fly.toml
[mounts]
  source = "wpc_data"
  destination = "/data"
```
Set `DATABASE_URL = "sqlite:////data/wpc.db"` via env var.

---

## 10. Model Usage

| Task | Model |
|---|---|
| All Phase 0 CRUD + HTMX + CSS | `claude-sonnet-4-5` |
| Cutting optimization algo (Phase 2) | `claude-opus-4-5` |
| Quick single-line fixes | `claude-haiku-4-5` |

**Pro subscription:** Sonnet handles all of Phase 0. Reserve Opus for Phase 2 layout engine.

---

## 11. Phase 2 Scope (out of scope now)

- Planner module merge into shared app (shared base.html, shared sidebar nav)
- `planner_project_id` becomes a real FK join
- Real PDF export: A3 layout plan + material list (WeasyPrint)
- Historical Google Sheets import
- Warranty tracking view
- Rain-day loss / crew utilization reporting

---

## 12. Starting Prompt for Claude Code

```
I'm building "WPC Projekt Adminisztrátor" — a web app for managing WPC terrace installation
projects (~80 jobs/year, 4 crews, Hungarian UI). It will later merge with a Planner module.

I've attached 3 files:
- wpc_admin_spec.md         — this spec, follow it exactly
- wpc-projekt-admin.html   — Admin UX reference (layout, sidebar, table, detail panel patterns)
- wpc_planner_mockup.html  — CANONICAL design tokens (colors, fonts, CSS variables — use these)

CRITICAL: Design tokens come from wpc_planner_mockup.html. UX/layout patterns come from
wpc-projekt-admin.html. Do not mix them up.

Tech: FastAPI + SQLModel (SQLite) + Jinja2 + HTMX. No React, no npm, no build step.
Host on 0.0.0.0:8000.

Start with Step 1 only: create models.py, database.py, main.py (health check route),
requirements.txt. Confirm uvicorn starts clean. Stop there.
```
