from pathlib import Path

renderer_path = Path(
    "project/src/client/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java"
)
text = renderer_path.read_text(encoding="utf-8")

old_constructor = """\tpublic PetArmorStandRenderer(EntityRendererProvider.Context context)
\t{
\t\tsuper(context);
\t}
"""
new_constructor = """\tpublic PetArmorStandRenderer(EntityRendererProvider.Context context)
\t{
\t\tsuper(context);
\t\t// ArmorStandPet entities should not cast the vanilla circular entity shadow.
\t\t// This affects only this custom renderer; ordinary armor stands are unchanged.
\t\tthis.shadowRadius = 0.0F;
\t}
"""

if text.count(old_constructor) != 1:
    raise SystemExit(
        f"Expected one PetArmorStandRenderer constructor, found {text.count(old_constructor)}"
    )

text = text.replace(old_constructor, new_constructor, 1)

if text.count("this.shadowRadius = 0.0F;") != 1:
    raise SystemExit("Pet renderer shadow suppression was not applied exactly once")

renderer_path.write_text(text, encoding="utf-8")
print("Removed the ground shadow from ArmorStandPet entities only")
