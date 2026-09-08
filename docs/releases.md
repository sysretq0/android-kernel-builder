# Releases, Telegram, AnyKernel3

Testing builds stay as workflow artifacts (`destination=artifact`,
per-branch `anykernel-*` + `versions-*` sets, never merged).
`destination=release` publishes one GitHub release plus a Telegram post
from a single renderer: `tools/render-release.py`, fed only by version
evidence and manifest labels.

## Per-branch artifacts

- `anykernel-<rev>.zip` — raw `Image` (compressed images panic at
  decompress), `BLOCK=boot`, `kernel.config`, extracted `ikconfig`,
  flash-time UI (identity box, device/slot line, per-line feature
  checklist outside the box). Filename carries the kernel version
  (`anykernel-android12-5.10-269.zip`).
- `versions-<branch>/` — `rev`, `branch`, `version`, plus one file per
  built integration (`ksu`, `susfs`, `clang`, …).

## Release job

`publish-release.py`: renders notes + Telegram table, creates the
release with all zips, links the matching KernelSU-Next manager APK
(resolved per-release from the most common KSU SHA so it never rots),
posts to Telegram (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`), and
optionally forwards to a group/topic (`forward` input, default off).
`docs/RELEASE_NOTES_EXTRA.txt` footnotes append to both body and post
(experimental notices live there, not in code).

The table shows per-branch integration state (version-only, no SHA
noise), the toolchain section lists override compilers, and Telegram
gets a compact monospace form plus `+extras` markers.
