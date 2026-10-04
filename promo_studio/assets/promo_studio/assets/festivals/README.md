# Festival artwork

Only names listed in `promo_studio/festival_assets.py` may resolve to artwork.
Artwork must exist locally under this directory (or under the directory named
by `SIDDHANTA_FESTIVAL_ASSET_DIR`). Remote URLs and upstream `file_name` values
are never fetched or trusted by the renderer.

Use the allowlist to map each festival name to the **correct** local asset;
do not reuse a visually similar festival image merely because the upstream
record points at it.
