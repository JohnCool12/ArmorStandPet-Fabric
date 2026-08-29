from pathlib import Path

ROOT = Path('project/src/main/java')

for p in ROOT.rglob('*.java'):
    s = p.read_text()
    s = s.replace('net.minecraft.nbt.ValueInput', 'net.minecraft.world.level.storage.ValueInput')
    s = s.replace('net.minecraft.nbt.ValueOutput', 'net.minecraft.world.level.storage.ValueOutput')
    p.write_text(s)

print('Corrected ValueInput/ValueOutput packages for Minecraft 26.1')
