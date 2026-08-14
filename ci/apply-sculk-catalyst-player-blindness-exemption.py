from pathlib import Path
import json

root = Path('project')
targeted = root / 'src/main/java/com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java'
effect = root / 'src/main/java/com/mcmoddev/golems/data/behavior/EffectBehavior.java'
sculk = root / 'src/main/resources/data/golems/golems/golem/sculk_catalyst.json'

s = targeted.read_text()

# Imports used to identify the actual attack target and exempt only player bystanders.
old_imports = '''import net.minecraft.world.effect.MobEffectInstance;\nimport net.minecraft.world.entity.LivingEntity;\nimport net.minecraft.world.entity.Mob;\nimport net.minecraft.world.entity.ai.targeting.TargetingConditions;\n'''
new_imports = '''import net.minecraft.world.effect.MobEffectInstance;\nimport net.minecraft.world.entity.Entity;\nimport net.minecraft.world.entity.LivingEntity;\nimport net.minecraft.world.entity.Mob;\nimport net.minecraft.world.entity.ai.targeting.TargetingConditions;\nimport net.minecraft.world.entity.player.Player;\n'''
if s.count(old_imports) != 1:
    raise SystemExit('TargetedMobEffects import anchor not found exactly once')
s = s.replace(old_imports, new_imports, 1)

old_codec = '''\t\t\tTargetType.CODEC.fieldOf("target").forGetter(TargetedMobEffects::getTargetType),\n\t\t\tCodec.doubleRange(0.0D, 128.0D).optionalFieldOf("radius", 0.0D).forGetter(TargetedMobEffects::getRadius),\n\t\t\tIntProvider.NON_NEGATIVE_CODEC.optionalFieldOf("rolls", ConstantInt.of(0)).forGetter(TargetedMobEffects::getRolls),\n\t\t\tEGCodecUtils.listOrElementCodec(EGCodecUtils.MOB_EFFECT_INSTANCE_CODEC).fieldOf("effect").forGetter(TargetedMobEffects::getEffects)\n\t).apply(instance, TargetedMobEffects::new));\n'''
new_codec = '''\t\t\tTargetType.CODEC.fieldOf("target").forGetter(TargetedMobEffects::getTargetType),\n\t\t\tCodec.doubleRange(0.0D, 128.0D).optionalFieldOf("radius", 0.0D).forGetter(TargetedMobEffects::getRadius),\n\t\t\tIntProvider.NON_NEGATIVE_CODEC.optionalFieldOf("rolls", ConstantInt.of(0)).forGetter(TargetedMobEffects::getRolls),\n\t\t\tCodec.BOOL.optionalFieldOf("exclude_bystander_players", false).forGetter(TargetedMobEffects::excludeBystanderPlayers),\n\t\t\tEGCodecUtils.listOrElementCodec(EGCodecUtils.MOB_EFFECT_INSTANCE_CODEC).fieldOf("effect").forGetter(TargetedMobEffects::getEffects)\n\t).apply(instance, TargetedMobEffects::new));\n'''
if s.count(old_codec) != 1:
    raise SystemExit('TargetedMobEffects codec anchor not found exactly once')
s = s.replace(old_codec, new_codec, 1)

old_fields = '''\t/** The number of effects to apply, or zero to apply all effects **/\n\tprivate final IntProvider rolls;\n\t/** The effects to apply **/\n\tprivate final List<MobEffectInstance> effects;\n\n\tpublic TargetedMobEffects(TargetType targetType, double radius, IntProvider rolls, List<MobEffectInstance> effects) {\n\t\tthis.targetType = targetType;\n\t\tthis.radius = radius;\n\t\tthis.rolls = rolls;\n\t\tthis.effects = effects;\n\t}\n'''
new_fields = '''\t/** The number of effects to apply, or zero to apply all effects **/\n\tprivate final IntProvider rolls;\n\t/** When true, AREA effects skip player bystanders but may still affect the direct attack target. **/\n\tprivate final boolean excludeBystanderPlayers;\n\t/** The effects to apply **/\n\tprivate final List<MobEffectInstance> effects;\n\n\tpublic TargetedMobEffects(TargetType targetType, double radius, IntProvider rolls, boolean excludeBystanderPlayers, List<MobEffectInstance> effects) {\n\t\tthis.targetType = targetType;\n\t\tthis.radius = radius;\n\t\tthis.rolls = rolls;\n\t\tthis.excludeBystanderPlayers = excludeBystanderPlayers;\n\t\tthis.effects = effects;\n\t}\n'''
if s.count(old_fields) != 1:
    raise SystemExit('TargetedMobEffects field/constructor anchor not found exactly once')
