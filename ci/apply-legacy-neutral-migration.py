from pathlib import Path

p = Path("project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java")
text = p.read_text()
old = '''\tprivate void maintainConstructedNeutralRetaliation() {
\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}
'''
new = '''\tprivate void maintainConstructedNeutralRetaliation() {
\t\t// Compatibility migration for T-built golems saved by the immediately previous
\t\t// custom build, which unfortunately stored PlayerCreated=false without a marker.
\t\t// If such a legacy golem is involved with a player, convert it before natural
\t\t// village/reputation targeting can continue. Preserve a real direct attacker;
\t\t// discard a player target that came only from stale village reputation.
\t\tif (!isConstructedNeutral() && !this.isPlayerCreated()
\t\t\t\t&& (this.getLastHurtByMob() instanceof Player || this.getTarget() instanceof Player)) {
\t\t\tfinal LivingEntity legacyAttacker = this.getLastHurtByMob();
\t\t\tmarkConstructedNeutral();
\t\t\tif (legacyAttacker instanceof Player player && player.isAlive()
\t\t\t\t\t&& !player.isCreative() && !player.isSpectator()) {
\t\t\t\tthis.setLastHurtByMob(player);
\t\t\t\tthis.setTarget(player);
\t\t\t}
\t\t\treturn;
\t\t}

\t\tif (!isConstructedNeutral()) {
\t\t\treturn;
\t\t}
'''
if text.count(old) != 1:
    raise SystemExit(f"Expected one maintainConstructedNeutralRetaliation header, found {text.count(old)}")
p.write_text(text.replace(old, new, 1))
print("Added legacy neutral migration bridge.")
