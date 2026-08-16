from pathlib import Path
import re

root = Path("project")

# Build configuration: Minecraft 1.21.1 uses Java 21 and intermediary remapping.
build = root / "build.gradle"
build.write_text("""plugins {
\tid 'fabric-loom' version '1.10-SNAPSHOT'
\tid 'maven-publish'
}

version = project.mod_version
group = project.maven_group

base {
\tarchivesName = project.archives_base_name
}

loom {
\tsplitEnvironmentSourceSets()

\tmods {
\t\t\"armorstandpet\" {
\t\t\tsourceSet sourceSets.main
\t\t\tsourceSet sourceSets.client
\t\t}
\t}
}

dependencies {
\tminecraft \"com.mojang:minecraft:${project.minecraft_version}\"
\tmappings loom.officialMojangMappings()
\tmodImplementation \"net.fabricmc:fabric-loader:${project.loader_version}\"
\tmodImplementation \"net.fabricmc.fabric-api:fabric-api:${project.fabric_version}\"
}

processResources {
\tinputs.property \"version\", project.version

\tfilesMatching(\"fabric.mod.json\") {
\t\texpand \"version\": project.version
\t}
}

tasks.withType(JavaCompile).configureEach {
\tit.options.release = 21
}

java {
\ttoolchain {
\t\tlanguageVersion = JavaLanguageVersion.of(21)
\t}

\twithSourcesJar()
}
""", encoding="utf-8")

props = root / "gradle.properties"
props.write_text("""org.gradle.jvmargs=-Xmx2G
org.gradle.parallel=true

# Fabric 1.21.1
minecraft_version=1.21.1
loader_version=0.16.14
fabric_version=0.116.15+1.21.1

# Mod
mod_version=2.0.0+1.21.1
maven_group=io.github.kyzderp
archives_base_name=armorstandpet-fabric-1.21.1
""", encoding="utf-8")

mod_json = root / "src/main/resources/fabric.mod.json"
text = mod_json.read_text(encoding="utf-8")
text = text.replace(
    "Fabric port of the original Bukkit/Spigot plugin by Kyzeragon.",
    "Fabric 1.21.1 port of the original Bukkit/Spigot plugin by Kyzeragon.",
)
text = text.replace('"fabricloader": ">=0.19.3"', '"fabricloader": ">=0.16.14"')
text = text.replace('"minecraft": "~26.2"', '"minecraft": "~1.21.1"')
text = text.replace('"java": ">=25"', '"java": ">=21"')
mod_json.write_text(text, encoding="utf-8")

# Straightforward Mojang-mapping renames between 26.2 and 1.21.1.
for path in list((root / "src").rglob("*.java")):
    text = path.read_text(encoding="utf-8")
    text = text.replace("Minecraft 26.2", "Minecraft 1.21.1")
    text = text.replace(
        "net.minecraft.resources.Identifier",
        "net.minecraft.resources.ResourceLocation",
    )
    text = re.sub(r"\bIdentifier\b", "ResourceLocation", text)
    text = text.replace(".dimension().identifier()", ".dimension().location()")
    text = text.replace(
        "net.minecraft.world.entity.EntityTypes",
        "net.minecraft.world.entity.EntityType",
    )
    text = re.sub(r"\bEntityTypes\.", "EntityType.", text)
    text = text.replace(
        "net.minecraft.world.level.portal.TeleportTransition",
        "net.minecraft.world.level.portal.DimensionTransition",
    )
    text = re.sub(r"\bTeleportTransition\b", "DimensionTransition", text)
    path.write_text(text, encoding="utf-8")

# 1.21.1 builds custom entity types using an identifier string.
mod_entities = root / "src/main/java/io/github/kyzderp/armorstandpet/entity/ModEntities.java"
text = mod_entities.read_text(encoding="utf-8")
text = text.replace(
    "private static final ResourceKey<EntityType<?>> PET_KEY = ResourceKey.create(Registries.ENTITY_TYPE, PET_ID);\n\n",
    "",
)
text = text.replace("import net.minecraft.resources.ResourceKey;\n", "")
text = text.replace("import net.minecraft.core.registries.Registries;\n", "")
text = text.replace(
    "PET_KEY,\n\t\t\tEntityType.Builder",
    "PET_ID,\n\t\t\tEntityType.Builder",
)
text = text.replace(".build(PET_KEY));", ".build(PET_ID.toString()));")
mod_entities.write_text(text, encoding="utf-8")

