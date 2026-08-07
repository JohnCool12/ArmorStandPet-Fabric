from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")

# Expose LivingEntity's protected vanilla armor and enchantment reduction path
# to the mortality controller. This also invokes vanilla armor durability logic.
entity_path = root / "entity/PetArmorStandEntity.java"
entity = entity_path.read_text(encoding="utf-8")
hurt_method = (
    "\t@Override\n"
    "\tpublic boolean hurtServer(ServerLevel world, DamageSource source, float amount)\n"
    "\t{\n"
    "\t\treturn PetMortalityController.hurt(this, world, source, amount);\n"
    "\t}\n"
)
defense_method = (
    "\n\t/** Applies the same armor, toughness, protection and resistance logic as other living entities. */\n"
    "\tpublic float applyPetDefenses(DamageSource source, float amount)\n"
    "\t{\n"
    "\t\tfloat afterArmor = this.getDamageAfterArmorAbsorb(source, amount);\n"
    "\t\treturn this.getDamageAfterMagicAbsorb(source, afterArmor);\n"
    "\t}\n"
)
if defense_method.strip() not in entity:
    if entity.count(hurt_method) != 1:
        raise SystemExit("Could not find patched PetArmorStandEntity.hurtServer")
    entity = entity.replace(hurt_method, hurt_method + defense_method, 1)
entity_path.write_text(entity, encoding="utf-8")

# Delete old revivable-death records immediately after storage is loaded.
mod_path = root / "ASPetMod.java"
mod = mod_path.read_text(encoding="utf-8")
controller_import = "import io.github.kyzderp.armorstandpet.combat.PetMortalityController;\n"
if controller_import not in mod:
    package_marker = "package io.github.kyzderp.armorstandpet;\n"
    if mod.count(package_marker) != 1:
        raise SystemExit("Could not find ASPetMod package marker")
    mod = mod.replace(package_marker, package_marker + "\n" + controller_import, 1)
load_call = "\t\tPetStorage.loadAll(false);\n"
purge_call = load_call + "\t\tPetMortalityController.purgeLegacyDeadPets();\n"
if "PetMortalityController.purgeLegacyDeadPets();" not in mod:
    if mod.count(load_call) != 1:
        raise SystemExit(f"Expected one PetStorage.loadAll(false) call, found {mod.count(load_call)}")
    mod = mod.replace(load_call, purge_call, 1)
mod_path.write_text(mod, encoding="utf-8")

# Make combat use the held item's vanilla attack attribute/enchantments and let
# a lethal swing finish visually before the pose is cleared.
combat_path = root / "combat/OwnerAttackCombatController.java"
combat = combat_path.read_text(encoding="utf-8")

imports = [
    "import net.minecraft.world.damagesource.DamageSource;\n",
    "import net.minecraft.world.entity.ai.attributes.Attributes;\n",
    "import net.minecraft.world.item.ItemStack;\n",
    "import net.minecraft.world.item.enchantment.EnchantmentHelper;\n",
]
import_marker = "import net.minecraft.world.InteractionHand;\n"
if combat.count(import_marker) != 1:
    raise SystemExit("Could not find combat import marker")
for item in imports:
    if item not in combat:
        combat = combat.replace(import_marker, import_marker + item, 1)

constant = "\tprivate static final float ATTACK_DAMAGE = 4.0F;\n"
if constant in combat:
    combat = combat.replace(constant, "", 1)

old_target_guard = "\t\t\t\t\t|| target == null || target.isRemoved() || !target.isAlive()\n"
new_target_guard = "\t\t\t\t\t|| target == null\n"
if old_target_guard not in combat:
    raise SystemExit("Could not find combat target lifetime guard")
combat = combat.replace(old_target_guard, new_target_guard, 1)

now_marker = "\t\t\tlong now = level.getGameTime();\n"
finish_gate = (
    now_marker
    + "\t\t\t// A lethal hit must keep its raised-arm pose long enough for clients to render it.\n"
    + "\t\t\tif (state.finishAfterAnimation)\n"
    + "\t\t\t{\n"
    + "\t\t\t\tif (now >= state.animationResetTick)\n"
    + "\t\t\t\t\tfinish(iterator, state);\n"
    + "\t\t\t\tcontinue;\n"
    + "\t\t\t}\n\n"
    + "\t\t\t// Death caused externally has no pet swing to preserve.\n"
    + "\t\t\tif (target.isRemoved() || !target.isAlive())\n"
    + "\t\t\t{\n"
    + "\t\t\t\tfinish(iterator, state);\n"
    + "\t\t\t\tcontinue;\n"
    + "\t\t\t}\n"
)
if "state.finishAfterAnimation" not in combat:
    if combat.count(now_marker) != 1:
        raise SystemExit(f"Expected one combat game-time marker, found {combat.count(now_marker)}")
    combat = combat.replace(now_marker, finish_gate, 1)

