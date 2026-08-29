from pathlib import Path

ROOT = Path('project/src/main/java')


def replace_method(text: str, marker: str, replacement: str) -> str:
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError(f'method marker not found: {marker}')
    # include the directly associated @Override when present
    start = text.rfind('\n', 0, idx) + 1
    probe = start
    prev_start = text.rfind('\n', 0, max(0, start - 1)) + 1
    if text[prev_start:start].strip() == '@Override':
        start = prev_start
    brace = text.find('{', idx)
    if brace < 0:
        raise RuntimeError(f'opening brace not found: {marker}')
    depth = 0
    i = brace
    in_string = False
    in_char = False
    escape = False
    while i < len(text):
        c = text[i]
        if escape:
            escape = False
        elif c == '\\' and (in_string or in_char):
            escape = True
        elif c == '"' and not in_char:
            in_string = not in_string
        elif c == "'" and not in_string:
            in_char = not in_char
        elif not in_string and not in_char:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    # consume one trailing newline for stable formatting
                    if end < len(text) and text[end] == '\n':
                        end += 1
                    return text[:start] + replacement.rstrip() + '\n' + text[end:]
        i += 1
    raise RuntimeError(f'unbalanced method: {marker}')


def remove_method(text: str, marker: str) -> str:
    return replace_method(text, marker, '')


# 26.1 ContainerListener is a menu listener, not a SimpleContainer listener.
p = ROOT / 'com/mcmoddev/golems/entity/IExtraGolem.java'
s = p.read_text()
s = s.replace('import net.minecraft.world.inventory.ContainerListener;\n', '')
s = s.replace('IInventoryProvider, ContainerListener, RangedAttackMob', 'IInventoryProvider, RangedAttackMob')
p.write_text(s)

# Core entity migration. These signatures/implementations are grounded in the exact
# minecraft-patched-26.1.2.95 ABI and in the previously compiled 26.1 Extra Golems jar.
p = ROOT / 'com/mcmoddev/golems/entity/GolemBase.java'
s = p.read_text()

s = replace_method(s, 'public boolean isSunBurnTickAccessor()', '''\t@Override
\tpublic boolean isSunBurnTickAccessor() {
\t\treturn this.level().getSkyDarken() < 4 && this.level().canSeeSky(this.blockPosition());
\t}''')

s = replace_method(s, 'public boolean canAttackType(final EntityType<?> type)', '''\t@Override
\tpublic boolean canAttack(final LivingEntity target) {
\t\tfinal EntityType<?> type = target.getType();
\t\tif (type == EntityType.PLAYER && this.isPlayerCreated() && !ExtraGolems.CONFIG.enableFriendlyFire()) {
\t\t\treturn false;
\t\t}
\t\tif (type == EntityType.VILLAGER || type == EGRegistry.EntityReg.GOLEM.get()
\t\t\t\t|| type == EntityType.IRON_GOLEM || type == EntityType.SNOW_GOLEM) {
\t\t\treturn false;
\t\t}
\t\treturn super.canAttack(target);
\t}''')

s = replace_method(s, 'protected ResourceKey<net.minecraft.world.level.storage.loot.LootTable> getDefaultLootTable()', '''\t@Override
\tprotected void dropFromLootTable(final ServerLevel level, final DamageSource source, final boolean recentlyHit) {
\t\tfinal Optional<GolemContainer> oContainer = getContainer();
\t\tif (oContainer.isEmpty()) {
\t\t\tsuper.dropFromLootTable(level, source, recentlyHit);
\t\t\treturn;
\t\t}
\t\tfinal ResourceKey<net.minecraft.world.level.storage.loot.LootTable> table = ResourceKey.create(
\t\t\t\tnet.minecraft.core.registries.Registries.LOOT_TABLE, oContainer.get().getLootTable());
\t\tthis.dropFromLootTable(level, source, recentlyHit, table);
\t}''')

