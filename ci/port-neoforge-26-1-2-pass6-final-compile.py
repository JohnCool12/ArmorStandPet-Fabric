from pathlib import Path
import re
p=Path('project/src/main/java/com/mcmoddev/golems/client/menu/GuideBookScreen.java')
s=p.read_text()
# Ensure extraction import exists and obsolete GuiGraphics references are gone.
if 'import net.minecraft.client.gui.GuiGraphicsExtractor;' not in s:
    s=s.replace('import net.minecraft.client.gui.Font;','import net.minecraft.client.gui.Font;\nimport net.minecraft.client.gui.GuiGraphicsExtractor;')
if 'import net.minecraft.client.renderer.RenderPipelines;' not in s:
    s=s.replace('import net.minecraft.client.gui.screens.Screen;','import net.minecraft.client.gui.screens.Screen;\nimport net.minecraft.client.renderer.RenderPipelines;')
# Replace the legacy whole-screen render method exactly.
start=s.index('\n\t@Override\n\tpublic void render(GuiGraphics graphics')
end=s.index('\n\t}', start)+4
new='''
	@Override
	public void extractBackground(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks) {
		// Preserve the original dimmed in-world backdrop without the vanilla menu blur.
		extractTransparentBackground(graphics);
	}

	@Override
	public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTicks) {
		graphics.blit(RenderPipelines.GUI_TEXTURED, TEXTURE, this.x, this.y, 0.0F, 0.0F,
				this.imageWidth, this.imageHeight, 256, 256);
		final float openTicks = this.ticksOpen + partialTicks;
		if (this.guideBook != null) {
			this.guideBook.getPage(this.page).render(this, graphics, openTicks);
			this.guideBook.getPage(this.page + 1).render(this, graphics, openTicks);
		}
		super.extractRenderState(graphics, mouseX, mouseY, partialTicks);
	}'''
s=s[:start]+new+s[end:]
# Replace the inner button's old renderWidget override.
s=s.replace('''		@Override
		public void renderWidget(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTick) {
			int vOffset = this.v;
			if (this.isHoveredOrFocused()) {
				vOffset += this.dv;
			}
			guiGraphics.blit(RenderPipelines.GUI_TEXTURED, this.texture, this.getX(), this.getY(), this.u, vOffset, this.width, this.height, 256, 256);
		}''','''		@Override
		protected void extractContents(GuiGraphicsExtractor guiGraphics, int mouseX, int mouseY, float partialTick) {
			int vOffset = this.v;
			if (this.isHoveredOrFocused()) vOffset += this.dv;
			guiGraphics.blit(RenderPipelines.GUI_TEXTURED, this.texture, this.getX(), this.getY(),
					(float)this.u, (float)vOffset, this.width, this.height, 256, 256);
		}''')
# Defensive cleanup: no obsolete GUI rendering type may remain in this file.
s=s.replace('GuiGraphics guiGraphics','GuiGraphicsExtractor guiGraphics')
p.write_text(s)
print('Applied pass 6 GuideBookScreen extraction fix.')
