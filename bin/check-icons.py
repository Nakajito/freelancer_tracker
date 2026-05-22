#!/usr/bin/env python3
"""
Check that all material-symbols-outlined icons used in templates exist in the
local font subset. Run after adding new icons or updating templates.

Usage:
    python bin/check-icons.py              # check only
    python bin/check-icons.py --patch      # check + patch missing icons (requires full font)
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FONT_PATH = ROOT / "static/fonts/material-symbols"
TEMPLATES_DIR = ROOT / "templates"


def get_icons_from_templates() -> set[str]:
    result = subprocess.run(
        [
            "grep",
            "-roh",
            r'material-symbols-outlined[^"]*">\([^<]*\)<',
            str(TEMPLATES_DIR),
        ],
        capture_output=True,
        text=True,
    )
    icons = set()
    for line in result.stdout.splitlines():
        m = re.search(r'">([a-z_]+)<', line)
        if m:
            icons.add(m.group(1))
    return icons


def get_icons_from_font(font_path: Path) -> set[str]:
    from fontTools.ttLib import TTFont

    f = TTFont(str(font_path))
    gsub = f["GSUB"].table
    found = set()
    for lookup in gsub.LookupList.Lookup:
        for sub in lookup.SubTable:
            if hasattr(sub, "ExtSubTable"):
                ext = sub.ExtSubTable
                if ext.LookupType == 4 and hasattr(ext, "ligatures"):
                    for g, ligs in ext.ligatures.items():
                        for lig in ligs:
                            name = g + "".join(
                                c if c != "underscore" else "_" for c in lig.Component
                            )
                            found.add(name)
    return found


def find_current_font() -> Path | None:
    fonts = sorted(
        FONT_PATH.glob("material-symbols-outlined-subset.v*.woff2"), reverse=True
    )
    return fonts[0] if fonts else None


def patch_font(missing: set[str], current_font: Path, full_font_path: Path) -> Path:
    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables.otTables import Ligature
    import copy

    existing = TTFont(str(current_font))
    full = TTFont(str(full_font_path))

    # Find glyph names in full font for missing icons
    full_gsub = full["GSUB"].table
    full_icon_to_glyph: dict[str, tuple[str, list[str]]] = {}
    for lookup in full_gsub.LookupList.Lookup:
        for sub in lookup.SubTable:
            if hasattr(sub, "ExtSubTable"):
                ext = sub.ExtSubTable
                if ext.LookupType == 4 and hasattr(ext, "ligatures"):
                    for g, ligs in ext.ligatures.items():
                        for lig in ligs:
                            name = g + "".join(
                                c if c != "underscore" else "_" for c in lig.Component
                            )
                            if name in missing:
                                full_icon_to_glyph[name] = (
                                    lig.LigGlyph,
                                    [g] + lig.Component,
                                )

    gsub = existing["GSUB"].table
    lookup = gsub.LookupList.Lookup[0]
    glyph_order = list(existing.getGlyphOrder())

    for icon_name, (glyph_name, components) in full_icon_to_glyph.items():
        first_char = components[0]
        rest = components[1:]

        # Add glyph to font
        glyph_order.append(glyph_name)
        existing.setGlyphOrder(glyph_order)
        existing["glyf"][glyph_name] = copy.deepcopy(full["glyf"][glyph_name])
        existing["hmtx"].metrics[glyph_name] = full["hmtx"].metrics[glyph_name]
        existing["maxp"].numGlyphs = len(glyph_order)

        # Add ligature - find a subtable with the right first char
        target_ext = None
        for sub in lookup.SubTable:
            ext = sub.ExtSubTable
            if (
                ext.LookupType == 4
                and hasattr(ext, "ligatures")
                and first_char in ext.ligatures
            ):
                target_ext = ext
                break
        if target_ext is None:
            # Use last subtable
            target_ext = lookup.SubTable[-1].ExtSubTable

        new_lig = Ligature()
        new_lig.LigGlyph = glyph_name
        new_lig.Component = rest
        existing_ligs = list(target_ext.ligatures.get(first_char, []))
        target_ext.ligatures[first_char] = [new_lig] + existing_ligs

        print(f"  Patched: {icon_name} -> {glyph_name}")

    # Save as next version
    current_version = int(current_font.stem.split(".v")[1])
    new_version = current_version + 1
    new_font_path = FONT_PATH / f"material-symbols-outlined-subset.v{new_version}.woff2"
    existing.flavor = "woff2"
    existing.save(str(new_font_path))
    return new_font_path


def main():
    patch_mode = "--patch" in sys.argv

    current_font = find_current_font()
    if not current_font:
        print("ERROR: No font subset found in", FONT_PATH)
        sys.exit(1)

    print(f"Font: {current_font.name}")
    template_icons = get_icons_from_templates()
    font_icons = get_icons_from_font(current_font)

    missing = template_icons - font_icons
    extra = font_icons - template_icons

    print(f"Template icons: {len(template_icons)}")
    print(f"Font icons: {len(font_icons)}")

    if not missing:
        print("All icons present in font subset.")
        return

    print(f"\nMISSING from font ({len(missing)}):")
    for icon in sorted(missing):
        print(f"  - {icon}")

    if extra:
        print(f"\nExtra (unused) in font ({len(extra)}): {sorted(extra)[:5]}...")

    if not patch_mode:
        print("\nRun with --patch and provide full font path to fix.")
        sys.exit(1)

    # Find full font
    full_font_candidates = [
        Path("/tmp/material-symbols-full.ttf"),
        Path("/tmp/MaterialSymbolsOutlined.ttf"),
    ]
    full_font = next((p for p in full_font_candidates if p.exists()), None)
    if not full_font:
        print("ERROR: Full font not found. Download from Google Fonts first:")
        print(
            "  curl -o /tmp/material-symbols-full.ttf '<ttf-url-from-fonts.googleapis.com>'"
        )
        sys.exit(1)

    new_font = patch_font(missing, current_font, full_font)
    print(f"\nPatched font saved: {new_font.name}")
    print(f"Update static/css/icons.css to reference {new_font.name}")


if __name__ == "__main__":
    main()