s = replace_method(s, 'public void customServerAiStep()', '''\t@Override
\tpublic void customServerAiStep(final ServerLevel level) {
\t\tsuper.customServerAiStep(level);
\t\tfinal Optional<GolemContainer> oContainer = getContainer();
\t\tif (oContainer.isEmpty()) {
\t\t\treturn;
\t\t}
\t\tfinal GolemContainer container = oContainer.get();
\t\tif (this.isInWater()
\t\t\t\t&& container.getAttributes().isWeakTo(level().registryAccess(), ImmutableSet.of(DamageTypes.DROWN))) {
\t\t\tthis.hurt(this.damageSources().drown(), 1.0F);
\t\t}
\t\tif (level.environmentAttributes().getValue(net.minecraft.world.attribute.EnvironmentAttributes.SNOW_GOLEM_MELTS,
\t\t\t\tthis.position())
\t\t\t\t&& container.getAttributes().isWeakTo(level().registryAccess(),
\t\t\t\t\t\tImmutableSet.of(DamageTypes.IN_FIRE, DamageTypes.ON_FIRE))) {
\t\t\tthis.hurt(this.damageSources().onFire(), 1.0F);
\t\t}
\t\tcontainer.getBehaviors().getActiveBehaviors(this).forEach(b -> b.onTick(this));
\t}''')

s = replace_method(s, 'public boolean isInvulnerableTo(DamageSource pSource)', '''\t@Override
\tpublic boolean isInvulnerableTo(final ServerLevel level, final DamageSource pSource) {
\t\tif (super.isInvulnerableTo(level, pSource)) {
\t\t\treturn true;
\t\t}
\t\tfinal Optional<GolemContainer> oContainer = getContainer();
\t\tif (oContainer.isEmpty()) {
\t\t\treturn false;
\t\t}
\t\tfinal RegistryAccess registryAccess = level.registryAccess();
\t\tfinal Optional<ResourceKey<DamageType>> oTypeKey = pSource.typeHolder().unwrapKey();
\t\treturn oTypeKey.isPresent()
\t\t\t\t&& oContainer.get().getAttributes().isImmuneTo(registryAccess, ImmutableSet.of(oTypeKey.get()));
\t}''')

s = replace_method(s, 'public boolean causeFallDamage(float distance, float damageMultiplier, DamageSource source)', '''\t@Override
\tpublic boolean causeFallDamage(final double distance, final float damageMultiplier, final DamageSource source) {
\t\tfinal Optional<GolemContainer> oContainer = getContainer();
\t\tif (oContainer.isEmpty()) {
\t\t\treturn super.causeFallDamage(distance, damageMultiplier, source);
\t\t}
\t\tif (oContainer.get().getAttributes().isWeakTo(level().registryAccess(), ImmutableSet.of(DamageTypes.FALL))) {
\t\t\tfinal int i = this.calculateFallDamage(distance, damageMultiplier);
\t\t\tif (i > 0) {
\t\t\t\tfinal SoundEvent sound = i > 4 ? this.getFallSounds().big() : this.getFallSounds().small();
\t\t\t\tthis.playSound(sound, 1.0F, 1.0F);
\t\t\t\tthis.playBlockFallSound();
\t\t\t\tthis.hurt(this.damageSources().fall(), (float) i);
\t\t\t\treturn true;
\t\t\t}
\t\t}
\t\treturn false;
\t}''')

s = replace_method(s, 'public boolean doHurtTarget(Entity target)', '''\t@Override
\tpublic boolean doHurtTarget(final ServerLevel level, final Entity target) {
\t\tif (super.doHurtTarget(level, target)) {
\t\t\tgetContainer().ifPresent(container -> {
\t\t\t\tfinal double knockback = container.getAttributes().getAttackKnockback();
\t\t\t\tif (knockback > 0 && !isBaby()) {
\t\t\t\t\tfinal Vec3 myPos = this.position();
\t\t\t\t\tfinal Vec3 ePos = target.position();
\t\t\t\t\tfinal double dX = Math.signum(ePos.x - myPos.x) * knockback;
\t\t\t\t\tfinal double dZ = Math.signum(ePos.z - myPos.z) * knockback;
\t\t\t\t\ttarget.setDeltaMovement(target.getDeltaMovement().add(dX, knockback / 2, dZ));
\t\t\t\t}
\t\t\t\tif (isEffectiveAi()) {
\t\t\t\t\tcontainer.getBehaviors().getActiveBehaviors(this).forEach(b -> b.onAttack(this, target));
\t\t\t\t}
\t\t\t});
\t\t\treturn true;
\t\t}
\t\treturn false;
\t}''')

s = replace_method(s, 'protected void actuallyHurt(DamageSource source, float amount)', '''\t@Override
\tprotected void actuallyHurt(final ServerLevel level, final DamageSource source, final float amount) {
\t\tsuper.actuallyHurt(level, source, amount);
\t\tif (isEffectiveAi()) {
\t\t\tgetContainer().ifPresent(container -> container.getBehaviors().getActiveBehaviors(this)
\t\t\t\t\t.forEach(b -> b.onActuallyHurt(this, source, amount)));
\t\t}
\t}''')

