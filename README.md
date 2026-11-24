# youngkwangk.github.io

Home pages, privacy policies and terms of service for personal Google Cloud OAuth apps.
Authorized domain for every project: `youngkwangk.github.io`

## Adding an app
1. Copy `_template/` to a new folder, such as `my-app/`.
2. Replace the ALL_CAPS placeholders in all three files (`index.html`, `privacy.html`, `terms.html`) with the app's name, scopes and data use.
3. Add a link to the app in the root `index.html`, then push.
4. In that project's **Google Auth Platform → Branding**, set:
   - Home page: `https://youngkwangk.github.io/my-app/`
   - Privacy policy: `https://youngkwangk.github.io/my-app/privacy.html`
   - Terms of service: `https://youngkwangk.github.io/my-app/terms.html`
   - Authorized domain: `youngkwangk.github.io`

## Checking the site

Run `python3 -m unittest tests/test_site.py` to check page structure, links and required app pages. The Google site verification file is checked as a plain-text token rather than a full HTML page.
