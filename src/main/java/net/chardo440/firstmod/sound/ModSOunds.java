package net.chardo440.firstmod.sound;

import net.chardo440.firstmod.FirstmodMod;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.level.block.SoundType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.function.Supplier;

public class ModSOunds {
    public static final DeferredRegister<SoundEvent> SOUND_EVENTS =
            DeferredRegister.create(BuiltInRegistries.SOUND_EVENT, FirstmodMod.MOD_ID);

    public static final Supplier<SoundEvent> FART_SOUND = registerSoundEvent("fart_sound");

    private static Supplier<SoundEvent> registerSoundEvent(String name) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(FirstmodMod.MOD_ID, name);
        return SOUND_EVENTS.register(name, () -> SoundEvent.createVariableRangeEvent(id));
    }

    private static SoundType customFartSound;

    public static SoundType getCustomFartSound() {
        if (customFartSound == null) {
            customFartSound = new SoundType(1.0F, 1.0F,
                    SoundEvents.GLASS_BREAK,  // Break sound
                    FART_SOUND.get(),  // Step sound (replace with actual step sound)
                    FART_SOUND.get(),  // Place sound (replace with actual place sound)
                    FART_SOUND.get(),  // Hit sound (replace with actual hit sound)
                    FART_SOUND.get()   // Fall sound (replace with actual fall sound)
            );
        }
        return customFartSound;
    }

    public static void register(IEventBus eventBus) {
        SOUND_EVENTS.register(eventBus);
    }
}