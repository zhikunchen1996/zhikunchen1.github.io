# Zhikun Chen — Academic Website

Source for [zhikunchen.com](https://zhikunchen.com/).

The site is built with Jekyll and the open-source [al-folio](https://github.com/alshedivat/al-folio) academic template. It includes a concise research profile, a Google Scholar–derived publication list, and a web CV.

## Local preview

```bash
bundle install
bundle exec jekyll serve
```

Then open `http://localhost:4000/`.

Pushes to `main` are built and deployed through GitHub Actions.

## Citation updates

Google Scholar citations refresh monthly on day 1 at 00:17 UTC. The updater also runs when its code or dependencies change on `main`, and can be run manually from GitHub Actions. Successful updates are published through the Pages deployment workflow; failed or empty fetches preserve existing data and fail visibly.

Run the network-free regression tests with `python -m unittest discover -s tests -v`. CI additionally verifies the real `scholarly` dependency import.
