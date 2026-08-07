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

required_counts = {
    "ATTACK_ANIMATION_TICKS = 9L": 1,
    "RIGHT_ARM_ATTACK_POSE": 2,
    "new EulerAngle(-0.9D, 0.0D, 0.1D)": 1,
    "setRightArmPose(RIGHT_ARM_ATTACK_POSE)": 1,
}
for text, expected in required_counts.items():
    actual = source.count(text)
    if actual != expected:
        raise SystemExit(f"Expected {expected} final occurrence(s) of {text!r}, found {actual}")

for forbidden in ["LEFT_ARM_ATTACK_POSE", "setLeftArmPose("]:
    if forbidden in source:
        raise SystemExit(f"Left-arm combat animation remained after conversion: {forbidden}")

path.write_text(source, encoding="utf-8")
print("Switched combat animation to the right arm and slowed it from 7 to 9 ticks")
