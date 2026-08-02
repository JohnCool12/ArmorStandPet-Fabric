from pathlib import Path
import re

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")
pet_path = root / "types/Pet.java"
storage_path = root / "storage/PetStorage.java"

# Every newly constructed Pet begins with a full internal ArmorStand health
# value. The explicit per-Pet health field is added by the following 1.21.1 API
# adaptation step and will also begin at 20.
pet = pet_path.read_text(encoding="utf-8")
old_constructor_block = """\t\tif (this.stand != null)
\t\t{
\t\t\tthis.stand.setGravity(false);
"""
new_constructor_block = """\t\tif (this.stand != null)
\t\t{
\t\t\tthis.stand.setHealth(20.0F);
\t\t\tthis.stand.setGravity(false);
"""
if pet.count(old_constructor_block) != 1:
    raise SystemExit(
        f"Expected one Pet constructor stand-initialization block, found {pet.count(old_constructor_block)}"
    )
pet = pet.replace(old_constructor_block, new_constructor_block, 1)
pet_path.write_text(pet, encoding="utf-8")

# loadPet() restores the same saved pet after a restart and therefore preserves
# its remaining health. loadPetSettings() is used when an armor stand becomes a
# newly created/replacement pet. It may reuse preferences, but health and death
# state belong to the old pet and must never transfer to the new entity.
storage = storage_path.read_text(encoding="utf-8")
method_match = re.search(
    r"public static Pet loadPetSettings\(String owner, String world, PetType type, PetArmorStandEntity stand\)"
    r"(?P<body>.*?)\n\t}\n\n\tprivate static ServerLevel getWorld",
    storage,
    flags=re.DOTALL,
)
if method_match is None:
    raise SystemExit("Could not locate PetStorage.loadPetSettings")

body = method_match.group("body")
load_pattern = re.compile(
    r"(?P<indent>^[ \t]*)Pet pet = Pet\.createPet\(type, owner, stand\);\s*\n"
    r"(?P=indent)pet\.deserializeSettings\(data\);",
    flags=re.MULTILINE,
)
load_matches = list(load_pattern.finditer(body))
if len(load_matches) != 1:
    raise SystemExit(
        f"Expected one loadPetSettings deserialize sequence, found {len(load_matches)}"
    )

indent = load_matches[0].group("indent")
replacement = (
    f"{indent}// This is a new pet instance. Do not inherit mortality state from an\n"
    f"{indent}// earlier pet belonging to the same owner and type.\n"
    f"{indent}data.mortalDead = false;\n"
    f"{indent}data.health = 20.0F;\n\n"
    f"{indent}Pet pet = Pet.createPet(type, owner, stand);\n"
    f"{indent}pet.deserializeSettings(data);"
)
new_body = load_pattern.sub(replacement, body, count=1)
storage = storage[:method_match.start("body")] + new_body + storage[method_match.end("body"):]
storage_path.write_text(storage, encoding="utf-8")

# The 1.21.1 renderer instance is shared between all ArmorStandPet entities.
# Select the radius for every render so a small pet cannot leave its reduced
# shadow behind for the next normal-sized pet. Half the normal radius matches
# the visual scale used for baby-sized mobs while retaining the standard shadow
# for full-sized pets.
renderer_path = Path(
    "project/src/client/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java"
)
renderer_path.write_text("""/*******************************************************************************
 * ArmorStandPet - Fabric 1.21.1 port
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.client;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.ArmorStandRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.world.entity.decoration.ArmorStand;

/** Uses the vanilla armor-stand renderer with a size-aware ground shadow. */
public final class PetArmorStandRenderer extends ArmorStandRenderer
{
\tprivate static final float SMALL_SHADOW_SCALE = 0.5F;
\tprivate final float normalShadowRadius;

\tpublic PetArmorStandRenderer(EntityRendererProvider.Context context)
\t{
\t\tsuper(context);
\t\tthis.normalShadowRadius = this.shadowRadius;
\t}

\t@Override
\tpublic void render(ArmorStand entity, float entityYaw, float partialTick,
\t\t\tPoseStack poseStack, MultiBufferSource buffers, int packedLight)
\t{
\t\tthis.shadowRadius = entity.isSmall()
\t\t\t\t? this.normalShadowRadius * SMALL_SHADOW_SCALE
\t\t\t\t: this.normalShadowRadius;
\t\tsuper.render(entity, entityYaw, partialTick, poseStack, buffers, packedLight);
\t}
}
""", encoding="utf-8")

# The reset must exist only in loadPetSettings. The normal loadPet path must
# continue restoring the same pet's persisted health after a server restart.
pet_check = pet_path.read_text(encoding="utf-8")
storage_check = storage_path.read_text(encoding="utf-8")
renderer_check = renderer_path.read_text(encoding="utf-8")
if pet_check.count("this.stand.setHealth(20.0F);") != 1:
    raise SystemExit("Fresh Pet constructor must initialize entity health exactly once")
if storage_check.count("data.health = 20.0F;") != 1:
    raise SystemExit("Only the new-pet settings path may force saved health to 20")
if storage_check.count("data.mortalDead = false;") != 1:
    raise SystemExit("Only the new-pet settings path may clear saved death state")
if renderer_check.count("entity.isSmall()") != 1:
    raise SystemExit("Small-pet shadow selection was not installed exactly once")
if renderer_check.count("this.normalShadowRadius * SMALL_SHADOW_SCALE") != 1:
    raise SystemExit("Small-pet shadow must be half the normal renderer radius")
if "this.shadowRadius = 0.0F" in renderer_check:
    raise SystemExit("The size-aware renderer must not remove all pet shadows")

print("Separated new-pet health and added an independent half-size shadow for small pets")
