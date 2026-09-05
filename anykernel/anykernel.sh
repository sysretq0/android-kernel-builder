### AnyKernel3 Ramdisk Mod Script
## sysretq0/android-kernel-builder (generic GKI installer)
## Backend (tools/, META-INF/): AnyKernel3 by osm0sis @ xda-developers, pristine

### AnyKernel setup
# global properties
# NOTE: @REV@ is stamped per-branch by tools/pack-anykernel.sh at pack time.
properties() { '
kernel.string=sysretq0 GKI @REV@
do.devicecheck=0
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=
device.name2=
device.name3=
device.name4=
device.name5=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; } # end properties


### AnyKernel install
# GKI generic: no device/version checks (do.devicecheck=0), no ramdisk mods,
# no modules. Kernel blob (Image.lz4 / Image.gz / Image) is swapped into the
# stock boot image, everything else is preserved.

# boot shell variables
BLOCK=auto;
IS_SLOT_DEVICE=auto;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

# import functions/variables and setup patching - see for reference (DO NOT REMOVE)
. tools/ak3-core.sh;

# boot install
ui_print " ";
ui_print "sysretq0 GKI: replacing kernel, keeping stock ramdisk...";
split_boot; # skip ramdisk unpack (no ramdisk mods; switch to dump_boot if you add any)

flash_boot; # skip repack (pairs with split_boot; switch to write_boot with dump_boot)
## end boot install
