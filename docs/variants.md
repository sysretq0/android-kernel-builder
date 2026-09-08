# Variants

`variants/<name>.json` is the whole fleet definition. Two variants exist:
`plain` and `susfs`. The workflow's branch choices duplicate the branch
list (GitHub requires static choices); JSON remains truth and the matrix
fails loud on drift.

## Shape

```json
{
  "defaults": {
    "our_revision": "lts",
    "fragments": true,
    "ksu":      { "branch": "dev", "tag": "", "commit": "<sha>" },
    "nomount":  { "branch": "dev", "tag": "", "commit": "<sha>" },
    "guard":    { "branch": "main", "tag": "", "commit": "<sha>" },
    "bbrv3": true,
    "ntsync": true,
    "mgate": false
  },
  "branches": [
    { "branch": "android12-5.10-lts", "manifest": "common-android12-5.10-lts",
      "kind": "build_sh", "extra": ["usb-serial"] },
    ...
  ]
}
```

- Module values are `true` / `false` / pin triple. `commit > tag >
  branch` precedence; `false` is off. There are no per-module dispatch
  inputs on purpose: run-time rerouting is a variant edit, so every
  built pin is reviewed in JSON.
- A branch record may replace a module's **whole triple** for that tree
  only (per-tree divergence); partial triples are replaced whole, never
  merged.
- `extra` assigns version-specific fragments from the single-copy pool
  (see `docs/fragments.md`); JSON stays small because the pool files
  carry the knowledge.
- `plain` vs `susfs` differ today in KSU ref (`dev` vs `dev-susfs`)
  and `susfs: true`. ModuleGate is `false` in both: it does not boot
  (see `docs/RISK.md`) and stays off until further notice.

## Dispatch

`variant`, `destination`, `branch` select from this file; `clang` and
`cleanup` are run-level switches, not fleet definition. Release is
decided on dispatch, not by variant — and every release sends Telegram.