s = s.replace(old_fields, new_fields, 1)

old_getters = '''\tpublic IntProvider getRolls() {\n\t\treturn rolls;\n\t}\n\n\tpublic List<MobEffectInstance> getEffects() {\n'''
new_getters = '''\tpublic IntProvider getRolls() {\n\t\treturn rolls;\n\t}\n\n\tpublic boolean excludeBystanderPlayers() {\n\t\treturn excludeBystanderPlayers;\n\t}\n\n\tpublic List<MobEffectInstance> getEffects() {\n'''
if s.count(old_getters) != 1:
    raise SystemExit('TargetedMobEffects getter anchor not found exactly once')
s = s.replace(old_getters, new_getters, 1)

old_apply = '''\tpublic void apply(IExtraGolem entity) {\n\t\tif(effects.isEmpty()) {\n\t\t\treturn;\n\t\t}\n\t\tfinal Mob mob = entity.asMob();\n\t\tfinal int rolls = this.rolls.sample(mob.getRandom());\n\t\tswitch (targetType) {\n\t\t\tcase AREA:\n\t\t\t\tTargetingConditions condition = TargetingConditions.forNonCombat()\n\t\t\t\t\t\t.ignoreLineOfSight().ignoreInvisibilityTesting();\n\t\t\t\tList<LivingEntity> targets = mob.level().getNearbyEntities(LivingEntity.class,\n\t\t\t\t\t\tcondition, mob, mob.getBoundingBox().inflate(radius));\n\t\t\t\t// apply to each entity in list\n\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t}\n\t\t\t\tbreak;\n\t\t\tcase SELF:\n\t\t\t\tcopyEffects(mob, rolls, effects);\n\t\t\t\tbreak;\n\t\t\tcase ENEMY:\n\t\t\t\tif(mob.getTarget() != null) {\n\t\t\t\t\tcopyEffects(mob.getTarget(), rolls, effects);\n\t\t\t\t}\n\t\t\t\tbreak;\n\t\t}\n\t}\n'''
new_apply = '''\tpublic void apply(IExtraGolem entity) {\n\t\tapply(entity, null);\n\t}\n\n\t/**\n\t * Applies effects while retaining the identity of the entity directly struck by an\n\t * ATTACK-triggered behavior. This is used by opt-in AREA effects that should not\n\t * punish player bystanders but must still affect a player who was actually hit.\n\t */\n\tpublic void apply(IExtraGolem entity, Entity directAttackTarget) {\n\t\tif(effects.isEmpty()) {\n\t\t\treturn;\n\t\t}\n\t\tfinal Mob mob = entity.asMob();\n\t\tfinal int rolls = this.rolls.sample(mob.getRandom());\n\t\tswitch (targetType) {\n\t\t\tcase AREA:\n\t\t\t\tTargetingConditions condition = TargetingConditions.forNonCombat()\n\t\t\t\t\t\t.ignoreLineOfSight().ignoreInvisibilityTesting();\n\t\t\t\tList<LivingEntity> targets = mob.level().getNearbyEntities(LivingEntity.class,\n\t\t\t\t\t\tcondition, mob, mob.getBoundingBox().inflate(radius));\n\t\t\t\t// Preserve the existing area effect for non-player living entities. Player\n\t\t\t\t// bystanders are exempt only when this data-driven option is enabled; the\n\t\t\t\t// exact player struck by this attack remains a valid recipient.\n\t\t\t\tfor (LivingEntity target : targets) {\n\t\t\t\t\tif (excludeBystanderPlayers && target instanceof Player && target != directAttackTarget) {\n\t\t\t\t\t\tcontinue;\n\t\t\t\t\t}\n\t\t\t\t\tcopyEffects(target, rolls, effects);\n\t\t\t\t}\n\t\t\t\tbreak;\n\t\t\tcase SELF:\n\t\t\t\tcopyEffects(mob, rolls, effects);\n\t\t\t\tbreak;\n\t\t\tcase ENEMY:\n\t\t\t\tif(mob.getTarget() != null) {\n\t\t\t\t\tcopyEffects(mob.getTarget(), rolls, effects);\n\t\t\t\t}\n\t\t\t\tbreak;\n\t\t}\n\t}\n'''
if s.count(old_apply) != 1:
    raise SystemExit('TargetedMobEffects apply anchor not found exactly once')
