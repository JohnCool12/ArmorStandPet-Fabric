package com.natamus.giantspawn.events;

import com.natamus.collective.functions.BlockPosFunctions;
import com.natamus.collective.functions.HashMapFunctions;
import com.natamus.giantspawn.config.ConfigHandler;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Giant;
import net.minecraft.world.level.Level;

import java.util.HashMap;
import java.util.concurrent.CopyOnWriteArrayList;

public class GiantEvent {
    private static final HashMap<Level, CopyOnWriteArrayList<Giant>> giants_per_world = new HashMap<>();
    private static final HashMap<Level, Integer> tickdelay_per_world = new HashMap<>();

    public static void onEntityJoin(Level level, Entity entity) {
        if (level.isClientSide) {
            return;
        }

        if (!(entity instanceof Giant)) {
            return;
        }

        if (!HashMapFunctions.computeIfAbsent(giants_per_world, level, k -> new CopyOnWriteArrayList<Giant>()).contains(entity)) {
            giants_per_world.get(level).add((Giant)entity);
        }

        Giant giant = (Giant)entity;

        giant.getAttribute(Attributes.FOLLOW_RANGE).setBaseValue(35.0D);
        giant.getAttribute(Attributes.MOVEMENT_SPEED).setBaseValue((double)0.23F * ConfigHandler.giantMovementSpeedModifier);
        giant.getAttribute(Attributes.ATTACK_DAMAGE).setBaseValue(3.0D * ConfigHandler.giantAttackDamageModifier);
        giant.getAttribute(Attributes.ARMOR).setBaseValue(2.0D);

        // A Giant is roughly six times the scale of a zombie. Its collision box
        // can cause the otherwise-zombie-like navigator to reject trivial
        // one-block rises before jump control gets a useful path node. Raising
        // step height to one block is a narrow geometry compensation; it does
        // not replace vanilla navigation or movement control.
        if (giant.getAttribute(Attributes.STEP_HEIGHT) != null) {
            giant.getAttribute(Attributes.STEP_HEIGHT).setBaseValue(1.0D);
        }
    }

    public static void onWorldTick(ServerLevel level) {
        int ticks = HashMapFunctions.computeIfAbsent(tickdelay_per_world, level, k -> 1);
        if (ticks % 20 != 0) {
            tickdelay_per_world.put(level, ticks + 1);
            return;
        }
        tickdelay_per_world.put(level, 1);

        if (!ConfigHandler.shouldBurnGiantsInDaylight) {
            return;
        }

        if (!level.isDay()) {
            return;
        }

        for (Giant giant : HashMapFunctions.computeIfAbsent(giants_per_world, level, k -> new CopyOnWriteArrayList<Giant>())) {
            if (giant.isAlive()) {
                if (!giant.isInWaterRainOrBubble()) {
                    if (giant.getItemBySlot(EquipmentSlot.HEAD).isEmpty()) {
                        BlockPos epos = giant.blockPosition();
                        if (BlockPosFunctions.isOnSurface(level, epos)) {
                            giant.setRemainingFireTicks(60);
                        }
                    }
                }
            }
            else {
                giants_per_world.get(level).remove(giant);
            }
        }
    }
}