# 1.21.1 entity persistence uses CompoundTag rather than ValueInput/ValueOutput.
entity_path = root / "src/main/java/io/github/kyzderp/armorstandpet/entity/PetArmorStandEntity.java"
entity = entity_path.read_text(encoding="utf-8")
entity = entity.replace("import com.mojang.serialization.Codec;\n", "")
entity = entity.replace("import net.minecraft.world.level.storage.ValueInput;\n", "")
entity = entity.replace("import net.minecraft.world.level.storage.ValueOutput;\n", "")
entity = entity.replace(
    "import net.minecraft.network.chat.Component;\n",
    "import net.minecraft.network.chat.Component;\n"
    "import net.minecraft.nbt.CompoundTag;\n"
    "import net.minecraft.nbt.ListTag;\n"
    "import net.minecraft.nbt.StringTag;\n"
    "import net.minecraft.nbt.Tag;\n",
)
old_hurt = """\t@Override
\tpublic boolean hurtServer(ServerLevel world, DamageSource source, float amount)
\t{
\t\treturn PetMortalityController.hurt(this, world, source, amount);
\t}
"""
new_hurt = """\t@Override
\tpublic boolean hurt(DamageSource source, float amount)
\t{
\t\tif (!(this.level() instanceof ServerLevel serverLevel))
\t\t\treturn false;
\t\treturn PetMortalityController.hurt(this, serverLevel, source, amount);
\t}
"""
if old_hurt not in entity:
    raise SystemExit("Could not find 26.2 hurtServer override")
entity = entity.replace(old_hurt, new_hurt, 1)
start = entity.index("\t@Override\n\tprotected void addAdditionalSaveData(")
end = entity.index(
    "\n\t// ------------------------------------------------------------------\n"
    "\t// Bukkit-ArmorStand-shaped convenience methods",
    start,
)
nbt_methods = """\t@Override
\tprotected void addAdditionalSaveData(CompoundTag tag)
\t{
\t\tsuper.addAdditionalSaveData(tag);
\t\tif (this.owner != null)
\t\t\ttag.putString(NBT_OWNER, this.owner);
\t\tif (this.petTypeName != null)
\t\t\ttag.putString(NBT_TYPE, this.petTypeName);
\t\ttag.putDouble(NBT_SPEED, this.speed);
\t\ttag.putDouble(NBT_GREET_RANGE, this.greetRange);
\t\ttag.put(NBT_ANNOUNCES, writeStrings(this.announces));
\t\ttag.put(NBT_INSULTS, writeStrings(this.insults));
\t\ttag.put(NBT_GREETINGS, writeStrings(this.greetings));
\t}

\t@Override
\tprotected void readAdditionalSaveData(CompoundTag tag)
\t{
\t\tsuper.readAdditionalSaveData(tag);
\t\tthis.owner = tag.contains(NBT_OWNER, Tag.TAG_STRING) ? tag.getString(NBT_OWNER) : null;
\t\tthis.petTypeName = tag.contains(NBT_TYPE, Tag.TAG_STRING) ? tag.getString(NBT_TYPE) : null;
\t\tthis.speed = tag.contains(NBT_SPEED, Tag.TAG_DOUBLE) ? tag.getDouble(NBT_SPEED) : 0.3;
\t\tthis.greetRange = tag.contains(NBT_GREET_RANGE, Tag.TAG_DOUBLE) ? tag.getDouble(NBT_GREET_RANGE) : 5.0;
\t\tthis.announces = readStrings(tag, NBT_ANNOUNCES);
\t\tthis.insults = readStrings(tag, NBT_INSULTS);
\t\tthis.greetings = readStrings(tag, NBT_GREETINGS);
\t}

\tprivate static ListTag writeStrings(List<String> values)
\t{
\t\tListTag list = new ListTag();
\t\tfor (String value : values)
\t\t\tlist.add(StringTag.valueOf(value));
\t\treturn list;
\t}

\tprivate static List<String> readStrings(CompoundTag tag, String key)
\t{
\t\tList<String> values = new ArrayList<>();
\t\tListTag list = tag.getList(key, Tag.TAG_STRING);
\t\tfor (int i = 0; i < list.size(); i++)
\t\t\tvalues.add(list.getString(i));
\t\treturn values;
\t}
"""
entity = entity[:start] + nbt_methods + entity[end:]
entity_path.write_text(entity, encoding="utf-8")

