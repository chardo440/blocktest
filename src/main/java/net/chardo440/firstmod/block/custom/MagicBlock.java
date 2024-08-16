package net.chardo440.firstmod.block.custom;

import net.chardo440.firstmod.item.FireworkExplosionHandler;
import net.chardo440.firstmod.item.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.FireworkRocketEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.BlockHitResult;

public class MagicBlock extends Block {

    private long lastSoundTime = 0;
    private static final long COOLDOWN_TICKS = 20; // 1 second cooldown (20 ticks)
    private boolean isScheduled = false;

    public MagicBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        ItemStack fireworkShoot = new ItemStack(Items.FIREWORK_ROCKET);
        FireworkRocketEntity firework = new FireworkRocketEntity(level, pos.getX(), pos.getY(), pos.getZ(), fireworkShoot);
        level.addFreshEntity(firework);

        level.playSound(null, pos, SoundEvents.FIREWORK_ROCKET_LAUNCH, SoundSource.BLOCKS, 3.0F, 1.0F);

        if (level instanceof ServerLevel) {
            FireworkExplosionHandler.handleFireworkExplosion((ServerLevel) level, firework);
        }

        return InteractionResult.SUCCESS;
    }


    // Handles entity stepping on the block
    @Override
    public void stepOn(Level level, BlockPos pos, BlockState state, Entity entity) {
        if (entity instanceof ItemEntity itemEntity) {
            long currentTime = level.getGameTime();

            if (!isScheduled && currentTime - lastSoundTime >= COOLDOWN_TICKS) {
                if (isValidItem(itemEntity.getItem())) {
                    itemEntity.setItem(new ItemStack(Items.DIAMOND, itemEntity.getItem().getCount()));
                    level.playSound(null, pos, SoundEvents.PLAYER_LEVELUP, SoundSource.BLOCKS, 1.0F, 1.0F);
                    lastSoundTime = currentTime;
                } else if (isBoomItem(itemEntity.getItem())) {
                    level.playSound(null, pos, SoundEvents.TNT_PRIMED, SoundSource.BLOCKS, 1.0F, 1.0F);
                    itemEntity.remove(Entity.RemovalReason.DISCARDED);
                    level.scheduleTick(pos, this, 20);
                    lastSoundTime = currentTime;
                    isScheduled = true;
                }
            }
        }

        super.stepOn(level, pos, state, entity);
    }

    // Handles the scheduled explosion tick
    @Override
    public void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if (isScheduled) {
            level.sendParticles(ParticleTypes.FIREWORK, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, 10, 0.5, 0.5, 0.5, 0.1);
            level.explode(null, pos.getX() + 1, pos.getY() + 1, pos.getZ() + 1, 200, Level.ExplosionInteraction.NONE);
            isScheduled = false;
        }
    }

    // Validates if the item can trigger an explosion
    private boolean isBoomItem(ItemStack item) {
        return item.getItem() == Items.TNT;
    }

    // Validates if the item can be converted to diamonds
    private boolean isValidItem(ItemStack item) {
        return item.getItem() == ModItems.BLACK_OPAL.get() || item.getItem() == Items.COAL || item.getItem() == Items.ANDESITE;
    }
}