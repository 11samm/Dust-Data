# Getty Museum Collection fixtures

This folder contains 26 real Getty Linked.Art object records: 25 returned by the stable URI-ordered SPARQL query in `manifest.json`, plus Van Gogh's *Irises*, retained as a known example with embedded AAT material IDs. The fixture set exercises records with and without images; exact, circa, range, decade, generation, century, and multi-century dates; generic, material-only, and specific media; and named, unknown, or missing attribution and description evidence.

The capture script preserves fields read by the adapter and omits unrelated long text. Markdown object descriptions are retained only when Getty marks them CC BY 4.0 or CC0. The fixtures are saved inputs; tests do not contact Getty. To refresh them, run `python scripts/getty_sample.py` from the repository root. Refreshing can change the cohort if Getty adds or updates collection records, so review the updated manifest and expected bands in `tests/test_getty_phase2.py`.

Source: [Getty Museum Collection API documentation](https://data.getty.edu/museum/collection/docs/). This URI-ordered sample provides repeatable parser and scoring coverage; it is not a representative sample of the full collection.
