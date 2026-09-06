# Handmade Craft Decor — Multi-Vendor Platform (MVC: Flask + MySQL)

A multi-tenant platform where **each user (a home-based handmade business)
gets their own online store** — products, categories, photos, story, about
us, contact info, all fully customisable — reachable at a unique shareable
link (`/store/<their-slug>`). Built in **MVC (Model–View–Controller)** style.

- **Backend (Model + Controller):** Python (Flask)
- **Database:** MySQL, with numbered migration files (SQLite also supported for quick demos)
- **Frontend (View):** HTML (Jinja2 templates) + CSS + JS — fully responsive

---

## 1. How the platform works

There are **three separate roles**:

| Role | Logs in at | What they do |
|---|---|---|
| **Admin** (you / platform owner) | `/admin/login` | Creates & manages vendor (user) accounts, sees platform-wide stats. Does **not** manage products directly. |
| **Vendor** (a "user" — one handmade business) | `/vendor/login` | Manages **their own** categories, products, photos, orders, custom orders, messages, and store settings (story / about / contact / social links / logo). |
| **Customer** (the public) | No login | Visits a vendor's store at `/store/<vendor-slug>/...`, browses products, places orders. Never sees any other vendor's data. |

- The **"Handmade Craft Decor"** branding only appears on the Admin and
  Vendor dashboards (and the marketing landing page at `/`). Each vendor's
  public storefront shows **only that vendor's own business name/logo** —
  never the platform name — so it looks like their own independent website.
- Every vendor gets a unique link like `yourdomain.com/store/priyas-crafts`
  which they can put in their Instagram/Facebook bio or share on WhatsApp.
  Customers who open that link only ever see that one vendor's store.
- New vendor accounts are created by the **Admin** (there's no public
  self-signup form) — go to `/admin/login` → **Vendors (Users)** → **+ Add Vendor**.

---

## 2. Project Structure (MVC)

```
handmade_creations_mvc/
│
├── backend/                          # ---- Model + Controller ----
│   ├── __init__.py                    # Flask app factory, registers all blueprints
│   ├── config.py                       # Reads settings from .env
│   ├── extensions.py                   # db, login_manager instances
│   ├── models/                         # MODEL layer (one file per table)
│   │   ├── admin.py                     # Platform super-admin
│   │   ├── vendor.py                    # A "user" / business owner + their store settings
│   │   ├── category.py                  # Scoped per vendor
│   │   ├── product.py                   # Scoped per vendor
│   │   ├── order.py                     # Scoped per vendor
│   │   ├── custom_order.py              # Scoped per vendor
│   │   └── contact_message.py           # Scoped per vendor
│   ├── controllers/                    # CONTROLLER layer (routes/logic)
│   │   ├── landing_controller.py         # "/" — platform marketing page
│   │   ├── admin_controller.py           # "/admin/*" — vendor management + platform dashboard
│   │   ├── vendor_controller.py          # "/vendor/*" — a vendor's own dashboard
│   │   └── public_controller.py          # "/store/<slug>/*" — one vendor's public storefront
│   └── utils/
│       ├── decorators.py                # @admin_required / @vendor_required
│       └── helpers.py                    # slugify, unique_slug, save_vendor_upload
│
├── frontend/                          # ---- View ----
│   ├── templates/
│   │   ├── landing.html                 # Platform homepage ("/")
│   │   ├── base.html                     # Shared header/footer for a vendor's storefront
│   │   ├── home.html / products.html / product_detail.html / order_form.html /
│   │   │   custom_order.html / my_orders.html / contact.html / about.html
│   │   ├── admin/                        # Admin panel (login, dashboard, vendor list/form)
│   │   └── vendor/                       # Vendor dashboard (login, dashboard, products,
│   │                                       categories, orders, custom orders, messages, settings)
│   └── static/
│       ├── css/style.css                 # Fully responsive styling
│       ├── js/script.js                   # Hamburger menu + copy-link logic
│       └── uploads/<vendor-slug>/...       # Each vendor's images live in their own folder
│
├── database/
│   ├── migrations/                     # Numbered MySQL migrations (001..007)
│   ├── migrate.py                       # Runs pending migrations, tracks them
│   └── seed.py                          # Creates admin + one demo vendor + sample data
│
├── .env
├── requirements.txt
└── run.py                               # Entry point — `python run.py`
```

---

## 3. Step-by-Step: VS Code Terminal Setup

### Step 1 — Open the project
Unzip, open the folder in VS Code, open a terminal (`` Ctrl+` ``).

### Step 2 — Create a virtual environment
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Set up your database

**Option A — Quick demo with SQLite (no MySQL needed, default):**
`.env` already has `USE_SQLITE=1`, so just run:
```bash
python database/seed.py
```

**Option B — MySQL (for real deployment):**
1. `CREATE DATABASE handmade_creations;`
2. In `.env`, set `USE_SQLITE=0` and fill in your MySQL credentials.
3. ```bash
   python database/migrate.py
   python database/seed.py
   ```

### Step 5 — Run the website
```bash
python run.py
```
Open `http://127.0.0.1:5000` — this is the platform landing page.

### Step 6 — Log in

**Admin** (manage vendors): `http://127.0.0.1:5000/admin/login`
```
Username: admin
Password: admin123
```

**Demo Vendor** (manage a store): `http://127.0.0.1:5000/vendor/login`
```
Email: kaku@example.com
Password: vendor123
Store link: http://127.0.0.1:5000/store/kakus-woolen-decor
```

**Change both passwords before real use.**

### Step 7 — Create a new vendor (a new "user")
1. Log in as Admin → **Vendors (Users)** → **+ Add Vendor**.
2. Fill in business name, owner name, login email/password (and, optionally,
   a custom store link — otherwise one is generated automatically).
3. Give those login details to the business owner. They log in at
   `/vendor/login`, add their categories/products/photos, fill in their
   story/about/contact under **Store Settings**, then copy their store link
   from the dashboard and share it on Instagram/Facebook/WhatsApp.

### Step 8 — Adding future migrations
```
database/migrations/008_add_something.sql
```
```bash
python database/migrate.py
```

---

## 4. Data isolation between vendors
Every `Category`, `Product`, `Order`, `CustomOrder` and `ContactMessage` row
carries a `vendor_id`. Every query in `vendor_controller.py` and
`public_controller.py` filters by the current vendor, so:
- A vendor can only ever see/edit their own products and orders.
- A customer visiting `/store/vendor-a` never sees `/store/vendor-b`'s data.
- Uploaded images are saved under `frontend/static/uploads/<vendor-slug>/`
  so filenames never collide between vendors.

## 5. Mobile Responsiveness
Same responsive hamburger-menu system as before, now used on the landing
page, both dashboards, and every vendor's storefront.

## 6. WhatsApp Ordering
Each vendor sets their own WhatsApp number in **Store Settings** — the
"Order on WhatsApp" button on their product pages uses that number.

## 7. Notes
- Passwords are hashed with Werkzeug's `generate_password_hash`.
- `.env` holds secrets/config and is git-ignored.
- No payment gateway is included by design — orders are placed on-site or
  via WhatsApp, and payment/delivery is handled manually by each vendor.
- Admin and Vendor share one Flask-Login session but are kept completely
  separate via a prefixed user id (`admin:<id>` / `vendor:<id>`) and two
  independent `@admin_required` / `@vendor_required` decorators.
