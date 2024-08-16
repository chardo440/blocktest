package net.chardo440.firstmod.item;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.projectile.FireworkRocketEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;


public class FireworkExplosionHandler {


    public static void handleFireworkExplosion(ServerLevel level, FireworkRocketEntity fireworkEntity) {
        ResourceLocation lootTableId = new ResourceLocation("firstmod", "firework_loot");
        LootTable lootTable = level.getServer().reloadableRegistries().getLootTable(lootTableId);

        LootContext.Builder builder = new LootContext.Builder(level)
                .withRandom(level.random)
                .withParameter(LootContextParams.ORIGIN, fireworkEntity.position());

        LootContext context = builder.create(LootContextParamSets.ENTITY);

        for (ItemStack stack : lootTable.getRandomItems(context)) {
            ItemEntity itemEntity = new ItemEntity(level, fireworkEntity.getX(), fireworkEntity.getY(), fireworkEntity.getZ(), stack);
            level.addFreshEntity(itemEntity);
        }
    }
}