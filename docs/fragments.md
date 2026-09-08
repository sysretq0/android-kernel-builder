# Fragments: portable Kconfig

Pure-Kconfig additions over stock `gki_defconfig`. Anything needing
source (KSU, SuSFS, BBRv3, NoMount, Guard, NTSync backport, ModuleGate)
is setup-owned under `.fragments/` so symbol and source cannot disagree —
repo fragments never carry source-backed symbols.

## Layout

- `fragments/common/` — every tree: `bbr`, `cake`, `cifs`, `ipset`,
  `metamodule`, `snd-aloop`, `udf`, `usb-printer`, `usb-rndis`
  (`example.config.example` is documentation, not staged).
- `fragments/version-specific/` — single-copy pool, assigned per branch
  via the variant `extra` list: `usb-serial` (5.10 only), `ntfs3`
  (5.15+), `zswap` (6.6 only). A listed-but-missing file fails hard.

## Rules

One symbol per line: `CONFIG_X=y|m|value`, or `# CONFIG_X is not set`
(which is a real Kconfig statement — the staging scripts preserve it;
dropping it once re-broke Kleaf staging fleet-wide). Full-line comments
and blanks are accepted but stripped at stage time.

## Staging (`tools/stage_fragments.py`)

- Validates every line, failing as `file:line`.
- Replaces symbols already present before appending (no duplicates), then
  appends the merged block.
- Never touches the committed defconfig: `build_sh` merges
  `work/modular.fragment` at `POST_DEFCONFIG_CMDS` time via a generated
  `build.config.portable` (keeps the `savedefconfig` byte-match check
  green); `kleaf` passes the staged file as `--defconfig_fragment`.

Portability notes learned the hard way: stock `=m` + module-list
declared means "never flip to `=y`" (usb-serial lives on 5.10 only for
this reason); tristate children can never exceed a `=m` parent
(`CAN=m` caps everything under it).
