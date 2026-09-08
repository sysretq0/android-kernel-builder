# Modules

`modules/<name>/` holds one integration: vendored patches (if any),
`patches.json` (branch → patch files), shared `tools/apply-patches.py`
(dry-run + fuzz cap + marker + `.rej` sweep, branch-absent clean skip),
and a thin `setup.sh` for one-offs. `modules/manifest.json` is the
registry:

- `order` — pipeline order, the only thing `integrate.py` iterates.
- `keys` — module → variant/evidence short key.
- `labels` — display names for every evidence key readers accept.
  A version key without a label fails closed in both readers — add the
  label with the feature, never in the reader.

Membership in `order` claims pipeline participation. Pure evidence
(toolchains — see `docs/clang.md`) registers in `labels` only.

## Evidence, not status

Each setup writes `.<key>-version` into the work dir;
`collect-versions.py` copies them to `versions-<branch>/<key>.txt`.
Presence means built; absence means off. Release body, Telegram, and the
installer checklist all render from these files — no hand-written status
anywhere, so a gated tree cannot lie about what it shipped.
