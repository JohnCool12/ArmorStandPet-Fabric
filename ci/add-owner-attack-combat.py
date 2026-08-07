from pathlib import Path
import re

path = Path("project/src/main/java/io/github/kyzderp/armorstandpet/listeners/PlayerActionListener.java")
source = path.read_text(encoding="utf-8")

combat_import = "import io.github.kyzderp.armorstandpet.combat.OwnerAttackCombatController;\n"
if combat_import not in source:
    marker = "import io.github.kyzderp.armorstandpet.actions.WalkAction;\n"
    if marker not in source:
        raise SystemExit("Could not find PlayerActionListener import insertion point")
    source = source.replace(marker, marker + combat_import, 1)

register_pattern = re.compile(
    r"(public\s+static\s+void\s+register\s*\(\s*\)\s*\{\s*)",
    re.MULTILINE,
)
if "OwnerAttackCombatController.register();" not in source:
    source, register_count = register_pattern.subn(
        r"\1\n\t\tOwnerAttackCombatController.register();\n",
        source,
        count=1,
    )
    if register_count != 1:
        raise SystemExit(f"Expected one PlayerActionListener.register() method, found {register_count}")

non_pet_guard = re.compile(
    r"if\s*\(\s*!\(\s*entity\s+instanceof\s+PetArmorStandEntity\s*\)\s*\)\s*"
    r"return\s+InteractionResult\.PASS\s*;",
    re.MULTILINE,
)
replacement = """if (!(entity instanceof PetArmorStandEntity))
		{
			OwnerAttackCombatController.onOwnerAttack(player, world, entity);
			return InteractionResult.PASS;
		}"""
source, guard_count = non_pet_guard.subn(replacement, source, count=1)
if guard_count != 1:
    raise SystemExit(f"Expected one non-pet attack guard, found {guard_count}")

required = [
    combat_import.strip(),
    "OwnerAttackCombatController.register();",
    "OwnerAttackCombatController.onOwnerAttack(player, world, entity);",
]
for text in required:
    if text not in source:
        raise SystemExit(f"Combat integration missing required text: {text}")

path.write_text(source, encoding="utf-8")
print("Enabled owner-directed pet attacks without owner-hurt retaliation")
