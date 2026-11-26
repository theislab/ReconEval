from pathlib import Path

import zarr


def fix_multiciliated_key(zarr_dir):
    """Rename LuCA expression groups and synchronize their name metadata."""
    root = Path(zarr_dir)
    old, new = "multi_ciliated_epithelial", "multiciliated_epithelial"
    for p in sorted(root.iterdir()):
        if p.name.startswith(old):
            dst = p.with_name(p.name.replace(old, new, 1))
            p.rename(dst)
            print(f"renamed: {p.name} -> {dst.name}")

    store = zarr.open_group(zarr_dir, mode='r+')
    store.attrs['combinations'] = sorted(store.group_keys())


def post_proc(zarr_dir, cfg):
    fix_multiciliated_key(zarr_dir)
