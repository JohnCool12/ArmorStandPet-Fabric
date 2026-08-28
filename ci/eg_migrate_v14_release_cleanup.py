#!/usr/bin/env python3
from pathlib import Path
import re, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else 'work').resolve()
events = ROOT / 'src/main/java/com/mcmoddev/golems/EGEvents.java'
s = events.read_text()
pattern = re.compile(r'''\t\t@SubscribeEvent\n\t\tpublic static void onServerStarted\(final ServerStartedEvent event\) \{\n\t\t\tGolemContainer\.populate\(event\.getServer\(\)\.registryAccess\(\)\);\n\t\t\ttry \{.*?\n\t\t\t\} catch \(Throwable t\) \{\n\t\t\t\tExtraGolems\.LOGGER\.error\("\[EGPORT\] construction self-test failed", t\);\n\t\t\t\}\n\t\t\}\n''', re.S)
replacement = '''\t\t@SubscribeEvent\n\t\tpublic static void onServerStarted(final ServerStartedEvent event) {\n\t\t\tGolemContainer.populate(event.getServer().registryAccess());\n\t\t}\n'''
new, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f'Expected exactly one instrumented onServerStarted block, found {count}')
if '[EGPORT]' in new or 'actual_build=' in new or 'testHead' in new:
    raise SystemExit('Release cleanup left runtime test instrumentation behind')
events.write_text(new)
print('Removed runtime construction diagnostics from release source')