s = s.replace(old_apply, new_apply, 1)

old_equals = '''\t\treturn Double.compare(that.radius, radius) == 0 && targetType == that.targetType\n\t\t\t\t&& rolls.getType() == that.rolls.getType() && rolls.getMinValue() == that.rolls.getMinValue() && rolls.getMaxValue() == this.rolls.getMaxValue()\n\t\t\t\t&& effects.equals(that.effects);\n'''
new_equals = '''\t\treturn Double.compare(that.radius, radius) == 0 && targetType == that.targetType\n\t\t\t\t&& rolls.getType() == that.rolls.getType() && rolls.getMinValue() == that.rolls.getMinValue() && rolls.getMaxValue() == this.rolls.getMaxValue()\n\t\t\t\t&& excludeBystanderPlayers == that.excludeBystanderPlayers\n\t\t\t\t&& effects.equals(that.effects);\n'''
if s.count(old_equals) != 1:
    raise SystemExit('TargetedMobEffects equals anchor not found exactly once')
s = s.replace(old_equals, new_equals, 1)

old_hash = '''\t\treturn Objects.hash(targetType, radius, rolls.getType(), rolls.getMinValue(), rolls.getMaxValue(), effects);\n'''
new_hash = '''\t\treturn Objects.hash(targetType, radius, rolls.getType(), rolls.getMinValue(), rolls.getMaxValue(), excludeBystanderPlayers, effects);\n'''
if s.count(old_hash) != 1:
    raise SystemExit('TargetedMobEffects hash anchor not found exactly once')
s = s.replace(old_hash, new_hash, 1)

targeted.write_text(s)

# Only ATTACK-triggered effects know the exact struck entity. Preserve old behavior for
# HURT/TICK callers by leaving their one-argument apply(...) calls unchanged.
s = effect.read_text()
old_attack_call = '''\t\t\ttargetedMobEffects.apply(entity.asMob());\n'''
# There are three identical calls; replace only the one within onAttack.
attack_start = s.index('\tpublic void onAttack(IExtraGolem entity, Entity target) {')
attack_end = s.index('\n\t}', attack_start) + 3
attack_block = s[attack_start:attack_end]
if attack_block.count(old_attack_call) != 1:
    raise SystemExit('EffectBehavior onAttack apply call not found exactly once')
attack_block = attack_block.replace(old_attack_call, '\t\t\ttargetedMobEffects.apply(entity.asMob(), target);\n', 1)
s = s[:attack_start] + attack_block + s[attack_end:]
effect.write_text(s)

# Opt in ONLY the Sculk Catalyst Golem. Other AREA effect behaviors retain the legacy
# behavior because the codec default is false.
data = json.loads(sculk.read_text())
changed = 0
for behavior in data.get('brain', {}).get('behaviors', []):
    if behavior.get('type') == 'golems:effect' and behavior.get('trigger') == 'attack':
        apply = behavior.get('apply', {})
        effect_obj = apply.get('effect', {})
        if apply.get('target') == 'area' and effect_obj.get('id') == 'minecraft:blindness':
            apply['exclude_bystander_players'] = True
            changed += 1
if changed != 1:
    raise SystemExit(f'Expected exactly one Sculk Catalyst attack-area blindness behavior, found {changed}')
sculk.write_text(json.dumps(data, indent=2) + '\n')

print('Applied Sculk Catalyst player-bystander blindness exemption; direct attack target remains eligible.')
