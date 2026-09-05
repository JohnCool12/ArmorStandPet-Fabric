from pathlib import Path
root=Path('project/src/main/java/com/mcmoddev/golems/client')

def edit(rel,fn):
    p=root/rel; p.write_text(fn(p.read_text()))

# Matrix3x2fStack is 2D; uniform scaling replaces the old 3D GUI PoseStack call.
for rel in ['menu/button/CyclingItemButton.java','menu/guide_book/page/GolemDiagramPage.java']:
    edit(rel, lambda s: s.replace('graphics.pose().scale(scale, scale, scale);','graphics.pose().scale(scale);'))

# Refresh the visible stack immediately when a description switches its item list.
def cycle(s):
    s=s.replace('this.items.clear();\n\t\tthis.items.addAll(list);\n\t\tthis.setIndex(index);',
                'int current = this.index;\n\t\tthis.items.clear();\n\t\tthis.items.addAll(list);\n\t\tthis.index = -1;\n\t\tthis.setIndex(Math.max(0, current));')
    return s
edit('menu/button/CyclingItemButton.java',cycle)

# Preserve the visible yellow debug/track fill with an explicit alpha channel.
edit('menu/button/ScrollButton.java', lambda s: s.replace('0xFFFF00);','0xFFFFFF00);'))

# Minecraft 26.1's six-argument textWithWordWrap overload draws a drop shadow.
# The guide uses black text on light parchment, so explicitly disable that shadow everywhere.
def no_shadow(s):
    s=s.replace('graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0xFF000000);',
                'graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0xFF000000, false);')
    s=s.replace('graphics.textWithWordWrap(font, title, posX, posY, maxWidth, 0xFF000000);',
                'graphics.textWithWordWrap(font, title, posX, posY, maxWidth, 0xFF000000, false);')
    s=s.replace('graphics.textWithWordWrap(font, getMessage(), posX, posY, maxWidth, 0xFF000000);',
                'graphics.textWithWordWrap(font, getMessage(), posX, posY, maxWidth, 0xFF000000, false);')
    return s

for rel in [
    'menu/guide_book/page/TitleAndBodyPage.java',
    'menu/guide_book/page/GolemDescriptionPage.java',
    'menu/button/TableOfContentsButton.java',
]:
    edit(rel, no_shadow)

# Invariant: no wrapped Guide Book text may silently fall back to the shadowed overload.
for rel in [
    'menu/guide_book/page/TitleAndBodyPage.java',
    'menu/guide_book/page/GolemDescriptionPage.java',
    'menu/button/TableOfContentsButton.java',
]:
    p = root / rel
    for line in p.read_text().splitlines():
        if 'textWithWordWrap(' in line and ', false);' not in line:
            raise SystemExit(f'Guide text shadow still enabled in {rel}: {line.strip()}')

print('Applied pass 5b GUI polish and disabled Extra Golems Guide text shadows.')
