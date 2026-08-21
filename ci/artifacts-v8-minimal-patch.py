from pathlib import Path
import json


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, found {count}: {old[:100]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

# --- Permanent 3-use Chorus Totem ---
replace_once(
    'common/src/main/java/artifacts/registry/ModDataComponents.java',
    'import net.minecraft.network.RegistryFriendlyByteBuf;\nimport net.minecraft.network.codec.StreamCodec;',
    'import net.minecraft.network.RegistryFriendlyByteBuf;\nimport net.minecraft.network.codec.ByteBufCodecs;\nimport net.minecraft.network.codec.StreamCodec;'
)
replace_once(
    'common/src/main/java/artifacts/registry/ModDataComponents.java',
    '    public static final Supplier<DataComponentType<Value<Boolean>>> HIDE_WHEN_INVISIBLE = registerSynced("hide_when_invisible", ValueTypes.enabledField().codec(), ValueTypes.BOOLEAN.streamCodec());\n',
    '    public static final Supplier<DataComponentType<Value<Boolean>>> HIDE_WHEN_INVISIBLE = registerSynced("hide_when_invisible", ValueTypes.enabledField().codec(), ValueTypes.BOOLEAN.streamCodec());\n'
    '    public static final Supplier<DataComponentType<Integer>> CHORUS_TOTEM_USES = registerSynced("chorus_totem_uses", Codec.intRange(1, 3), ByteBufCodecs.INT);\n'
)
replace_once(
    'common/src/main/java/artifacts/registry/ModItems.java',
    '    public static final Holder<Item> CHORUS_TOTEM = wearableItem("chorus_totem", builder -> builder\n'
    '            .component(ModDataComponents.DEATH_PROTECTION_TELEPORT.get(), new DeathProtectionTeleport(',
    '    public static final Holder<Item> CHORUS_TOTEM = wearableItem("chorus_totem", builder -> builder\n'
    '            .component(ModDataComponents.CHORUS_TOTEM_USES.get(), 3)\n'
    '            .component(ModDataComponents.DEATH_PROTECTION_TELEPORT.get(), new DeathProtectionTeleport('
)

replace_once(
    'common/src/main/java/artifacts/mixin/ability/deathprotectionteleport/LivingEntityMixin.java',
    'import net.minecraft.tags.DamageTypeTags;\n',
    ''
)
replace_once(
    'common/src/main/java/artifacts/mixin/ability/deathprotectionteleport/LivingEntityMixin.java',
    '        if (!totem.isEmpty()\n'
    '                && entity.level() instanceof ServerLevel level\n'
    '                && !damageSource.is(DamageTypeTags.BYPASSES_INVULNERABILITY)\n'
    '        ) {',
    '        if (!totem.isEmpty()\n'
    '                && entity.level() instanceof ServerLevel level\n'
    '        ) {'
)
replace_once(
    'common/src/main/java/artifacts/mixin/ability/deathprotectionteleport/LivingEntityMixin.java',
    '                    if (ability.consumedOnUse().get()) {\n'
    '                        totem.shrink(1);\n'
    '                    } else if (entity instanceof Player player) {\n'
    '                        player.getCooldowns().addCooldown(totem.getItem(), ability.cooldown().get() * 20);\n'
    '                    }',
    '                    int usesLeft = totem.getOrDefault(ModDataComponents.CHORUS_TOTEM_USES.get(), 3);\n'
    '                    if (usesLeft <= 1) {\n'
    '                        totem.shrink(1);\n'
    '                    } else {\n'
    '                        totem.set(ModDataComponents.CHORUS_TOTEM_USES.get(), usesLeft - 1);\n'
    '                    }'
)

replace_once(
    'common/src/main/java/artifacts/item/WearableArtifactItem.java',
    '    public void appendHoverText(ItemStack itemStack, TooltipContext tooltipContext, List<Component> list, TooltipFlag tooltipFlag) {\n'
    '        if (Artifacts.CONFIG.client.showTooltips.get()',
    '    public void appendHoverText(ItemStack itemStack, TooltipContext tooltipContext, List<Component> list, TooltipFlag tooltipFlag) {\n'
    '        Integer chorusTotemUses = itemStack.get(ModDataComponents.CHORUS_TOTEM_USES.get());\n'
    '        if (chorusTotemUses != null) {\n'
    '            list.add(Component.translatable("artifacts.tooltip.chorus_totem_uses", chorusTotemUses).withStyle(ChatFormatting.LIGHT_PURPLE));\n'
    '        }\n\n'
    '        if (Artifacts.CONFIG.client.showTooltips.get()'
)

lang = Path('common/src/generated/resources/assets/artifacts/lang/en_us.json')
lang_text = lang.read_text(encoding='utf-8')
if '"artifacts.tooltip.chorus_totem_uses"' not in lang_text:
    lang_text = lang_text.replace(
        '  "item.artifacts.chorus_totem": "Chorus Totem",',
        '  "item.artifacts.chorus_totem": "Chorus Totem",\n  "artifacts.tooltip.chorus_totem_uses": "%s uses left",',
        1
    )
lang.write_text(lang_text, encoding='utf-8')

replace_once(
    'common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java',
    'import net.minecraft.server.level.ServerLevel;\n',
    'import net.minecraft.server.level.ServerLevel;\nimport net.minecraft.server.level.ServerPlayer;\n'
)
replace_once(
    'common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java',
    'import net.minecraft.world.level.gameevent.GameEvent;\n',
    'import net.minecraft.world.level.gameevent.GameEvent;\nimport net.minecraft.world.level.portal.DimensionTransition;\n'
)
replace_once(
    'common/src/main/java/artifacts/component/ability/DeathProtectionTeleport.java',
    '''    public static void teleport(LivingEntity entity, ServerLevel level) {\n        double oldX = entity.getX();\n        double oldY = entity.getY();\n        double oldZ = entity.getZ();\n\n        for (int i = 0; i < 32; ++i) {\n''',
    '''    public static void teleport(LivingEntity entity, ServerLevel level) {\n        double oldX = entity.getX();\n        double oldY = entity.getY();\n        double oldZ = entity.getZ();\n\n        if (entity instanceof ServerPlayer player && player.getRespawnPosition() != null) {\n            DimensionTransition respawn = player.findRespawnPositionAndUseSpawnBlock(false, DimensionTransition.DO_NOTHING);\n            if (!respawn.missingRespawnBlock()) {\n                if (player.isPassenger()) {\n                    player.stopRiding();\n                }\n\n                ServerLevel oldLevel = level;\n                player.teleportTo(respawn.newLevel(), respawn.pos().x, respawn.pos().y, respawn.pos().z, respawn.yRot(), respawn.xRot());\n                oldLevel.playSound(null, oldX, oldY, oldZ, SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                player.serverLevel().playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.CHORUS_FRUIT_TELEPORT, SoundSource.PLAYERS, 1, 1);\n                return;\n            }\n        }\n\n        for (int i = 0; i < 32; ++i) {\n'''
)

compat = Path('common/src/main/java/artifacts/compat/hardcorerevival')
compat.mkdir(parents=True, exist_ok=True)
(compat / 'HardcoreRevivalFinalDeathCompat.java').write_text(r'''package artifacts.compat.hardcorerevival;

import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.equipment.EquipmentHelper;
import artifacts.network.ChorusTotemUsedPacket;
import artifacts.network.NetworkHandler;
import artifacts.registry.ModDataComponents;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

public final class HardcoreRevivalFinalDeathCompat {
    private static final ThreadLocal<State> FINAL_DEATH = new ThreadLocal<>();

    private HardcoreRevivalFinalDeathCompat() {
    }

    public static void capture(Player player) {
        ItemStack found = ItemStack.EMPTY;
        for (InteractionHand hand : InteractionHand.values()) {
            ItemStack stack = player.getItemInHand(hand);
            DeathProtectionTeleport ability = stack.get(ModDataComponents.DEATH_PROTECTION_TELEPORT.get());
            if (!stack.has(ModDataComponents.DISABLED_BY_TOGGLE.get())
                    && ability != null && ability.isNonCosmetic()
                    && stack.has(ModDataComponents.CHORUS_TOTEM_USES.get())
                    && !player.getCooldowns().isOnCooldown(stack.getItem())) {
                found = stack;
                break;
            }
        }

        if (found.isEmpty()) {
            found = EquipmentHelper.reduceAbilities(
                    ModDataComponents.DEATH_PROTECTION_TELEPORT.get(),
                    player,
                    true,
                    true,
                    ItemStack.EMPTY,
                    (ability, stack, result) ->
                            result.isEmpty() && stack.has(ModDataComponents.CHORUS_TOTEM_USES.get()) ? stack : result
            );
        }
        FINAL_DEATH.set(new State(player, found));
    }

    public static ItemStack captured(Player player) {
        State state = FINAL_DEATH.get();
        return state != null && state.player() == player ? state.stack() : ItemStack.EMPTY;
    }

    public static void clear(Player player) {
        State state = FINAL_DEATH.get();
        if (state != null && state.player() == player) {
            FINAL_DEATH.remove();
        }
    }

    public static void schedulePostTeleportEffects(ServerPlayer player) {
        player.server.execute(() -> {
            ServerPlayer live = player.server.getPlayerList().getPlayer(player.getUUID());
            if (live == null || !live.isAlive()) {
                return;
            }
            live.serverLevel().playSound(null, live.getX(), live.getY(), live.getZ(),
                    SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);
            NetworkHandler.sendToPlayer(live, new ChorusTotemUsedPacket());
        });
    }

    private record State(Player player, ItemStack stack) {
    }
}
''', encoding='utf-8')

mixin_dir = Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival')
mixin_dir.mkdir(parents=True, exist_ok=True)
(mixin_dir / 'HardcoreRevivalManagerMixin.java').write_text(r'''package artifacts.mixin.compat.hardcorerevival;

import artifacts.compat.hardcorerevival.HardcoreRevivalFinalDeathCompat;
import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.registry.ModDataComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Pseudo
@Mixin(targets = "net.blay09.mods.hardcorerevival.HardcoreRevivalManager", remap = false)
public abstract class HardcoreRevivalManagerMixin {
    @Inject(method = "notRescuedInTime", at = @At("HEAD"), remap = false, require = 0)
    private static void artifacts$capture(Player player, CallbackInfo ci) {
        HardcoreRevivalFinalDeathCompat.capture(player);
    }

    @Inject(
            method = "notRescuedInTime",
            at = @At(value = "INVOKE",
                    target = "Lnet/blay09/mods/hardcorerevival/HardcoreRevivalManager;reset(Lnet/minecraft/class_1657;)V",
                    shift = At.Shift.AFTER,
                    remap = false),
            cancellable = true,
            remap = false,
            require = 0
    )
    private static void artifacts$saveAfterReset(Player player, CallbackInfo ci) {
        if (!(player instanceof ServerPlayer serverPlayer)) return;
        ItemStack totem = HardcoreRevivalFinalDeathCompat.captured(player);
        if (totem.isEmpty()) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }
        DeathProtectionTeleport ability = totem.get(ModDataComponents.DEATH_PROTECTION_TELEPORT.get());
        if (ability == null || ability.teleportationChance().get() <= player.getRandom().nextDouble()) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }
        if (!(player.level() instanceof ServerLevel level)) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }

        DeathProtectionTeleport.teleport(player, level);
        int usesLeft = totem.getOrDefault(ModDataComponents.CHORUS_TOTEM_USES.get(), 3);
        if (usesLeft <= 1) totem.shrink(1);
        else totem.set(ModDataComponents.CHORUS_TOTEM_USES.get(), usesLeft - 1);

        int restored = ability.healthRestored().get();
        player.setHealth(Math.min(player.getMaxHealth(), Math.max(1, restored)));
        HardcoreRevivalFinalDeathCompat.clear(player);
        HardcoreRevivalFinalDeathCompat.schedulePostTeleportEffects(serverPlayer);
        ci.cancel();
    }

    @Inject(method = "notRescuedInTime", at = @At("RETURN"), remap = false, require = 0)
    private static void artifacts$clear(Player player, CallbackInfo ci) {
        HardcoreRevivalFinalDeathCompat.clear(player);
    }
}
''', encoding='utf-8')

(mixin_dir / 'DeathProtectionTeleportKnockoutOnlyMixin.java').write_text(r'''package artifacts.mixin.compat.hardcorerevival;

import artifacts.component.ability.DeathProtectionTeleport;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = DeathProtectionTeleport.class, remap = false)
public abstract class DeathProtectionTeleportKnockoutOnlyMixin {
    @Inject(method = "findTotem", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private static void artifacts$deferPlayerDeathProtectionToHardcoreRevival(
            LivingEntity entity, CallbackInfoReturnable<ItemStack> cir) {
        if (entity instanceof Player) cir.setReturnValue(ItemStack.EMPTY);
    }
}
''', encoding='utf-8')

p = Path('common/src/main/resources/mixins.artifacts.common.json')
data = json.loads(p.read_text(encoding='utf-8'))
for name in [
    'compat.hardcorerevival.HardcoreRevivalManagerMixin',
    'compat.hardcorerevival.DeathProtectionTeleportKnockoutOnlyMixin',
]:
    if name not in data['mixins']:
        data['mixins'].append(name)
p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

for tag in [
    Path('common/src/generated/resources/data/hardcorerevival/tags/item/passthrough_death_when_held.json'),
    Path('common/src/main/resources/data/hardcorerevival/tags/item/passthrough_death_when_held.json'),
]:
    if tag.exists():
        tag.unlink()
