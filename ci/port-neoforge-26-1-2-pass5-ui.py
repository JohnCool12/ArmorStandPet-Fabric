from pathlib import Path
import re

root=Path('project/src/main/java/com/mcmoddev/golems/client')

def edit(rel, fn):
    p=root/rel; s=p.read_text(); p.write_text(fn(s))

def write(rel,s):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s)

# Last renderer compile error: copyFrom disappeared; PartPose is the native replacement.
edit('entity/GolemModel.java', lambda s: s.replace('this.ears.copyFrom(this.root().getChild("head"));','this.ears.loadPose(this.root().getChild("head").storePose());'))

# Page rendering is extraction-based in 26.1.
for rel in [
    'menu/guide_book/page/BookPage.java','menu/guide_book/page/TitleAndBodyPage.java',
    'menu/guide_book/page/GolemDescriptionPage.java','menu/guide_book/page/GolemDiagramPage.java',
    'menu/guide_book/page/TableOfContentsPage.java','menu/guide_book/page/CraftingRecipePage.java']:
    def common(s):
        s=s.replace('import net.minecraft.client.gui.GuiGraphics;','import net.minecraft.client.gui.GuiGraphicsExtractor;')
        s=s.replace('GuiGraphics graphics','GuiGraphicsExtractor graphics')
        s=s.replace('graphics.drawString(', 'graphics.text(')
        s=s.replace('graphics.drawWordWrap(', 'graphics.textWithWordWrap(')
        s=s.replace('graphics.renderItem(', 'graphics.item(')
        s=s.replace('graphics.pose().pushPose();','graphics.pose().pushMatrix();').replace('graphics.pose().popPose();','graphics.pose().popMatrix();')
        return s
    edit(rel,common)

# Native GUI pipeline arguments and known image dimensions.
def bookpage(s):
    # text() keeps the old no-shadow choice; use opaque black explicitly.
    s=s.replace('graphics.text(font, pageText, posX - font.width(pageText) / 2, posY, 0, false);','graphics.text(font, pageText, posX - font.width(pageText) / 2, posY, 0xFF000000, false);')
    return s
edit('menu/guide_book/page/BookPage.java',bookpage)

def titlebody(s):
    s=s.replace('graphics.text(font, title, posX, posY, 0, false);','graphics.text(font, title, posX, posY, 0xFF000000, false);')
    s=s.replace('graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0);','graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0xFF000000);')
    return s
edit('menu/guide_book/page/TitleAndBodyPage.java',titlebody)

