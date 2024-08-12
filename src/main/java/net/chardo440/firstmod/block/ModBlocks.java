package net.chardo440.firstmod.block;

import net.chardo440.firstmod.FirstmodMod;
import net.chardo440.firstmod.item.ModItems;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.minecraft.world.level.block.SoundType;
import net.chardo440.firstmod.sound.ModSOunds;

import java.util.function.Supplier;

import static net.chardo440.firstmod.sound.ModSOunds.FART_SOUND;

public class ModBlocks {
    public static final DeferredRegister.Blocks BLOCKS =
                DeferredRegister.createBlocks(FirstmodMod.MOD_ID);

    public static final DeferredBlock<Block> BLACK_OPAL_BLOCK = registerBlock("black_opal_block",
            () -> new Block(BlockBehaviour.Properties.of().strength(4f).requiresCorrectToolForDrops()));

    public static final DeferredBlock<Block> RAW_BLACK_OPAL_BLOCK = registerBlock("raw_black_opal_block",
            () -> new Block(BlockBehaviour.Properties.of().strength(4f).requiresCorrectToolForDrops()));

    public static final DeferredBlock<Block> LAMP_1 = registerBlock("lamp_1",
            () -> new Block(BlockBehaviour.Properties.of()
                    .strength(4f)
                    .noOcclusion()
                    .lightLevel((state)->12)
                    .requiresCorrectToolForDrops()));

    public static final DeferredBlock<Block> DOUBLE_STREET_LAMP_1 = registerBlock("double_street_lamp_1",
            () -> new Block(BlockBehaviour.Properties.of()
                    .strength(4f)
                    .noOcclusion()
                    .lightLevel((state)->15)
                    .sound(ModSOunds.getCustomFartSound())
                    .requiresCorrectToolForDrops()));

    private static <T extends Block> DeferredBlock<T> registerBlock(String name, Supplier<T> block) {
        DeferredBlock<T> toReturn = BLOCKS.register(name, block);
        registerBlockItem(name, toReturn);
        return toReturn;

    }

    private static <T extends Block> void registerBlockItem(String name, DeferredBlock<T> block) {
        ModItems.ITEMS.register(name, () -> new BlockItem(block.get(), new Item.Properties()));
    }

    public static void register(IEventBus eventBus) {
        BLOCKS.register(eventBus);
    }
}
