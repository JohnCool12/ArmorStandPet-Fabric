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
print('Applied pass 5b GUI polish.')
