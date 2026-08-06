package com.kyanite.deeperdarker.util.registry;

import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * Fabric registry bootstrap that mirrors the useful lazy semantics of the
 * original NeoForge declarations without depending on NeoForge classes.
 */
public class DDDeferredRegister<T> {
    protected final Registry<T> registry;
    protected final ResourceKey<? extends Registry<T>> registryKey;
    protected final String namespace;
    protected final List<DDRegistryEntry<? extends T>> entries = new ArrayList<>();
    private boolean registered;

    protected DDDeferredRegister(Registry<T> registry, ResourceKey<? extends Registry<T>> registryKey, String namespace) {
        this.registry = registry;
        this.registryKey = registryKey;
        this.namespace = namespace;
    }

    @SuppressWarnings("unchecked")
    public static <T> DDDeferredRegister<T> create(ResourceKey<? extends Registry<T>> registryKey, String namespace) {
        Registry<T> registry = (Registry<T>) BuiltInRegistries.REGISTRY.get(registryKey.location());
        if (registry == null) throw new IllegalArgumentException("Unknown built-in registry: " + registryKey.location());
        return new DDDeferredRegister<>(registry, registryKey, namespace);
    }

    public static Blocks createBlocks(String namespace) {
        return new Blocks(namespace);
    }

    public static Items createItems(String namespace) {
        return new Items(namespace);
    }

    public static DDDeferredRegister<DataComponentType<?>> createDataComponents(
            ResourceKey<? extends Registry<DataComponentType<?>>> registryKey, String namespace) {
        return create(registryKey, namespace);
    }

    public <I extends T> DDRegistryEntry<I> register(String name, Supplier<? extends I> factory) {
        DDRegistryEntry<I> entry = new DDRegistryEntry<>((Registry<I>) registry,
                (ResourceKey<? extends Registry<I>>) registryKey,
                ResourceLocation.fromNamespaceAndPath(namespace, name), factory);
        entries.add(entry);
        return entry;
    }

    public void registerAll() {
        if (registered) return;
        registered = true;
        for (DDRegistryEntry<? extends T> rawEntry : entries) {
            registerEntry(rawEntry);
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private void registerEntry(DDRegistryEntry<? extends T> rawEntry) {
        DDRegistryEntry entry = rawEntry;
        Object value = entry.create();
        Object registeredValue = Registry.register((Registry) registry, entry.getId(), value);
        entry.bind(registeredValue);
    }

    public static final class Blocks extends DDDeferredRegister<Block> {
        private Blocks(String namespace) {
            super(BuiltInRegistries.BLOCK, Registries.BLOCK, namespace);
        }

        @Override
        public <I extends Block> DDBlockEntry<I> register(String name, Supplier<? extends I> factory) {
            DDBlockEntry<I> entry = new DDBlockEntry<>((Registry<I>) registry,
                    (ResourceKey<? extends Registry<I>>) registryKey,
                    ResourceLocation.fromNamespaceAndPath(namespace, name), factory);
            super.entries.add(entry);
            return entry;
        }
    }

    public static final class Items extends DDDeferredRegister<Item> {
        private Items(String namespace) {
            super(BuiltInRegistries.ITEM, Registries.ITEM, namespace);
        }

        @Override
        public <I extends Item> DDItemEntry<I> register(String name, Supplier<? extends I> factory) {
            DDItemEntry<I> entry = new DDItemEntry<>((Registry<I>) registry,
                    (ResourceKey<? extends Registry<I>>) registryKey,
                    ResourceLocation.fromNamespaceAndPath(namespace, name), factory);
            super.entries.add(entry);
            return entry;
        }

        public DDItemEntry<Item> registerSimpleItem(String name) {
            return register(name, () -> new Item(new Item.Properties()));
        }

        public DDItemEntry<Item> registerSimpleItem(String name, Item.Properties properties) {
            return register(name, () -> new Item(properties));
        }

        public DDItemEntry<BlockItem> registerSimpleBlockItem(String name, Supplier<? extends Block> block) {
            return registerSimpleBlockItem(name, block, new Item.Properties());
        }

        public DDItemEntry<BlockItem> registerSimpleBlockItem(String name, Supplier<? extends Block> block,
                                                               Item.Properties properties) {
            return register(name, () -> new BlockItem(block.get(), properties));
        }
    }
}
