package net.chardo440.firstmod.item;

import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.food.FoodProperties;

public class ModFoodProperties {
    public static final FoodProperties TOMATO = new FoodProperties.Builder().nutrition(3).saturationModifier(1f)
            .effect(() -> new MobEffectInstance(MobEffects.CONFUSION), 1f).build();
}