# 1.21.1's container click API uses ClickType.
gui_path = root / "src/main/java/io/github/kyzderp/armorstandpet/gui/ChooseTypeScreenHandler.java"
gui = gui_path.read_text(encoding="utf-8")
gui = gui.replace(
    "import net.minecraft.world.inventory.ContainerInput;\n",
    "import net.minecraft.world.inventory.ClickType;\n",
)
gui = gui.replace(
    "public void clicked(int slotIndex, int button, ContainerInput input, Player clicker)",
    "public void clicked(int slotIndex, int button, ClickType clickType, Player clicker)",
)
gui_path.write_text(gui, encoding="utf-8")

# 1.21.1 uses the pre-render-state armor stand renderer. No custom identity
# substitution is needed, so keep a thin vanilla subclass for behavior parity.
renderer_path = root / "src/client/java/io/github/kyzderp/armorstandpet/client/PetArmorStandRenderer.java"
renderer_path.write_text("""/*******************************************************************************
 * ArmorStandPet - Fabric 1.21.1 port
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.client;

import net.minecraft.client.renderer.entity.ArmorStandRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;

/** Uses the vanilla 1.21.1 armor-stand renderer for the custom pet entity. */
public final class PetArmorStandRenderer extends ArmorStandRenderer
{
\tpublic PetArmorStandRenderer(EntityRendererProvider.Context context)
\t{
\t\tsuper(context);
\t}
}
""", encoding="utf-8")

# Cross-dimension entity movement uses DimensionTransition.changeDimension in 1.21.1.
pet_path = root / "src/main/java/io/github/kyzderp/armorstandpet/types/Pet.java"
pet = pet_path.read_text(encoding="utf-8")
pet = pet.replace(
    "this.stand.teleport(new DimensionTransition(",
    "this.stand.changeDimension(new DimensionTransition(",
)
pet_path.write_text(pet, encoding="utf-8")

# 1.21.1 damage entry point and item durability API.
combat_path = root / "src/main/java/io/github/kyzderp/armorstandpet/combat/OwnerAttackCombatController.java"
combat = combat_path.read_text(encoding="utf-8")
combat = combat.replace(
    "boolean damaged = target.hurtServer(level, damageSource, attackDamage);",
    "boolean damaged = target.hurt(damageSource, attackDamage);",
)
old_item = """\t\t\tif (damaged && !weapon.isEmpty())
\t\t\t{
\t\t\t\tweapon.hurtEnemy(target, stand);
\t\t\t\tweapon.postHurtEnemy(target, stand);
\t\t\t\tEnchantmentHelper.doPostAttackEffectsWithItemSource(
\t\t\t\t\t\tlevel, target, damageSource, weapon);
\t\t\t}
"""
new_item = """\t\t\tif (damaged && !weapon.isEmpty())
\t\t\t{
\t\t\t\t// 1.21.1 restricts ItemStack.hurtEnemy/postHurtEnemy to Player.
\t\t\t\t// Apply the same one durability point and enchantment post-hit effects
\t\t\t\t// without inventing a fake player entity.
\t\t\t\tweapon.hurtAndBreak(1, stand, EquipmentSlot.MAINHAND);
\t\t\t\tEnchantmentHelper.doPostAttackEffectsWithItemSource(
\t\t\t\t\t\tlevel, target, damageSource, weapon);
\t\t\t}
"""
if old_item not in combat:
    raise SystemExit("Could not find 26.2 item post-hit block")
combat = combat.replace(old_item, new_item, 1)
combat = combat.replace(
    "import net.minecraft.world.entity.ai.attributes.Attributes;\n",
    "import net.minecraft.world.entity.ai.attributes.Attributes;\n"
    "import net.minecraft.world.entity.EquipmentSlot;\n",
)
combat_path.write_text(combat, encoding="utf-8")

# 1.21.1 item particles take an ItemStack.
mortality_path = root / "src/main/java/io/github/kyzderp/armorstandpet/combat/PetMortalityController.java"
mortality = mortality_path.read_text(encoding="utf-8")
mortality = mortality.replace(
    "import net.minecraft.world.item.Items;\n",
    "import net.minecraft.world.item.Items;\n"
    "import net.minecraft.world.item.ItemStack;\n",
)
mortality = mortality.replace(
    "new ItemParticleOption(ParticleTypes.ITEM, Items.ARMOR_STAND)",
    "new ItemParticleOption(ParticleTypes.ITEM, new ItemStack(Items.ARMOR_STAND))",
)
mortality_path.write_text(mortality, encoding="utf-8")

for path in list((root / "src").rglob("*.java")):
    text = path.read_text(encoding="utf-8").replace(
        "Minecraft 26.2", "Minecraft 1.21.1"
    )
    path.write_text(text, encoding="utf-8")

print("Applied clean Minecraft 1.21.1 compatibility port")
