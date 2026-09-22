from pathlib import Path
import re

root = Path('project/src/main/java')

def p(rel): return root / rel

def edit(rel, fn):
    f=p(rel); s=f.read_text(); n=fn(s); f.write_text(n)

def replace(rel, *pairs):
    def fn(s):
        for a,b in pairs: s=s.replace(a,b)
        return s
    edit(rel,fn)

# Minecraft 26.1 exact signatures
replace('com/mcmoddev/golems/block/UtilityBlock.java',
        ('net.minecraft.world.level.block.entity.InsideBlockEffectApplier','net.minecraft.world.entity.InsideBlockEffectApplier'),
        ('@Override protected void fallOn','@Override public void fallOn'),
        ('@Override protected boolean isPossibleToRespawnInThis','@Override public boolean isPossibleToRespawnInThis'))

replace('com/mcmoddev/golems/data/golem/BuildingBlocks.java',
        ('this.cachedBlocks.add(BuiltInRegistries.BLOCK.get(id));','this.cachedBlocks.add(BuiltInRegistries.BLOCK.getValue(id));'))

replace('com/mcmoddev/golems/entity/GolemBase.java',
        ('public boolean causeFallDamage(float distance, float damageMultiplier, DamageSource source)',
         'public boolean causeFallDamage(double distance, float damageMultiplier, DamageSource source)'))

# Preserve the old behavior NBT keys at the entity root despite ValueInput/ValueOutput.
def save_compat(s):
    old='''\t\tCompoundTag behaviorTag = input.read("ExtraGolemsBehaviorData", CompoundTag.CODEC).orElseGet(CompoundTag::new);\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onReadData(this, behaviorTag)));'''
    new='''\t\tCompoundTag behaviorTag = new CompoundTag();\n\t\tinput.getInt("Ammo").ifPresent(v -> behaviorTag.putInt("Ammo", v));\n\t\tinput.read("ExplodeData", CompoundTag.CODEC).ifPresent(v -> behaviorTag.put("ExplodeData", v));\n\t\tinput.read("FuelData", CompoundTag.CODEC).ifPresent(v -> behaviorTag.put("FuelData", v));\n\t\t// Also accept the briefly-used nested format from early 26.1 port builds.\n\t\tinput.read("ExtraGolemsBehaviorData", CompoundTag.CODEC).ifPresent(behaviorTag::merge);\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onReadData(this, behaviorTag)));'''
    s=s.replace(old,new)
    old2='''\t\tCompoundTag behaviorTag = new CompoundTag();\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onWriteData(this, behaviorTag)));\n\t\tif (!behaviorTag.isEmpty()) output.store("ExtraGolemsBehaviorData", CompoundTag.CODEC, behaviorTag);'''
    new2='''\t\tCompoundTag behaviorTag = new CompoundTag();\n\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(bh -> bh.onWriteData(this, behaviorTag)));\n\t\tif (behaviorTag.contains("Ammo")) output.putInt("Ammo", behaviorTag.getIntOr("Ammo", 0));\n\t\tif (behaviorTag.contains("ExplodeData")) output.store("ExplodeData", CompoundTag.CODEC, behaviorTag.getCompoundOrEmpty("ExplodeData"));\n\t\tif (behaviorTag.contains("FuelData")) output.store("FuelData", CompoundTag.CODEC, behaviorTag.getCompoundOrEmpty("FuelData"));'''
    return s.replace(old2,new2)
edit('com/mcmoddev/golems/entity/GolemBase.java', save_compat)

# Tooltip API now emits through a Consumer and includes TooltipDisplay.
def tooltip(s):
    s=s.replace('import net.minecraft.world.item.TooltipFlag;', 'import net.minecraft.world.item.TooltipFlag;\nimport net.minecraft.world.item.component.TooltipDisplay;\nimport java.util.function.Consumer;')
    s=s.replace('public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag)',
                'public void appendHoverText(ItemStack stack, TooltipContext context, TooltipDisplay display, Consumer<Component> tooltip, TooltipFlag flag)')
    s=s.replace('tooltip.add(Component.translatable(getDescriptionId() + ".tooltip", name));','tooltip.accept(Component.translatable(getDescriptionId() + ".tooltip", name));')
    return s
