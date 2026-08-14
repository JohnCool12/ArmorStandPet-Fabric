from pathlib import Path
import json

root = Path('project')
modjson = root / 'src/main/resources/fabric.mod.json'
testjava = root / 'src/main/java/com/mcmoddev/golems/test/VillagePretrackingInitializationGameTest.java'

data = json.loads(modjson.read_text())
entries = data.setdefault('entrypoints', {}).setdefault('fabric-gametest', [])
entry = 'com.mcmoddev.golems.test.VillagePretrackingInitializationGameTest'
if entry not in entries:
    entries.append(entry)
modjson.write_text(json.dumps(data, indent=2) + '\n')

testjava.parent.mkdir(parents=True, exist_ok=True)
testjava.write_text(r'''package com.mcmoddev.golems.test;

import com.mcmoddev.golems.EGRegistry;
import com.mcmoddev.golems.entity.GolemBase;
import net.fabricmc.fabric.api.gametest.v1.FabricGameTest;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;

public final class VillagePretrackingInitializationGameTest implements FabricGameTest {
    @GameTest(template = FabricGameTest.EMPTY_STRUCTURE, timeoutTicks = 40)
    public void villageReplacementMaterialExistsBeforeEntityIsAdded(final GameTestHelper helper) {
        final ResourceLocation obsidian = ResourceLocation.fromNamespaceAndPath("golems", "obsidian");

        // This is the exact construction phase used by SpawnUtil: EntityType#create returns
        // a brand-new entity that has NOT yet been inserted into the ServerLevel. The scoped
        // village material must already be visible at that point.
        GolemBase.beginVillageSummonInitialization(obsidian);
        final GolemBase replacement;
        try {
            replacement = EGRegistry.EntityReg.GOLEM.get().create(helper.getLevel());
        } finally {
            GolemBase.endVillageSummonInitialization();
        }

        helper.assertTrue(replacement != null, "Failed to create village replacement Extra Golem");
        helper.assertTrue(helper.getLevel().getEntity(replacement.getId()) == null,
                "Replacement was unexpectedly already inserted into the world");
        helper.assertTrue(replacement.getGolemId().isPresent(),
                "Replacement has no material ID before world insertion");
        helper.assertTrue(replacement.getGolemId().orElseThrow().equals(obsidian),
                "Replacement material ID was not initialized before world insertion");
        helper.assertTrue(replacement.getContainer().isPresent(),
                "Replacement container cannot resolve before world insertion");

        helper.getLevel().addFreshEntity(replacement);
        helper.assertTrue(helper.getLevel().getEntity(replacement.getId()) == replacement,
                "Replacement failed to enter the world after pre-initialization");
        helper.assertTrue(replacement.getGolemId().orElseThrow().equals(obsidian),
                "Replacement material changed after world insertion");

        // The ThreadLocal must be strictly scoped to this SpawnUtil invocation. A normal
        // Extra Golem created immediately afterward must still begin unconfigured.
        final GolemBase unrelated = EGRegistry.EntityReg.GOLEM.get().create(helper.getLevel());
        helper.assertTrue(unrelated != null, "Failed to create unrelated Extra Golem");
        helper.assertTrue(unrelated.getGolemId().isEmpty(),
                "Village material initialization leaked into unrelated entity creation");

        replacement.discard();
        unrelated.discard();
        helper.succeed();
    }
}
''')
print('Injected village replacement pre-tracking initialization GameTest.')
