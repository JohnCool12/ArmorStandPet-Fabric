from pathlib import Path

p=Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival/KnockoutHandlerMixin.java')
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text('''package artifacts.mixin.compat.hardcorerevival;

import artifacts.component.ability.DeathProtectionTeleport;
import artifacts.equipment.EquipmentHelper;
import artifacts.network.ChorusTotemUsedPacket;
import artifacts.network.NetworkHandler;
import artifacts.registry.ModDataComponents;
import com.llamalad7.mixinextras.sugar.Local;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

@Pseudo
@Mixin(targets="net.blay09.mods.hardcorerevival.handler.KnockoutHandler",remap=false)
public abstract class KnockoutHandlerMixin {
    @Unique private static final ThreadLocal<ServerPlayer> artifacts$preventKnockout=new ThreadLocal<>();

    @ModifyArg(method="onPlayerDamage",at=@At(value="INVOKE",target="Lnet/blay09/mods/balm/api/event/LivingDamageEvent;setDamageAmount(F)V",remap=false),index=0,remap=false,require=0)
    private static float artifacts$activate(float amount,@Local(ordinal=0) ServerPlayer player){
        ItemStack totem=EquipmentHelper.reduceAbilities(ModDataComponents.DEATH_PROTECTION_TELEPORT.get(),player,true,true,ItemStack.EMPTY,(ability,stack,result)->result.isEmpty()?stack:result);
        if(totem.isEmpty()||!(player.level() instanceof ServerLevel level)) return amount;
        if(!(totem.get(ModDataComponents.DEATH_PROTECTION_TELEPORT.get()) instanceof DeathProtectionTeleport ability)) return amount;
        if(ability.teleportationChance().get()<=player.getRandom().nextDouble()) return amount;
        DeathProtectionTeleport.teleport(player,level);
        int uses=totem.getOrDefault(ModDataComponents.CHORUS_TOTEM_USES.get(),3);
        if(uses<=1) totem.shrink(1); else totem.set(ModDataComponents.CHORUS_TOTEM_USES.get(),uses-1);
        player.setHealth(Math.min(player.getMaxHealth(),Math.max(1,ability.healthRestored().get())));
        player.level().playSound(player,player.getX(),player.getY(),player.getZ(),SoundEvents.TOTEM_USE,SoundSource.PLAYERS,1,1);
        NetworkHandler.sendToPlayer(player,new ChorusTotemUsedPacket());
        artifacts$preventKnockout.set(player);
        return 0F;
    }

    public static boolean artifacts$consumePreventKnockout(ServerPlayer player){
        ServerPlayer pending=artifacts$preventKnockout.get();
        artifacts$preventKnockout.remove();
        return pending==player;
    }
}
''',encoding='utf-8')

p2=Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival/HardcoreRevivalManagerMixin.java')
p2.write_text('''package artifacts.mixin.compat.hardcorerevival;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Pseudo
@Mixin(targets="net.blay09.mods.hardcorerevival.HardcoreRevivalManager",remap=false)
public abstract class HardcoreRevivalManagerMixin {
    @Inject(method="knockout",at=@At("HEAD"),cancellable=true,remap=false,require=0)
    private static void artifacts$skip(Player player,DamageSource source,CallbackInfo ci){
        if(player instanceof ServerPlayer serverPlayer&&KnockoutHandlerMixin.artifacts$consumePreventKnockout(serverPlayer)) ci.cancel();
    }
}
''',encoding='utf-8')

m=Path('common/src/main/resources/mixins.artifacts.common.json')
s=m.read_text(encoding='utf-8')
s=s.replace('    "compat.hardcorerevival.KnockoutHandlerMixin",\n','    "compat.hardcorerevival.KnockoutHandlerMixin",\n    "compat.hardcorerevival.HardcoreRevivalManagerMixin",\n',1)
m.write_text(s,encoding='utf-8')
