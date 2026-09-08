# Upstream detection, mirror sync, pin refreshes

## detect-upstream (every 12h + dispatch)

1. `tools/check-upstream.py <variant>` compares the 8 mirror `-lts`
   tips against `kernel/common` live, by direct SHA comparison — no
   state file to rot.
2. On change, `tools/mirror-upstream.py --push` fast-forwards the
   changed refs via the GitHub API (fast-forward only, never forced;
   needs `KERNEL_MIRROR_TOKEN`). Dry-run by default; a rejected update
   fails loud instead of rewriting history.
3. Then dispatches the plain fleet (`destination=artifact`).

Builds consume the mirror through `manifests/vendor-common.xml.template`
(`kernel/common` swapped to the mirror at the matrix branch), so a
fresh mirror means fresh builds with no other step.

## refresh-pins (daily 06:00 UTC + dispatch)

`tools/refresh-pins.py --write` bumps module pins in both variants
directly to `main` (no PR), then commits and pushes. Format-preserving:
JSON shape and comments survive a bump.