old_attack = (
    "\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);\n"
    "\t\t\tstand.swing(InteractionHand.MAIN_HAND);\n"
    "\t\t\ttarget.hurtServer(level, level.damageSources().mobAttack(stand), ATTACK_DAMAGE);\n"
    "\t\t\tstate.animationResetTick = now + ATTACK_ANIMATION_TICKS;\n"
    "\t\t\tstate.nextAttackTick = now + ATTACK_COOLDOWN_TICKS;\n\n"
    "\t\t\tif (!target.isAlive() || target.isRemoved())\n"
    "\t\t\t\tfinish(iterator, state);\n"
)
new_attack = (
    "\t\t\tstand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);\n"
    "\t\t\tstand.swing(InteractionHand.MAIN_HAND);\n\n"
    "\t\t\tItemStack weapon = stand.getMainHandItem();\n"
    "\t\t\tDamageSource damageSource = level.damageSources().mobAttack(stand);\n"
    "\t\t\t// LivingEntity's equipment system applies the held item's attack\n"
    "\t\t\t// attribute modifiers to this value, just as it does for players.\n"
    "\t\t\tfloat attackDamage = Math.max(0.0F,\n"
    "\t\t\t\t\t(float) stand.getAttributeValue(Attributes.ATTACK_DAMAGE));\n"
    "\t\t\tif (!weapon.isEmpty())\n"
    "\t\t\t\tattackDamage = EnchantmentHelper.modifyDamage(\n"
    "\t\t\t\t\t\tlevel, weapon, target, damageSource, attackDamage);\n\n"
    "\t\t\tboolean damaged = target.hurtServer(level, damageSource, attackDamage);\n"
    "\t\t\tif (damaged && !weapon.isEmpty())\n"
    "\t\t\t{\n"
    "\t\t\t\tweapon.hurtEnemy(target, stand);\n"
    "\t\t\t\tweapon.postHurtEnemy(target, stand);\n"
    "\t\t\t\tEnchantmentHelper.doPostAttackEffectsWithItemSource(\n"
    "\t\t\t\t\t\tlevel, target, damageSource, weapon);\n"
    "\t\t\t}\n\n"
    "\t\t\tstate.animationResetTick = now + ATTACK_ANIMATION_TICKS;\n"
    "\t\t\tstate.nextAttackTick = now + ATTACK_COOLDOWN_TICKS;\n\n"
    "\t\t\tif (!target.isAlive() || target.isRemoved())\n"
    "\t\t\t\tstate.finishAfterAnimation = true;\n"
)
if combat.count(old_attack) != 1:
    raise SystemExit(f"Expected one old fixed-damage attack block, found {combat.count(old_attack)}")
combat = combat.replace(old_attack, new_attack, 1)

field_marker = "\t\tprivate long animationResetTick;\n"
field_addition = field_marker + "\t\tprivate boolean finishAfterAnimation;\n"
if "private boolean finishAfterAnimation;" not in combat:
    if combat.count(field_marker) != 1:
        raise SystemExit("Could not find AttackState animation field")
    combat = combat.replace(field_marker, field_addition, 1)

for forbidden in [
    "ATTACK_DAMAGE = 4.0F",
    "getDamageSource(stand)",
    "getBonusAttackDamage(",
    "finish(iterator, state);\n\t\t}\n\t}\n\n\tprivate static void restorePetName",
]:
    if forbidden in combat:
        raise SystemExit(f"Obsolete combat behavior remained: {forbidden}")

required = [
    "state.finishAfterAnimation = true",
    "if (state.finishAfterAnimation)",
    "getAttributeValue(Attributes.ATTACK_DAMAGE)",
    "EnchantmentHelper.modifyDamage",
    "weapon.hurtEnemy(target, stand)",
    "weapon.postHurtEnemy(target, stand)",
    "doPostAttackEffectsWithItemSource",
]
for text in required:
    if text not in combat:
        raise SystemExit(f"Equipment/final-animation combat integration missing: {text}")
combat_path.write_text(combat, encoding="utf-8")

print("Added permanent-death cleanup, vanilla armor/weapon behavior, and lethal-hit animation hold")