def desc(s):
    if 'import net.minecraft.client.renderer.RenderPipelines;' not in s:
        s=s.replace('import net.minecraft.client.gui.components.Button;','import net.minecraft.client.gui.components.Button;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('graphics.textWithWordWrap(font, title, posX, posY, maxWidth, 0);','graphics.textWithWordWrap(font, title, posX, posY, maxWidth, 0xFF000000);')
    s=s.replace('graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0);','graphics.textWithWordWrap(font, body, posX, posY, maxWidth, 0xFF000000);')
    s=s.replace('graphics.blit(entry.getImage(), posX, posY, 0, 0, IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_HEIGHT);','graphics.blit(RenderPipelines.GUI_TEXTURED, entry.getImage(), posX, posY, 0.0F, 0.0F, IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_HEIGHT);')
    return s
edit('menu/guide_book/page/GolemDescriptionPage.java',desc)

# Diagram only needed API/name conversion; uniform Matrix3x2 scale is supported.

def tocpage(s):
    if 'import net.minecraft.client.renderer.RenderPipelines;' not in s:
        s=s.replace('import net.minecraft.client.gui.components.Button;','import net.minecraft.client.gui.components.Button;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('graphics.blit(texture, x + padding, y + padding * 2, tableU, tableV, tableWidth, tableHeight);','graphics.blit(RenderPipelines.GUI_TEXTURED, texture, x + padding, y + padding * 2, tableU, tableV, tableWidth, tableHeight, 256, 256);')
    return s
edit('menu/guide_book/page/TableOfContentsPage.java',tocpage)

# Recipe page now consumes the recipe's exact visual ingredients directly. Full recipes are no longer synced client-side in 26.1.
def recipepage(s):
    if 'import net.minecraft.client.renderer.RenderPipelines;' not in s:
        s=s.replace('import net.minecraft.client.gui.components.Button;','import net.minecraft.client.gui.components.Button;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('import net.minecraft.client.Minecraft;\n','').replace('import net.minecraft.world.item.crafting.CraftingRecipe;\n','')
    s=s.replace('graphics.blit(texture, bx, by, u, v, imageWidth, imageHeight);','graphics.blit(RenderPipelines.GUI_TEXTURED, texture, bx, by, u, v, imageWidth, imageHeight, 256, 256);')
    s=s.replace('private final CraftingRecipe recipe;','private final List<Ingredient> ingredients;\n\t\tprivate final ItemStack result;')
    s=s.replace('public Builder(IBookScreen parent, int page, CraftingRecipe recipe) {\n\t\t\tsuper(parent, page);\n\t\t\tthis.recipe = recipe;', 'public Builder(IBookScreen parent, int page, List<Ingredient> ingredients, ItemStack result) {\n\t\t\tsuper(parent, page);\n\t\t\tthis.ingredients = List.copyOf(ingredients);\n\t\t\tthis.result = result.copy();')
    s=s.replace('final List<Ingredient> ingredients = recipe.getIngredients();\n','')
    s=s.replace('final ItemStack result = recipe.getResultItem(Minecraft.getInstance().level.registryAccess());\n','')
    return s
edit('menu/guide_book/page/CraftingRecipePage.java',recipepage)

# Cycling button: Ingredient exposes a holder stream; render via extraction.
def cycle(s):
    s=s.replace('import net.minecraft.client.gui.GuiGraphics;','import net.minecraft.client.gui.GuiGraphicsExtractor;')
    s=s.replace('this(builder, ImmutableList.copyOf(ingredient.getItems()), scale);','this(builder, ingredient.items().map(ItemStack::new).toList(), scale);')
    s=s.replace('this.index = index;','this.index = index;',1)
    s=s.replace('this.itemStack = ItemStack.EMPTY;\n\t\tthis.setIndex(0);','this.itemStack = ItemStack.EMPTY;\n\t\tthis.index = -1;\n\t\tthis.setIndex(0);')
    s=s.replace('protected void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float partialTick)', 'protected void extractContents(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTick)')
    s=s.replace('graphics.pose().pushPose();','graphics.pose().pushMatrix();').replace('graphics.pose().popPose();','graphics.pose().popMatrix();')
    s=s.replace('graphics.renderItem(', 'graphics.item(')
    return s
edit('menu/button/CyclingItemButton.java',cycle)

# TOC button extraction.
def tocbutton(s):
    s=s.replace('import net.minecraft.client.gui.GuiGraphics;','import net.minecraft.client.gui.GuiGraphicsExtractor;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('public void renderWidget(final GuiGraphics graphics, int mouseX, int mouseY, float partialTicks)', 'protected void extractContents(final GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks)')
    s=s.replace('graphics.blit(this.texture, this.getX(), this.getY(), this.u, vOffset, this.width, this.height);','graphics.blit(RenderPipelines.GUI_TEXTURED, this.texture, this.getX(), this.getY(), this.u, vOffset, this.width, this.height, 256, 256);')
    s=s.replace('graphics.renderItem(itemStack, posX, posY);','graphics.item(itemStack, posX, posY);')
    s=s.replace('graphics.drawWordWrap(font, getMessage(), posX, posY, maxWidth, 0);','graphics.textWithWordWrap(font, getMessage(), posX, posY, maxWidth, 0xFF000000);')
    return s
edit('menu/button/TableOfContentsButton.java',tocbutton)

# Scroll widget + 26.1 mouse event records.
def scroll(s):
    s=s.replace('import net.minecraft.client.gui.GuiGraphics;','import net.minecraft.client.gui.GuiGraphicsExtractor;\nimport net.minecraft.client.input.MouseButtonEvent;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('public void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float partialTick)', 'protected void extractContents(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTick)')
    s=s.replace('graphics.blit(resourceLocation, renderX, renderY, iconU, v, iconWidth, iconHeight);','graphics.blit(RenderPipelines.GUI_TEXTURED, resourceLocation, renderX, renderY, iconU, v, iconWidth, iconHeight, 256, 256);')
    s=re.sub(r'@Override\n    public void onClick\(double mouseX, double mouseY\) \{\n        this.dragging = true;\n        setValueFromMouse\(mouseX, mouseY\);\n        super.onClick\(mouseX, mouseY\);\n    \}', '@Override\n    public void onClick(MouseButtonEvent event, boolean doubleClick) {\n        this.dragging = true;\n        setValueFromMouse(event.x(), event.y());\n        super.onClick(event, doubleClick);\n    }', s)
    s=re.sub(r'@Override\n    public void onDrag\(double mouseX, double mouseY, double dragX, double dragY\) \{\n        this.dragging = true;\n        setValueFromMouse\(mouseX, mouseY\);\n    \}', '@Override\n    public boolean mouseDragged(MouseButtonEvent event, double dragX, double dragY) {\n        this.dragging = true;\n        setValueFromMouse(event.x(), event.y());\n        return true;\n    }\n\n    public void dragTo(double mouseX, double mouseY) {\n        this.dragging = true;\n        setValueFromMouse(mouseX, mouseY);\n    }', s)
    s=re.sub(r'@Override\n    public boolean mouseReleased\(double mouseX, double mouseY, int button\) \{\n        dragging = false;\n        return super.mouseReleased\(mouseX, mouseY, button\);\n    \}', '@Override\n    public boolean mouseReleased(MouseButtonEvent event) {\n        dragging = false;\n        return super.mouseReleased(event);\n    }', s)
    return s
edit('menu/button/ScrollButton.java',scroll)

# Main book screen: background and page drawing are extracted before child widgets.
def screen(s):
    s=s.replace('import net.minecraft.client.gui.GuiGraphics;','import net.minecraft.client.gui.GuiGraphicsExtractor;\nimport net.minecraft.client.input.MouseButtonEvent;\nimport net.minecraft.client.renderer.RenderPipelines;')
    s=s.replace('super(EGRegistry.ItemReg.GUIDE_BOOK.get().getDescription());','super(EGRegistry.ItemReg.GUIDE_BOOK.get().getName(new ItemStack(EGRegistry.ItemReg.GUIDE_BOOK.get())));')
    # remove old blurred-background override block
    s=re.sub(r'\n\t/\*\*\n\t \* Override to disable the blur effect.*?\n\t\}\n\n\t//// RENDER ////', '\n\t//// RENDER ////', s, flags=re.S)
    old=re.search(r'\n\t@Override\n\tpublic void render\(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks\) \{.*?\n\t\}', s, flags=re.S)
    if old:
        new='''\n\t@Override\n\tpublic void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks) {\n\t\t// Preserve the original crisp in-world book background: dim only, no blur.\n\t\textractTransparentBackground(graphics);\n\t}\n\n\t@Override\n\tpublic void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks) {\n\t\tgraphics.blit(RenderPipelines.GUI_TEXTURED, TEXTURE, this.x, this.y, 0.0F, 0.0F, this.imageWidth, this.imageHeight, 256, 256);\n\t\tfinal float ticksOpen = this.ticksOpen + partialTicks;\n\t\tif (this.guideBook != null) {\n\t\t\tthis.guideBook.getPage(this.page).render(this, graphics, ticksOpen);\n\t\t\tthis.guideBook.getPage(this.page + 1).render(this, graphics, ticksOpen);\n\t\t}\n\t\tsuper.extractRenderState(graphics, mouseX, mouseY, partialTicks);\n\t}'''
        s=s[:old.start()]+new+s[old.end():]
    # old screen-level drag routing -> event form; use scroll button helper to preserve drag outside its bounds
    s=re.sub(r'\n\t@Override\n\tpublic boolean mouseDragged\(double mouseX, double mouseY, int button, double dragX, double dragY\) \{.*?\n\t\}', '''\n\t@Override\n\tpublic boolean mouseDragged(MouseButtonEvent event, double dragX, double dragY) {\n\t\tif (guideBook != null && guideBook.getPage(page) instanceof ScrollButton.IScrollProvider provider && provider.getScrollButton().isDragging()) {\n\t\t\tprovider.getScrollButton().dragTo(event.x(), event.y());\n\t\t\treturn true;\n\t\t}\n\t\tif (guideBook != null && guideBook.getPage(page + 1) instanceof ScrollButton.IScrollProvider provider && provider.getScrollButton().isDragging()) {\n\t\t\tprovider.getScrollButton().dragTo(event.x(), event.y());\n\t\t\treturn true;\n\t\t}\n\t\treturn super.mouseDragged(event, dragX, dragY);\n\t}''', s, flags=re.S)
    s=s.replace('public void renderWidget(GuiGraphicsExtractor guiGraphics, int mouseX, int mouseY, float partialTick)', 'protected void extractContents(GuiGraphicsExtractor guiGraphics, int mouseX, int mouseY, float partialTick)')
    s=s.replace('guiGraphics.blit(this.texture, this.getX(), this.getY(), this.u, vOffset, this.width, this.height);','guiGraphics.blit(RenderPipelines.GUI_TEXTURED, this.texture, this.getX(), this.getY(), this.u, vOffset, this.width, this.height, 256, 256);')
    return s
edit('menu/GuideBookScreen.java',screen)

# Inventory screen mirrors vanilla 26.1 DispenserScreen extraction.
write('menu/GolemInventoryScreen.java', r'''package com.mcmoddev.golems.client.menu;

import com.mcmoddev.golems.menu.GolemInventoryMenu;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.player.Inventory;

public class GolemInventoryScreen extends AbstractContainerScreen<GolemInventoryMenu> {
    public static final Identifier BG_TEXTURE = Identifier.withDefaultNamespace("textures/gui/container/dispenser.png");

    public GolemInventoryScreen(GolemInventoryMenu cont, Inventory pInv, Component title) { super(cont, pInv, title); }

    @Override
    protected void init() {
        super.init();
        this.titleLabelX = (this.imageWidth - this.font.width(this.title)) / 2;
    }

    @Override
    public void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTick) {
        super.extractBackground(graphics, mouseX, mouseY, partialTick);
        int i = (this.width - this.imageWidth) / 2;
        int j = (this.height - this.imageHeight) / 2;
        graphics.blit(RenderPipelines.GUI_TEXTURED, BG_TEXTURE, i, j, 0.0F, 0.0F, this.imageWidth, this.imageHeight, 256, 256);
    }
}
''')

# Guide book recipe and debug behavior. The 26.1 client does not retain server RecipeManager entries;
# these visuals are built from the exact two JSON recipes bundled by this mod.
def guide(s):
    s=s.replace('import com.mcmoddev.golems.ExtraGolems;','import com.mcmoddev.golems.ExtraGolems;\nimport com.mcmoddev.golems.EGRegistry;')
    s=s.replace('import com.mcmoddev.golems.network.EGNetwork;\n','')
    s=s.replace('import net.minecraft.client.gui.screens.Screen;\n','')
    s=s.replace('import net.minecraft.world.item.crafting.CraftingRecipe;\nimport net.minecraft.world.item.crafting.Recipe;\nimport net.minecraft.world.item.crafting.RecipeManager;','import net.minecraft.world.item.ItemStack;\nimport net.minecraft.world.item.Items;\nimport net.minecraft.world.item.crafting.Ingredient;\nimport net.minecraft.world.level.block.Blocks;')
    s=s.replace('final RecipeManager recipeManager = Minecraft.getInstance().level.getRecipeManager();\n\t\tfinal Optional<CraftingRecipe> oSpellRecipe = loadRecipe(recipeManager, SPELL_RECIPE);\n\t\tfinal Optional<CraftingRecipe> oHeadRecipe = loadRecipe(recipeManager, HEAD_RECIPE);\n\t\tif(oSpellRecipe.isPresent() && oHeadRecipe.isPresent()) {\n\t\t\tpages.add(new CraftingRecipePage.Builder(screen, page++, oSpellRecipe.get())', 'pages.add(new CraftingRecipePage.Builder(screen, page++, List.of(Ingredient.of(Items.FEATHER), Ingredient.of(Items.REDSTONE), Ingredient.of(Items.PAPER), Ingredient.of(Items.INK_SAC)), new ItemStack(EGRegistry.ItemReg.GOLEM_SPELL.get(), 3))')
    s=s.replace('\t\t\tpages.add(new CraftingRecipePage.Builder(screen, page++, oHeadRecipe.get())', '\t\tpages.add(new CraftingRecipePage.Builder(screen, page++, List.of(Ingredient.of(Blocks.CARVED_PUMPKIN), Ingredient.of(EGRegistry.ItemReg.GOLEM_SPELL.get())), new ItemStack(EGRegistry.BlockReg.GOLEM_HEAD.get()))')
    # Remove closing brace belonging to old if after second recipe build.
    s=s.replace('\t\t\t\t\t.build());\n\t\t}\n\n\t\t// add build instructions section', '\t\t\t\t\t.build());\n\n\t\t// add build instructions section',1)
    s=s.replace('return Screen.hasControlDown();','return Minecraft.getInstance().hasControlDown();')
    s=s.replace('net.neoforged.neoforge.network.PacketDistributor.sendToServer(', 'net.neoforged.neoforge.client.network.ClientPacketDistributor.sendToServer(')
    s=re.sub(r'\n\tprivate static Optional<CraftingRecipe> loadRecipe\(.*?\n\t\}\n', '\n', s, flags=re.S)
    return s
edit('menu/guide_book/GuideBook.java',guide)

print('Applied pass 5: native 26.1 GUI extraction, guide recipes, mouse input, inventory screen.')
