# Skilljar exercises: Markdown to GitHub Pages

## Goal

Camunda Academy exercises are written in Hugo-style Markdown. We want to show them inside Skilljar lessons with collapsible solution blocks. Skilljar lessons can't render Hugo shortcodes, and a Google Doc embed doesn't work (collapsible headings are an editor-only feature). So we convert the Markdown to static HTML, host it on GitHub Pages, and embed the page in Skilljar with an `<iframe>`. Content updates on every merge to `main`, with no manual pasting.

## Current state

- `build.py` converts `content/*.md` to `site/*.html` (plus `site/index.html`), using `template.html`.  
  - Front matter: only `title` is used.  
  - `{{< snippet Name >}} ... {{< /snippet >}}` becomes a closed `<details class="snippet">` block with highlighted, re-indented code. The code language comes from the second extension of the file name (`exercise5-java.java.md` gives `java`).  
  - Normal Markdown is rendered with python-markdown (`fenced_code`, `tables`, `sane_lists`).  
- `.github/workflows/pages.yml` builds and deploys to GitHub Pages on pushes to `main` that touch `content/`, `build.py` or `template.html`.  
- `content/exercise5-java.java.md` is a real exercise used as the test input.  
- `site/` is generated output. Don't commit it (`.gitignore`).  
- Verified locally: the HTML output looks correct. Not yet verified: the GitHub Pages deploy and the rendering inside Skilljar.
- I've created a public repository that is empty at the moment: https://github.com/camunda-academy/skilljar-easy-html-rendering.git
- I've configured it with Settings \> Pages and set Source to GitHub Actions. 

## Known issues in the sample source

- The numbered steps are broken in the source itself, because code blocks sit outside the list items. Any renderer restarts the numbering. Fix the source by indenting code blocks under their list item and numbering steps consecutively. Don't hack the converter around this.  
- Snippet bodies are not in code fences. The converter treats everything inside the shortcode as code.

## Constraints

- This is the official md-html converter https://github.com/camunda-academy/academy-md-html. `build.py` is a throwaway proof of concept, so keep changes to it small and don't polish it.  
- The GitHub Pages site can be public.  
- Skilljar's iframe embed is untested. Skilljar might strip HTML, block the frame, or need a fixed iframe height.

## Next steps

1. Create a git project and link it to the newly created repository and push this folder.  
2. Run the "Publish exercises" workflow if the first run failed.  
3. Confirm the page loads at `https://<user>.github.io/<repo>/exercise5-java.html`.  
4. Embed it in a Skilljar lesson with an iframe and check three things: the snippets are closed by default, they expand on click, and the iframe height is adequate.  
5. Report what works and what doesn't, then decide whether to adopt the colleagues' converter or extend `build.py`.

## Working rules

- Ask before pushing, creating repos or changing GitHub settings.  
- Never put API keys or secrets in this repo.