package net.chardo440.firstmod.sound;

import net.chardo440.firstmod.FirstmodMod;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.sounds.SoundEvent;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.function.Supplier;

public class ModSOunds {
    public static final DeferredRegister<SoundEvent> SOUND_EVENTS =
                DeferredRegister.create(BuiltInRegistries.SOUND_EVENT, FirstmodMod.MOD_ID);

    public static final Supplier<SoundEvent> FART_SOUND = registerSoundEvent("fart_sound");

    private static Supplier<SoundEvent> registerSoundEvent(String name) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(FirstmodMod.MOD_ID, name);
        return  SOUND_EVENTS.register(name, () -> SoundEvent.createVariableRangeEvent(id));
    }

    public static void register(IEventBus eventBus) {
        SOUND_EVENTS.register(eventBus);
    }
}
