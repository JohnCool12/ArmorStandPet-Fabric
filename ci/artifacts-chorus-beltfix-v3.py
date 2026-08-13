from pathlib import Path

u=Path('common/src/main/java/artifacts/integration/hardcorerevival/HardcoreRevivalCompat.java')
u.parent.mkdir(parents=True,exist_ok=True)
u.write_text('''package artifacts.integration.hardcorerevival;

import net.minecraft.server.level.ServerPlayer;

public final class HardcoreRevivalCompat {
    private static final ThreadLocal<ServerPlayer> PREVENT_NEXT_KNOCKOUT=new ThreadLocal<>();
    private HardcoreRevivalCompat(){}
    public static void preventNextKnockout(ServerPlayer player){PREVENT_NEXT_KNOCKOUT.set(player);}
    public static boolean consumePreventNextKnockout(ServerPlayer player){
        ServerPlayer pending=PREVENT_NEXT_KNOCKOUT.get();
        PREVENT_NEXT_KNOCKOUT.remove();
        return pending==player;
    }
}
''',encoding='utf-8')

p=Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival/KnockoutHandlerMixin.java')
s=p.read_text(encoding='utf-8')
s=s.replace('import artifacts.equipment.EquipmentHelper;\n','import artifacts.equipment.EquipmentHelper;\nimport artifacts.integration.hardcorerevival.HardcoreRevivalCompat;\n',1)
s=s.replace('import org.spongepowered.asm.mixin.Unique;\n','',1)
s=s.replace('    @Unique private static final ThreadLocal<ServerPlayer> artifacts$preventKnockout=new ThreadLocal<>();\n\n','',1)
s=s.replace('        artifacts$preventKnockout.set(player);','        HardcoreRevivalCompat.preventNextKnockout(player);',1)
s=s.replace('''\n    public static boolean artifacts$consumePreventKnockout(ServerPlayer player){
        ServerPlayer pending=artifacts$preventKnockout.get();
        artifacts$preventKnockout.remove();
        return pending==player;
    }
''','\n',1)
p.write_text(s,encoding='utf-8')

p=Path('common/src/main/java/artifacts/mixin/compat/hardcorerevival/HardcoreRevivalManagerMixin.java')
s=p.read_text(encoding='utf-8')
s=s.replace('package artifacts.mixin.compat.hardcorerevival;\n\n','package artifacts.mixin.compat.hardcorerevival;\n\nimport artifacts.integration.hardcorerevival.HardcoreRevivalCompat;\n',1)
s=s.replace('KnockoutHandlerMixin.artifacts$consumePreventKnockout(serverPlayer)','HardcoreRevivalCompat.consumePreventNextKnockout(serverPlayer)',1)
p.write_text(s,encoding='utf-8')
