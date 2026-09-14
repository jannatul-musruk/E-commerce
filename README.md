# Nokshi — a Django e-commerce project

A working storefront for a Bangladeshi handicraft shop: pottery, jamdani, jute,
leather and brass. Built with Django 5.2 and SQLite.

---

## Run it

```bash
cd ecommerce

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data      # fills the shop with sample products and orders
python manage.py runserver
```

Open http://127.0.0.1:8000/

| Role     | Username | Password    |
| -------- | -------- | ----------- |
| Shopper  | `rumi`   | `nokshi1234` |
| Shopper  | `nabila` | `nokshi1234` |
| Admin    | `admin`  | `admin1234` |

The admin lives at http://127.0.0.1:8000/admin/

Run the tests with `python manage.py test`.

---

## What the site does

**Catalogue** — home page with featured and latest items, a shop page with
keyword search, filtering by craft and by workshop, four sort orders and
pagination, and a product page with variants, stock, reviews and related items.

**Accounts** — signup, login, logout and a profile page. Passwords are hashed by
Django. A `Customer` profile is created automatically for every new user through
a `post_save` signal.

**Bag** — add, change quantity, remove. Stock is checked before anything is
added, so you cannot order more than exists.

**Checkout** — delivery address form with phone validation, four payment methods
(cash on delivery, bKash, Nagad, card), delivery charged at ৳60 inside Dhaka and
৳120 elsewhere. Placing an order runs inside a database transaction: it creates
the order and its items, writes the payment and shipping rows, reduces stock and
empties the bag. If any step fails, nothing is saved.

**Orders** — order history, order detail, cancel (which puts the stock back), and
a return request on delivered items.

**Extras** — wishlist, product reviews with a one-review-per-customer rule,
notifications when an order changes state, a newsletter subscription toggle and
an activity log.

**Admin** — every model registered with useful columns, filters and search.
Orders have inline items, payment and address, plus bulk actions to mark orders
confirmed, shipped or delivered. Each action also writes a notification to the
customer.

---

## Models

`CustomUser` · `Customer` · `Category` · `Brand` · `Product` · `ProductVariant` ·
`Cart` · `CartItem` · `Order` · `OrderItem` · `Payment` · `ShippingAddress` ·
`Wishlist` · `Review` · `ReturnRequest` · `Subscription` · `Notification` ·
`ActivityLog`

---

## What changed from the first version

| Problem in the old code | What it does now |
| --- | --- |
| `CharField(255)` set `verbose_name`, not `max_length`, so the columns had no length limit and would break on MySQL or Postgres | every field declares `max_length` explicitly |
| `CustomUser` was a plain `models.Model` storing passwords in plain text, with no login or sessions | extends `AbstractUser`; passwords are hashed, login/logout and permissions come free |
| `/registration/` crashed with `NoReverseMatch` because `{% url 'login' %}` had no matching route | full auth routes wired up, signup uses a real `ModelForm` |
| `CartItem.__str__` used `self.quantity`, `Order.__str__` used `self.status`, `ActivityLog.__str__` used `self.timestamp` — none of those fields existed | all `__str__` methods match real fields; `ShippingAddress.__str__` now returns a value |
| `CartItem.quantity` was a `CharField`; `Payment.amount` was an `IntegerField` | `PositiveIntegerField` and `DecimalField` |
| Foreign keys named `Customer_ID`, producing `obj.Customer_ID.CustomUser_ID.userName` | snake_case names and related names: `obj.customer.user.username` |
| `Subscription` primary key was called `StopIteration_ID` | renamed |
| No media settings, so product images could not be uploaded or served | `MEDIA_URL` and `MEDIA_ROOT` configured and served in development |
| `SECRET_KEY` hardcoded, `.gitignore` saved as UTF-16 so git ignored nothing, virtualenv and a whole XAMPP install committed | key read from the environment, UTF-8 `.gitignore` that excludes `.venv`, `db.sqlite3`, `media/` and `xampp/` |
| No forms, no tests | `forms.py` with six forms, six tests covering signup, hashing, the bag and checkout |

---

## Where to take it next

- Product images: upload real photos in the admin. The seeded ones are generated
  patterns standing in for photography.
- Coupons and discounts on `Order`.
- A real payment gateway (SSLCommerz or bKash checkout) in place of the demo
  `Payment` record.
- Order confirmation email through Django's email backend.
- Move to PostgreSQL before deploying, and set `DEBUG=False` with a real
  `DJANGO_SECRET_KEY`.
