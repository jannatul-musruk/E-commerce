# Putting Nokshi online

Two separate jobs. Do them in order.

- **Part A — GitHub:** stores the code so it can be shared and marked.
- **Part B — PythonAnywhere:** runs the site so it has a link anyone can open.

Budget about an hour for the first time. Do this a day before the demo, not an
hour before.

---

# Part A — Push the code to GitHub

### A1. Check what git will send

Open a terminal in `E-commerce` (the folder that holds `.git`):

```bash
git status
```

If `.env/` or `xampp/` show up in the list, stop and fix `.gitignore` first —
they must not be committed.

### A2. Force-add the database and images

`.gitignore` blocks `db.sqlite3` and `media/` on purpose, because a real project
never commits those. For a class demo you want them, so the teacher can clone
and see a full shop:

```bash
git add -f db.sqlite3 media/
git add .
git commit -m "Complete e-commerce project: storefront, cart, checkout, admin"
```

### A3. Push

If the repo already has a GitHub remote:

```bash
git push
```

If not, make an empty repo on github.com (no README, no .gitignore), then:

```bash
git remote add origin https://github.com/YOURNAME/E-commerce.git
git branch -M main
git push -u origin main
```

Open the repo in a browser and check `ecommerce/products/models.py` is there.

---

# Part B — Host the site on PythonAnywhere

Free tier, no card needed. You get `yourname.pythonanywhere.com`.

### B1. Make the account

Sign up at pythonanywhere.com, pick **Beginner (free)**. The username you choose
becomes part of your URL, so pick something you would not mind a teacher seeing.

### B2. Pull the code in

**Consoles → Bash**, then:

```bash
git clone https://github.com/YOURNAME/E-commerce.git
cd E-commerce/ecommerce
```

Check that `manage.py` is there with `ls`.

### B3. Make a virtualenv and install

```bash
mkvirtualenv nokshi --python=/usr/bin/python3.10
pip install -r requirements.txt
```

The prompt turns into `(nokshi)`. Write down the path it prints — usually
`/home/YOURNAME/.virtualenvs/nokshi`.

### B4. Prepare the database and static files

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

If your `db.sqlite3` came through git, the shop already has products. If not,
run `python manage.py seed_data` and make a fresh admin account with
`python manage.py createsuperuser`.

### B5. Create the web app

**Web → Add a new web app → Manual configuration → Python 3.10.**
Do not pick the Django option; manual gives you control.

Then on the Web tab fill in:

| Field | Value |
| --- | --- |
| Source code | `/home/YOURNAME/E-commerce/ecommerce` |
| Working directory | `/home/YOURNAME/E-commerce/ecommerce` |
| Virtualenv | `/home/YOURNAME/.virtualenvs/nokshi` |

### B6. Edit the WSGI file

On the Web tab, click the **WSGI configuration file** link. Delete everything in
it and paste this, changing `YOURNAME`:

```python
import os
import sys

path = '/home/YOURNAME/E-commerce/ecommerce'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'ecommerce.settings'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_SECRET_KEY'] = 'paste-a-long-random-string-here'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'YOURNAME.pythonanywhere.com'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

For the secret key, run this in a Bash console and paste the output:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### B7. Map the static and media URLs

Still on the Web tab, under **Static files**, add two rows:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/YOURNAME/E-commerce/ecommerce/staticfiles` |
| `/media/` | `/home/YOURNAME/E-commerce/ecommerce/media` |

Skip this and the site loads with no styling at all — just black text on white.
That is the single most common mistake.

### B8. Reload and open

Hit the big green **Reload** button, then open
`https://YOURNAME.pythonanywhere.com`.

---

## When something breaks

Every error is written to the log files linked at the top of the Web tab. Open
**Error log** and read the last few lines — the real cause is almost always
there.

| What you see | What to do |
| --- | --- |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` in the WSGI file does not match your URL |
| Site works but looks unstyled | Static files mapping in B7 is wrong, or you skipped `collectstatic` |
| `ModuleNotFoundError: django` | Virtualenv path in B5 is wrong |
| Product images missing | The `/media/` mapping is missing, or `media/` never reached GitHub |
| `no such table` | You did not run `migrate` |
| Changes not showing | You forgot to press **Reload** |

After any code change: `git push` on your PC, then on PythonAnywhere run
`git pull` in the console and press **Reload**.

---

## Before the demo

- Open the live link on your phone, on mobile data. If it works there, it works
  anywhere.
- Log in as a customer and place one order start to finish, so you know the flow
  cold.
- Open `/admin/` and mark that order as shipped, to show the two sides connect.
- Keep the project running on your laptop as a backup. Campus wifi fails.
