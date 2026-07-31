/*******************************************************************************
 * ArmorStandPet - Fabric port
 * Original Bukkit plugin (c) 2016, 2017 Hannah Chu
 *******************************************************************************/
package io.github.kyzderp.armorstandpet.gui;

import io.github.kyzderp.armorstandpet.ASPetMod;
import io.github.kyzderp.armorstandpet.Lang;
import io.github.kyzderp.armorstandpet.Settings;
import io.github.kyzderp.armorstandpet.actions.NotBusyAction;
import io.github.kyzderp.armorstandpet.entity.PetArmorStandEntity;
import io.github.kyzderp.armorstandpet.entity.StandFactory;
import io.github.kyzderp.armorstandpet.storage.PetConfigDoesNotExistException;
import io.github.kyzderp.armorstandpet.storage.PetSettings;
import io.github.kyzderp.armorstandpet.storage.PetStorage;
import io.github.kyzderp.armorstandpet.storage.PlayerFileDoesNotExistException;
import io.github.kyzderp.armorstandpet.struct.OwnerToPet;
import io.github.kyzderp.armorstandpet.struct.StandToOwner;
import io.github.kyzderp.armorstandpet.types.Pet;
import io.github.kyzderp.armorstandpet.types.PetType;
import io.github.kyzderp.armorstandpet.util.ColorUtil;
import io.github.kyzderp.armorstandpet.util.PermissionUtil;

import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.HopperMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemLore;

/**
 * Vanilla hopper-menu based pet type picker.
 *
 * Minecraft 26.2 no longer reliably preserves legacy-formatted custom item
 * names through every menu-click path. The previous implementation tried to
 * recover the selected PetType by reading the clicked ItemStack's hover name;
 * when that lookup failed it returned silently, leaving the GUI open and doing
 * nothing. The server now stores the PetType assigned to each displayed slot
 * when the menu is built, so selection does not depend on text formatting.
 */
public class ChooseTypeScreenHandler extends HopperMenu
{
    private static final int PICKER_SIZE = 5;

    private final ServerPlayer player;
    private final ArmorStand rawStand;
    private final String worldname;
    private final PetType[] slotTypes;
    private boolean handled = false;

    private ChooseTypeScreenHandler(int syncId, Inventory playerInventory,
            ServerPlayer player, ArmorStand rawStand, PickerContents contents)
    {
        super(syncId, playerInventory, contents.inventory);
        this.player = player;
        this.rawStand = rawStand;
        this.worldname = rawStand.level().dimension().identifier().toString();
        this.slotTypes = contents.slotTypes;
    }

    public static void open(ServerPlayer player, ArmorStand rawStand)
    {
        PickerContents contents = buildContents(player);

        MenuProvider factory = new MenuProvider()
        {
            @Override
            public Component getDisplayName()
            {
                return Component.literal("ArmorStandPet Type");
            }

            @Override
            public AbstractContainerMenu createMenu(int syncId, Inventory inventory, Player menuPlayer)
            {
                return new ChooseTypeScreenHandler(syncId, inventory, player, rawStand, contents);
            }
        };

        player.openMenu(factory);
    }

    private static PickerContents buildContents(ServerPlayer player)
    {
        SimpleContainer inventory = new SimpleContainer(PICKER_SIZE);
        PetType[] slotTypes = new PetType[PICKER_SIZE];
        int slot = 0;

        for (PetType type : PetType.values())
        {
            String typeName = type.name().toLowerCase();
            Boolean enabled = Settings.typeEnables.get(typeName);
            if (enabled == null || !enabled
                    || !PermissionUtil.hasPermission(player.createCommandSourceStack(),
                            "armorstandpet.type." + typeName))
            {
                continue;
            }

            if (slot >= PICKER_SIZE)
                break;

            ItemStack stack = new ItemStack(type.item, 1);
            stack.set(DataComponents.CUSTOM_NAME, ColorUtil.rawText("\u00A7a" + type.name));
            stack.set(DataComponents.LORE,
                    new ItemLore(type.lore.stream().map(ColorUtil::rawText).toList()));

            inventory.setItem(slot, stack);
            slotTypes[slot] = type;
            slot++;
        }

        return new PickerContents(inventory, slotTypes);
    }

    @Override
    public void clicked(int slotIndex, int button, ContainerInput input, Player clicker)
    {
        if (this.handled || slotIndex < 0 || slotIndex >= PICKER_SIZE)
            return;

        PetType type = this.slotTypes[slotIndex];
        if (type == null)
        {
            ASPetMod.LOGGER.warn("Ignored ArmorStandPet picker click from {} in unmapped slot {}",
                    this.player.getName().getString(), slotIndex);
            return;
        }

        this.handled = true;
        try
        {
            this.handleTypeSelection(type);
            if (clicker instanceof ServerPlayer serverPlayer)
                serverPlayer.closeContainer();
        }
        catch (RuntimeException exception)
        {
            this.handled = false;
            ASPetMod.LOGGER.error("Failed to create ArmorStandPet type {} for {}",
                    type.name, this.player.getName().getString(), exception);
            ASPetMod.error(this.player,
                    "Could not create that ArmorStandPet. Check the server log for details.");
        }
    }

    private void handleTypeSelection(PetType type)
    {
        Pet previousPet = OwnerToPet.get(this.worldname, this.player.getName().getString());
        if (previousPet != null)
            PetStorage.savePets(new PetSettings(this.player.getName().getString(), previousPet, this.worldname));

        PetArmorStandEntity petStand;
        if (this.rawStand instanceof PetArmorStandEntity existingPetStand)
        {
            petStand = existingPetStand;
        }
        else
        {
            petStand = StandFactory.claimFrom(this.player.level(), this.rawStand,
                    this.player.getName().getString(), type);
        }

        Pet pet;
        try
        {
            pet = PetStorage.loadPetSettings(this.player.getName().getString(), this.worldname,
                    type, petStand);
            if (Settings.DEBUG)
                ASPetMod.LOGGER.info("Loaded existing pet for " + this.player.getName().getString());
        }
        catch (PlayerFileDoesNotExistException | PetConfigDoesNotExistException exception)
        {
            pet = Pet.createPet(type, this.player.getName().getString(), petStand);
            if (Settings.DEBUG)
                ASPetMod.LOGGER.info("No existing config found for " + this.player.getName().getString());
        }

        OwnerToPet.put(this.worldname, this.player.getName().getString(), pet);
        StandToOwner.put(this.worldname, petStand, this.player.getName().getString());

        ASPetMod.LOGGER.info("Player " + this.player.getName().getString() + " created a new pet: "
                + type.name + " at " + pet.getLocationString());
        ASPetMod.inform(this.player, Lang.get("newPet"));
        pet.stand();
        pet.faceOwner();
        pet.isBusy = true;
        pet.say(pet.getInitialMessage(), new NotBusyAction(pet, null));
    }

    private static final class PickerContents
    {
        private final SimpleContainer inventory;
        private final PetType[] slotTypes;

        private PickerContents(SimpleContainer inventory, PetType[] slotTypes)
        {
            this.inventory = inventory;
            this.slotTypes = slotTypes;
        }
    }
}
