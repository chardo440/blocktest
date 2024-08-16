package net.chardo440.firstmod.item;

import net.chardo440.firstmod.FirstmodMod;
import net.chardo440.firstmod.item.custom.ChainsawItem;
import net.minecraft.world.item.Item;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModItems {
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(FirstmodMod.MOD_ID);

    public static final DeferredItem<Item> BLACK_OPAL = ITEMS.registerSimpleItem("black_opal");

    public static final DeferredItem<Item> RAW_BLACK_OPAL = ITEMS.registerSimpleItem("raw_black_opal");

    public static final DeferredItem<Item> CHAINSAW = ITEMS.registerItem("chainsaw", ChainsawItem::new, new Item.Properties()
            .durability(32));

    public static final DeferredItem<Item> TOMATO = ITEMS.registerItem("tomato", Item::new, new Item.Properties().food(ModFoodProperties.TOMATO));

    public static void register(IEventBus eventBus){
        ITEMS.register(eventBus);
    }
}