s = replace_method(s, 'public void readAdditionalSaveData(final CompoundTag tag)', '''\t@Override
\tprotected void readAdditionalSaveData(final net.minecraft.world.level.storage.ValueInput input) {
\t\tsuper.readAdditionalSaveData(input);
\t\tfinal CompoundTag tag = input.read("ExtraGolemsData", CompoundTag.CODEC).orElseGet(CompoundTag::new);
\t\treadContainer(tag);
\t\treadVariant(tag);
\t\tthis.setBaby(tag.getBooleanOr(KEY_CHILD, false));
\t\tsetupInventory();
\t\tthis.readInventoryFromTag(input);
\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onReadData(this, tag)));
\t}''')

s = remove_method(s, 'public void readInventory(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries)')
s = remove_method(s, 'public void writeInventory(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries)')

s = replace_method(s, 'public void addAdditionalSaveData(final CompoundTag tag)', '''\t@Override
\tprotected void addAdditionalSaveData(final net.minecraft.world.level.storage.ValueOutput output) {
\t\tsuper.addAdditionalSaveData(output);
\t\tfinal CompoundTag tag = new CompoundTag();
\t\twriteContainer(tag);
\t\twriteVariant(tag);
\t\ttag.putBoolean(KEY_CHILD, this.isBaby());
\t\tthis.getContainer().ifPresent(container -> container.getBehaviors().forEach(b -> b.onWriteData(this, tag)));
\t\toutput.store("ExtraGolemsData", CompoundTag.CODEC, tag);
\t\tthis.writeInventoryToTag(output);
\t}''')

s = replace_method(s, 'public void setupInventory()', '''\t@Override
\tpublic void setupInventory() {
\t\tfinal SimpleContainer old = this.inventory;
\t\tthis.inventory = new SimpleContainer(INVENTORY_SIZE);
\t\tif (old != null) {
\t\t\tfinal int size = Math.min(old.getContainerSize(), this.inventory.getContainerSize());
\t\t\tfor (int i = 0; i < size; ++i) {
\t\t\t\tfinal ItemStack stack = old.getItem(i);
\t\t\t\tif (!stack.isEmpty()) {
\t\t\t\t\tthis.inventory.setItem(i, stack.copy());
\t\t\t\t}
\t\t\t}
\t\t}
\t\tthis.isInventoryChanged = true;
\t}''')

s = replace_method(s, 'public boolean wantsToPickUp(ItemStack stack)', '''\t@Override
\tpublic boolean wantsToPickUp(final ServerLevel level, final ItemStack stack) {
\t\tif (stack.isEmpty()) {
\t\t\treturn false;
\t\t}
\t\tfinal Optional<GolemContainer> oContainer = getContainer();
\t\tif (oContainer.isEmpty()) {
\t\t\treturn false;
\t\t}
\t\tif (isEffectiveAi() && !wantsToPickup.test(stack)) {
\t\t\treturn false;
\t\t}
\t\treturn getInventory().canAddItem(stack);
\t}''')

s = replace_method(s, 'protected void dropEquipment()', '''\t@Override
\tprotected void dropEquipment(final ServerLevel level) {
\t\tsuper.dropEquipment(level);
\t\tContainers.dropContents(this.level(), this.blockPosition(), this.inventory);
\t}''')

s = replace_method(s, 'protected void pickUpItem(ItemEntity item)', '''\t@Override
\tprotected void pickUpItem(final ServerLevel level, final ItemEntity item) {
\t\tInventoryCarrier.pickUpItem(level, this, this, item);
\t}''')

s = replace_method(s, 'public void containerChanged(Container container)', '''\tpublic void containerChanged(final Container container) {
\t\tif (container == this.inventory) {
\t\t\tthis.isInventoryChanged = true;
\t\t}
\t}''')

p.write_text(s)

# Item#use now receives Level directly; preserve the exact native guide opener.
p = ROOT / 'com/mcmoddev/golems/item/GuideBookItem.java'
s = p.read_text().replace('if (player.getCommandSenderWorld().isClientSide()) {', 'if (level.isClientSide()) {')
p.write_text(s)

print('Applied exact 26.1.2 GolemBase/inventory/NBT semantic migration')
