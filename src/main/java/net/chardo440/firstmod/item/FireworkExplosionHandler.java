package net.chardo440.firstmod.item;

import cpw.mods.modlauncher.api.ITransformationService;
import net.minecraft.commands.arguments.ResourceLocationArgument;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.projectile.FireworkRocketEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;

import static net.minecraft.resources.ResourceLocation.fromNamespaceAndPath;
import net.minecraft.core.registries.BuiltInRegistries; // Adjust the import based on your actual package

import java.util.Optional;

public class FireworkExplosionHandler {


    public static void handleFireworkExplosion(ServerLevel level, FireworkRocketEntity fireworkEntity) {
        ResourceLocation lootTableId = ResourceLocation.fromNamespaceAndPath("firstmod", "firework_loot");

        // Access the LootTable using the registry system
        LootTable lootTable = level.getServer().registryAccess().registryOrThrow(Registries.LOOT_TABLE).get(lootTableId);

        // Create LootParams
        LootParams lootParams = new LootParams.Builder(level)
                .withParameter(LootContextParams.ORIGIN, fireworkEntity.position())
                .create(LootContextParamSets.ENTITY);

        // Use the getRandomItems method with LootParams
        RandomSource random = level.random;
        for (ItemStack stack : lootTable.getRandomItems(lootParams, random)) {
            ItemEntity itemEntity = new ItemEntity(level, fireworkEntity.getX(), fireworkEntity.getY(), fireworkEntity.getZ(), stack);
            level.addFreshEntity(itemEntity);
        }
    }
}