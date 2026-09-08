from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()


def replace_once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s = s.replace(old, new, 1)

# Vanilla Iron Golems use 1.0 ordinary knockback resistance but leave the separate
# explosion-knockback resistance at its vanilla default of 0. Extra Golems should do
# the same regardless of their material-specific ordinary knockback resistance.
old = '''\t\t\t\t.add(Attributes.KNOCKBACK_RESISTANCE,\n\t\t\t\t\t\tcom.mcmoddev.golems.data.golem.Attributes.EMPTY.getKnockbackResistance())\n\t\t\t\t.add(Attributes.ATTACK_KNOCKBACK, com.mcmoddev.golems.data.golem.Attributes.EMPTY.getAttackKnockback())\n'''
new = '''\t\t\t\t.add(Attributes.KNOCKBACK_RESISTANCE,\n\t\t\t\t\t\tcom.mcmoddev.golems.data.golem.Attributes.EMPTY.getKnockbackResistance())\n\t\t\t\t.add(Attributes.EXPLOSION_KNOCKBACK_RESISTANCE, 0.0D)\n\t\t\t\t.add(Attributes.ATTACK_KNOCKBACK, com.mcmoddev.golems.data.golem.Attributes.EMPTY.getAttackKnockback())\n'''
replace_once(old, new, 'explicit vanilla explosion knockback resistance')

# The original mod conflated explosion DAMAGE immunity with total explosion immunity.
# Explosion processing checks ignoreExplosion() before calculating velocity, so returning
# true here suppresses Wind Charge / Wind Burst movement too. Delegate physical explosion
# eligibility to vanilla IronGolem. Material damage immunity remains enforced separately by
# isInvulnerableTo(DamageSource), so explosion-proof materials still take no explosion damage.
old = '''\t@Override\n\tpublic boolean ignoreExplosion(net.minecraft.world.level.Explosion explosion) {\n\t\tfinal Optional<GolemContainer> oContainer = getContainer();\n\t\tif (oContainer.isEmpty()) {\n\t\t\treturn super.ignoreExplosion(explosion);\n\t\t}\n\t\treturn oContainer.get().getAttributes().isImmuneTo(level().registryAccess(),\n\t\t\t\tImmutableSet.of(DamageTypes.EXPLOSION, DamageTypes.PLAYER_EXPLOSION));\n\t}\n'''
new = '''\t@Override\n\tpublic boolean ignoreExplosion(net.minecraft.world.level.Explosion explosion) {\n\t\t// Match vanilla Iron Golem physics. Damage immunity is handled by\n\t\t// isInvulnerableTo(DamageSource), not by skipping explosion processing.\n\t\treturn super.ignoreExplosion(explosion);\n\t}\n'''
replace_once(old, new, 'separate explosion damage immunity from knockback physics')

p.write_text(s)
print('Applied vanilla Iron Golem explosion/wind knockback parity to all Extra Golems.')
