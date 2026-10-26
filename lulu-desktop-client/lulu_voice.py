import os
import asyncio
import threading
import tempfile
import edge_tts
import pygame

# You can change Lulu's voice anytime!
# Popular neural voices:
# "en-US-AriaNeural" (Friendly, expressive female voice)
# "en-US- JennyNeural" (Warm assistant female voice)
# "en-GB-SoniaNeural" (British female voice)
LULU_VOICE = "en-US-AriaNeural"

class LuluVoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        # Safely determine temp directory for audio cache
        try:
            self.temp_dir = r"E:\DevCache\temp_audio"
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception:
            self.temp_dir = os.path.join(tempfile.gettempdir(), "lulu_audio_cache")
            os.makedirs(self.temp_dir, exist_ok=True)
        self.counter = 0

    def speak(self, text):
        """Speaks text in a background thread so Lulu's neon animation never lags."""
        threading.Thread(target=self._run_tts, args=(text,), daemon=True).start()

    def _run_tts(self, text):
        try:
            self.counter += 1
            output_file = os.path.join(self.temp_dir, f"lulu_speech_{self.counter}.mp3")
            
            # Generate neural audio using Microsoft Edge-TTS
            asyncio.run(self._generate_audio(text, output_file))

            # Stop any previous speech if the user clicks fast
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.music.unload()

            # Play the new speech immediately
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"[Lulu Voice Error]: {e}")

    async def _generate_audio(self, text, output_file):
        communicate = edge_tts.Communicate(text, LULU_VOICE, rate="+5%")
        await communicate.save(output_file)