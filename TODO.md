# TODO

## Renderer improvements

- **Capitalize sentence-initial matchup phrases**: The renderer currently outputs lowercase matchup text like "righty against righty." When this is appended to a batter intro line it reads fine, but when it stands alone it should be capitalized ("Righty against righty."). Rather than lowercasing the target files to match, the renderer should capitalize the first letter of any phrase that begins a sentence. This applies to matchup text in `renderers/narrative/renderer.py` around line 637.
