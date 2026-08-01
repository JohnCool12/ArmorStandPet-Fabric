from pathlib import Path

path = Path("project/src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java")
source = path.read_text(encoding="utf-8")

replacements = {
    "private static final long ATTACK_ANIMATION_TICKS = 7L;":
        "private static final long ATTACK_ANIMATION_TICKS = 9L;",
    "private static final EulerAngle LEFT_ARM_ATTACK_POSE = new EulerAngle(-0.9D, 0.0D, -0.1D);":
        "private static final EulerAngle RIGHT_ARM_ATTACK_POSE = new EulerAngle(-0.9D, 0.0D, 0.1D);",
    "stand.setLeftArmPose(LEFT_ARM_ATTACK_POSE);":
        "stand.setRightArmPose(RIGHT_ARM_ATTACK_POSE);",
}

for old, new in replacements.items():
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one occurrence of {old!r}, found {count}")
    source = source.replace(old, new, 1)

required = [
    "ATTACK_ANIMATION_TICKS = 9L",
    "RIGHT_ARM_ATTACK_POSE",
    "new EulerAngle(-0.9D, 0.0D, 0.1D)",
    "setRightArmPose(RIGHT_ARM_ATTACK_POSE)",
]
for text in required:
    if source.count(text) != 1:
        raise SystemExit(f"Expected exactly one final occurrence of {text!r}")

for forbidden in ["LEFT_ARM_ATTACK_POSE", "setLeftArmPose("]:
    if forbidden in source:
        raise SystemExit(f"Left-arm combat animation remained after conversion: {forbidden}")

path.write_text(source, encoding="utf-8")
print("Switched combat animation to the right arm and slowed it from 7 to 9 ticks")
