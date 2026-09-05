# AnyKernel3 flashable zip

Device-generic GKI installer, built from this template at pack time by
`tools/pack-anykernel.sh` (see workflow `Pack AnyKernel3 zip` step).

## Layout

```text
anykernel/
  META-INF/  pristine AK3 backend (DO NOT CHANGE per upstream header)
  tools/     pristine AK3 backend: ak3-core.sh, busybox, magiskboot… (DO NOT CHANGE)
  anykernel.sh   OUR installer: generic GKI (no device check, kernel-only swap)
  banner         OUR ui_print banner (shown first at flash time)
  version        generated at pack time: <rev> + build date (not committed)
```

Upstream: https://github.com/osm0sis/AnyKernel3 — license in
`LICENSE.upstream`, attribution line kept in the backend (`update-binary`
prints `AnyKernel3 by osm0sis @ xda-developers`).

## Customization points (frontend only)

- `banner` — free-form lines, printed first.
- `anykernel.sh` `properties()`: `kernel.string` (pack script stamps `@REV@`
  with the branch/rev, e.g. `android14-6.1-stable`), checks on/off.
- `version` — written per build; add more lines in `pack-anykernel.sh` if
  you want e.g. fragment list or defconfig hash shown on screen.
- Install body prints its own `ui_print` lines (currently: kernel-only swap
  notice). Ramdisk/module support = switch `split_boot`→`dump_boot`,
  `flash_boot`→`write_boot` and flip `do.modules`.

## Behavior

- `BLOCK=auto` / `IS_SLOT_DEVICE=auto`: finds `boot` (`init_boot` first on
  hdr v4 layouts) + slot automatically.
- Kernel image (`Image.lz4` preferred, else `Image.gz`, else `Image`) is
  detected by filename and swapped into the stock boot image; ramdisk, dtb,
  cmdline preserved. `PATCH_VBMETA_FLAG=auto` handles vbmeta.
- No device allowlist (`do.devicecheck=0`): one zip flashes any GKI device
  with a matching KMI.
