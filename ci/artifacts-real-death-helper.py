from pathlib import Path
import json


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, found {count}: {old[:120]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

# Add the custom permanent-use component needed by the compatibility code.
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

compat = Path('common/src/main/java/artifacts/compat/hardcorerevival')
compat.mkdir(parents=True, exist_ok=True)
(compat / 'HardcoreRevivalFinalDeathCompat.java').write_text(r'''package artifacts.compat.hardcorerevival;

import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.equipment.EquipmentHelper;
import artifacts.equipment.EquipmentSlotManager;
import artifacts.network.ChorusTotemUsedPacket;
import artifacts.network.NetworkHandler;
import artifacts.registry.ModDataComponents;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.portal.DimensionTransition;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public final class HardcoreRevivalFinalDeathCompat {

    private static final ThreadLocal<State> FINAL_DEATH = new ThreadLocal<>();
    private static final Map<UUID, PendingRespawnTotem> PENDING_RESPAWN = new ConcurrentHashMap<>();

    private HardcoreRevivalFinalDeathCompat() {
    }

    public static void captureEquippedTotem(Player player) {
        ItemStack equippedTotem = EquipmentHelper.reduceAbilities(
                ModDataComponents.DEATH_PROTECTION_TELEPORT.get(),
                player,
                true,
                true,
                ItemStack.EMPTY,
                (DeathProtectionTeleport ability, ItemStack stack, ItemStack result) ->
                        result.isEmpty() && stack.has(ModDataComponents.CHORUS_TOTEM_USES.get()) ? stack : result
        );
        FINAL_DEATH.set(new State(player, equippedTotem, false));
    }

    public static ItemStack getCapturedTotem(Player player) {
        State state = FINAL_DEATH.get();
        return state != null && state.player() == player ? state.totem() : ItemStack.EMPTY;
    }

    public static boolean isHandlingFinalDeath(LivingEntity entity) {
        State state = FINAL_DEATH.get();
        return state != null && state.player() == entity;
    }

    public static void suppressGeneric(Player player) {
        State state = FINAL_DEATH.get();
        if (state != null && state.player() == player) {
            FINAL_DEATH.set(new State(state.player(), state.totem(), true));
        }
    }

    public static boolean shouldSuppress(LivingEntity entity) {
        State state = FINAL_DEATH.get();
        return state != null && state.player() == entity && state.suppress();
    }

    public static boolean hasValidPersonalSpawn(ServerPlayer player) {
        if (player.getRespawnPosition() == null) {
            return false;
        }
        if (player.server.getLevel(player.getRespawnDimension()) == null) {
            return false;
        }

        // Validate without consuming a Respawn Anchor charge. The actual death respawn
        // uses Minecraft's normal false/alive path later and consumes the charge once.
        DimensionTransition respawn = player.findRespawnPositionAndUseSpawnBlock(true, DimensionTransition.DO_NOTHING);
        return !respawn.missingRespawnBlock();
    }

    public static void prepareRealDeath(ServerPlayer player, ItemStack equippedTotem) {
        int usesLeft = equippedTotem.getOrDefault(ModDataComponents.CHORUS_TOTEM_USES.get(), 3);
        ItemStack survivingTotem = ItemStack.EMPTY;
        if (usesLeft > 1) {
            survivingTotem = equippedTotem.copy();
            survivingTotem.set(ModDataComponents.CHORUS_TOTEM_USES.get(), usesLeft - 1);
        }

        // Remove the equipped stack before the fatal hit so grave/death-inventory mods
        // never see the Chorus Totem as part of the dying player's belongings.
        equippedTotem.setCount(0);
        PENDING_RESPAWN.put(player.getUUID(), new PendingRespawnTotem(survivingTotem));
    }

    public static void restorePending(ServerPlayer player) {
        PendingRespawnTotem pending = PENDING_RESPAWN.remove(player.getUUID());
        if (pending == null) {
            return;
        }

        ItemStack stack = pending.stack();
        if (!stack.isEmpty()) {
            ItemStack toEquip = stack.copy();
            if (!EquipmentSlotManager.tryEquipAccessory(player, toEquip)) {
                if (!player.getInventory().add(toEquip)) {
                    player.drop(toEquip, false);
                }
            }
        }

        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);
        NetworkHandler.sendToPlayer(player, new ChorusTotemUsedPacket());
    }

    public static void restoreIfDeathWasPrevented(ServerPlayer player) {
        if (player.isAlive() && PENDING_RESPAWN.containsKey(player.getUUID())) {
            restorePending(player);
        }
    }

    public static void clear(Player player) {
        State state = FINAL_DEATH.get();
        if (state != null && state.player() == player) {
            FINAL_DEATH.remove();
        }
    }

    private record State(Player player, ItemStack totem, boolean suppress) {
    }

    private record PendingRespawnTotem(ItemStack stack) {
    }
}
''', encoding='utf-8')

mixin_dir = Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival')
mixin_dir.mkdir(parents=True, exist_ok=True)
(mixin_dir / 'HardcoreRevivalManagerMixin.java').write_text(r'''package artifacts.mixin.compat.hardcorerevival;

import artifacts.compat.hardcorerevival.HardcoreRevivalFinalDeathCompat;
import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.network.ChorusTotemUsedPacket;
import artifacts.network.NetworkHandler;
import artifacts.registry.ModDataComponents;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
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
        HardcoreRevivalFinalDeathCompat.captureEquippedTotem(player);
    }

    @Inject(
            method = "notRescuedInTime",
            at = @At(
                    value = "INVOKE",
                    target = "Lnet/blay09/mods/hardcorerevival/HardcoreRevivalManager;reset(Lnet/minecraft/world/entity/player/Player;)V",
                    shift = At.Shift.AFTER,
                    remap = false
            ),
            cancellable = true,
            remap = false,
            require = 0
    )
    private static void artifacts$handleAfterReset(Player player, CallbackInfo ci) {
        if (!(player instanceof ServerPlayer serverPlayer)) {
            return;
        }

        ItemStack totem = HardcoreRevivalFinalDeathCompat.getCapturedTotem(player);
        if (totem.isEmpty()) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }

        Object component = totem.get(ModDataComponents.DEATH_PROTECTION_TELEPORT.get());
        if (!(component instanceof DeathProtectionTeleport ability)) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }

        double chance = ability.teleportationChance().get();
        if (chance <= player.getRandom().nextDouble()) {
            HardcoreRevivalFinalDeathCompat.suppressGeneric(player);
            return;
        }

        if (HardcoreRevivalFinalDeathCompat.hasValidPersonalSpawn(serverPlayer)) {
            HardcoreRevivalFinalDeathCompat.prepareRealDeath(serverPlayer, totem);
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }

        // No valid personal spawn: preserve V7 behavior (prevent death and use the
        // Chorus Totem teleport routine, which falls back to random teleportation).
        if (!(player.level() instanceof ServerLevel level)) {
            HardcoreRevivalFinalDeathCompat.clear(player);
            return;
        }

        DeathProtectionTeleport.teleport(player, level);
        int usesLeft = totem.getOrDefault(ModDataComponents.CHORUS_TOTEM_USES.get(), 3);
        if (usesLeft <= 1) {
            totem.shrink(1);
        } else {
            totem.set(ModDataComponents.CHORUS_TOTEM_USES.get(), usesLeft - 1);
        }

        int healthRestored = ability.healthRestored().get();
        player.setHealth(Math.min(player.getMaxHealth(), Math.max(1, healthRestored)));
        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 1F, 1F);
        NetworkHandler.sendToPlayer(serverPlayer, new ChorusTotemUsedPacket());

        HardcoreRevivalFinalDeathCompat.clear(player);
        ci.cancel();
    }

    @Inject(method = "notRescuedInTime", at = @At("RETURN"), remap = false, require = 0)
    private static void artifacts$clear(Player player, CallbackInfo ci) {
        if (player instanceof ServerPlayer serverPlayer) {
            HardcoreRevivalFinalDeathCompat.restoreIfDeathWasPrevented(serverPlayer);
        }
        HardcoreRevivalFinalDeathCompat.clear(player);
    }
}
''', encoding='utf-8')

(mixin_dir / 'PlayerListRespawnMixin.java').write_text(r'''package artifacts.mixin.compat.hardcorerevival;

import artifacts.compat.hardcorerevival.HardcoreRevivalFinalDeathCompat;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(PlayerList.class)
public abstract class PlayerListRespawnMixin {

    @Inject(method = "respawn", at = @At("RETURN"))
    private void artifacts$restoreChorusTotemAfterRealRespawn(
            ServerPlayer oldPlayer,
            boolean keepEverything,
            Entity.RemovalReason removalReason,
            CallbackInfoReturnable<ServerPlayer> cir
    ) {
        ServerPlayer newPlayer = cir.getReturnValue();
        if (newPlayer != null) {
            HardcoreRevivalFinalDeathCompat.restorePending(newPlayer);
        }
    }
}
''', encoding='utf-8')

p = Path('common/src/main/resources/mixins.artifacts.common.json')
data = json.loads(p.read_text(encoding='utf-8'))
mixins = data['mixins']
for name in [
    'compat.hardcorerevival.HardcoreRevivalManagerMixin',
    'compat.hardcorerevival.PlayerListRespawnMixin',
]:
    if name not in mixins:
        mixins.append(name)
p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
