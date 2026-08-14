from pathlib import Path

p = Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s = p.read_text()

# Add a per-entity transient guard used only while vanilla DefendVillageTargetGoal
# assigns its reputation-derived player target. This lets us distinguish legitimate
# village hostility from unexplained/group-propagated player targets.
field_anchor = '''\t// COLOR //\n\tprivate int biomeColor = 0x83A05A;\n'''
field_repl = '''\t// COLOR //\n\tprivate int biomeColor = 0x83A05A;\n\n\t// PLAYER TARGET PROVENANCE //\n\t// True only while this golem's own vanilla DefendVillageTargetGoal is assigning\n\t// a reputation-derived player target. Direct retaliation is instead authorized\n\t// by this golem's own lastHurtByMob / NeutralMob anger state.\n\tprivate boolean assigningVillageDefensePlayerTarget;\n'''
if s.count(field_anchor) != 1:
    raise SystemExit(f'Expected field anchor once, found {s.count(field_anchor)}')
s = s.replace(field_anchor, field_repl, 1)

old_goal = '''\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this));'''
new_goal = '''\t\tthis.targetSelector.addGoal(1, new DefendVillageTargetGoal(this) {\n\t\t\t@Override\n\t\t\tpublic void start() {\n\t\t\t\tassigningVillageDefensePlayerTarget = true;\n\t\t\t\ttry {\n\t\t\t\t\tsuper.start();\n\t\t\t\t} finally {\n\t\t\t\t\tassigningVillageDefensePlayerTarget = false;\n\t\t\t\t}\n\t\t\t}\n\t\t});'''
count = s.count(old_goal)
if count < 1:
    raise SystemExit('Natural target helper DefendVillageTargetGoal line missing')
# Replace every exact natural-stack registration that survives the cumulative patches.
s = s.replace(old_goal, new_goal)

old_set = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tsuper.setTarget(pTarget);\n'''
new_set = '''\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {\n\t\t// Vanilla Iron Golem direct retaliation is individual: HurtByTargetGoal only\n\t\t// alerts peers when setAlertOthers() was explicitly enabled, which IronGolem\n\t\t// does not do. Reject player targets that have no provenance local to THIS\n\t\t// golem. Legitimate player targets remain allowed when:\n\t\t//   1) this golem was directly hurt by that player;\n\t\t//   2) this golem's own NeutralMob anger state says it is angry at that player; or\n\t\t//   3) this golem's own vanilla DefendVillageTargetGoal is assigning the target\n\t\t//      because nearby villager reputation is sufficiently low.\n\t\t// This also hardens against any material behavior/mod integration that attempts\n\t\t// to copy another golem's player target without copying a legitimate cause.\n\t\tif (pTarget instanceof Player player\n\t\t\t\t&& !assigningVillageDefensePlayerTarget\n\t\t\t\t&& this.getLastHurtByMob() != player\n\t\t\t\t&& !this.isAngryAt(player)) {\n\t\t\treturn;\n\t\t}\n\n\t\tfinal LivingEntity oldTarget = this.getTarget();\n\t\tsuper.setTarget(pTarget);\n'''
if s.count(old_set) != 1:
    raise SystemExit(f'Expected setTarget header once, found {s.count(old_set)}')
s = s.replace(old_set, new_set, 1)

# Static safeguards.
if 'setAlertOthers' in s:
    raise SystemExit('Unexpected setAlertOthers call exists in GolemBase')
if 'assigningVillageDefensePlayerTarget' not in s:
    raise SystemExit('Village-defense provenance guard missing')
if 'this.getLastHurtByMob() != player' not in s or '!this.isAngryAt(player)' not in s:
    raise SystemExit('Direct/anger provenance checks missing')

p.write_text(s)
print(f'Applied individual player-target provenance guard; wrapped {count} DefendVillageTargetGoal registration(s).')
