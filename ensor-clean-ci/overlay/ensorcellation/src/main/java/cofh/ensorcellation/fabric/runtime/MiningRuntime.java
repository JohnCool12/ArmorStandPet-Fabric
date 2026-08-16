package cofh.ensorcellation.fabric.runtime;

import cofh.core.fabric.util.AreaEffectHelper;
import cofh.ensorcellation.fabric.enchantment.EnsorEnchantments;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Fabric counterpart of CoFH Core AreaEffectEvents for Air Affinity and Excavating. */
public final class MiningRuntime {
    private record PendingBreak(BlockPos origin, List<BlockPos> area) {}
    private record MiningTarget(BlockPos pos, Direction face) {}

    private static final Map<UUID, MiningTarget> LAST_TARGET = new ConcurrentHashMap<>();
    private static final Map<UUID, PendingBreak> PENDING = new ConcurrentHashMap<>();
    private static final ThreadLocal<Boolean> AREA_BREAK = ThreadLocal.withInitial(() -> false);

    public static void register() {
        AttackBlockCallback.EVENT.register((player, world, hand, pos, direction) -> {
            LAST_TARGET.put(player.getUUID(), new MiningTarget(pos.immutable(), direction));
            return InteractionResult.PASS;
        });

        PlayerBlockBreakEvents.BEFORE.register((world, player, pos, state, blockEntity) -> {
            if (AREA_BREAK.get()) return true;
            PENDING.remove(player.getUUID());
            int enchLevel = EnsorEnchantments.level(player.getMainHandItem(), world, "excavating");
            MiningTarget target = LAST_TARGET.get(player.getUUID());
            if (enchLevel > 0 && target != null && target.pos().equals(pos) && !player.isSecondaryUseActive()) {
                List<BlockPos> area = AreaEffectHelper.getExtraBlocks(world, player, pos, target.face(), enchLevel);
                if (!area.isEmpty()) PENDING.put(player.getUUID(), new PendingBreak(pos.immutable(), List.copyOf(area)));
            }
            return true;
        });

        PlayerBlockBreakEvents.AFTER.register((world, player, pos, state, blockEntity) -> {
            if (AREA_BREAK.get() || !(player instanceof ServerPlayer serverPlayer)) return;
            PendingBreak pending = PENDING.remove(player.getUUID());
            if (pending == null || !pending.origin().equals(pos) || pending.area().isEmpty()) return;
            AREA_BREAK.set(true);
            try {
                for (BlockPos extra : pending.area()) {
                    if (serverPlayer.getMainHandItem().isEmpty()) break;
                    serverPlayer.gameMode.destroyBlock(extra);
                }
            } finally {
                AREA_BREAK.set(false);
            }
        });
    }

    /** Mirrors the original Forge BreakSpeed event at Player#getDestroySpeed. */
    public static float modifyDestroySpeed(float original, Player player, BlockState state) {
        float result = original;
        ItemStack tool = player.getMainHandItem();

        // Air Affinity is an equipped head-armor enchantment in the original mod.
        int airAffinity = EnsorEnchantments.equipped(player, "air_affinity");
        if (airAffinity > 0 && !player.onGround()) result *= 5.0F;

        int excavating = EnsorEnchantments.level(tool, player.level(), "excavating");
        MiningTarget target = LAST_TARGET.get(player.getUUID());
        if (excavating <= 0 || target == null || player.isSecondaryUseActive()) return result;

        Level level = player.level();
        BlockPos pos = target.pos();
        if (!level.getBlockState(pos).equals(state)) return result;

        List<BlockPos> area = AreaEffectHelper.getExtraBlocks(level, player, pos, target.face(), excavating);
        return result * AreaEffectHelper.speedMultiplier(level, pos, area);
    }

    private MiningRuntime() {}
}