edit('com/mcmoddev/golems/item/SpawnGolemItem.java', tooltip)

# TagKey kept location(); ResourceKey changed to identifier().
replace('com/mcmoddev/golems/data/behavior/TemptBehavior.java',
        ('value.left().get().identifier()','value.left().get().location()'))

# TargetingConditions.test now needs the ServerLevel as first argument.
for rel, who in [
    ('com/mcmoddev/golems/data/behavior/SetFireBehavior.java','self'),
    ('com/mcmoddev/golems/data/behavior/util/TargetedMobEffects.java','mob')]:
    def targetfix(s, who=who):
        if 'import net.minecraft.server.level.ServerLevel;' not in s:
            # Insert after package/import area using a stable Minecraft import.
            anchor='import net.minecraft'
            idx=s.find(anchor)
            s=s[:idx]+'import net.minecraft.server.level.ServerLevel;\n'+s[idx:]
        old=f'{who}.level().getEntities(net.minecraft.world.level.entity.EntityTypeTest.forClass(LivingEntity.class), {who}.getBoundingBox().inflate(radius), target -> condition.test({who}, target))'
        new=f'({who}.level() instanceof ServerLevel serverLevel ? serverLevel.getEntities(net.minecraft.world.level.entity.EntityTypeTest.forClass(LivingEntity.class), {who}.getBoundingBox().inflate(radius), target -> condition.test(serverLevel, {who}, target)) : java.util.List.of())'
        return s.replace(old,new)
    edit(rel,targetfix)

# Mob wantsToPickUp has ServerLevel in 26.1.
def itemgoal(s):
    if 'import net.minecraft.server.level.ServerLevel;' not in s:
        s=s.replace('import net.minecraft.world.entity.Mob;','import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.world.entity.Mob;')
    s=s.replace('entity.wantsToPickUp(e.getItem())','entity.level() instanceof ServerLevel serverLevel && entity.wantsToPickUp(serverLevel, e.getItem())')
    return s
edit('com/mcmoddev/golems/entity/goal/MoveToItemGoal.java', itemgoal)

# NeoForge mod file API exposes the root path; resolve the embedded pack beneath it.
replace('com/mcmoddev/golems/integration/AddonLoader.java',
        ('getFile().findResource("/" + packName)','getFile().getFilePath().resolve(packName)'))

# TOP should not import Jade UI classes.
edit('com/mcmoddev/golems/integration/TOPDescriptionManager.java', lambda s: s.replace('import snownee.jade.api.ui.IElement;\n',''))

# Jade 26.1 no longer exposes the old IElement/getIcon API. Keep all tooltip text integration;
# remove only the obsolete icon override until the replacement extension point is compiled against.
def jade(s):
    s=s.replace('import org.jetbrains.annotations.Nullable;\n','').replace('import snownee.jade.api.ui.IElement;\n','').replace('import snownee.jade.impl.ui.ItemStackElement;\n','')
    s=re.sub(r'\n\t\t@Override\n\t\tpublic @Nullable IElement getIcon\(EntityAccessor accessor, IPluginConfig config, IElement currentIcon\) \{.*?\n\t\t\}\n', '\n', s, flags=re.S)
    return s
edit('com/mcmoddev/golems/integration/JadeDescriptionManager.java', jade)

# Missing imports introduced by the command migration.
def cmd(s):
    imports='import net.minecraft.server.permissions.Permissions;\nimport net.minecraft.util.ProblemReporter;\nimport net.minecraft.world.level.storage.TagValueInput;\n'
    if 'import net.minecraft.server.permissions.Permissions;' not in s:
        s=s.replace('import net.minecraft.resources.Identifier;\n', 'import net.minecraft.resources.Identifier;\n'+imports)
    return s
edit('com/mcmoddev/golems/network/SummonGolemCommand.java', cmd)

print('Applied pass 3: common/gameplay compile fixes + behavior-save compatibility.')
