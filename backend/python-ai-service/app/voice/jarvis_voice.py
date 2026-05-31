"""
JarvisVoice — Билингвал (MN + EN) STT/TTS системийн нэгдсэн API
================================================================

Ашиглах:
    from jarvis_voice import JarvisVoice

    jarvis = JarvisVoice(device="cuda")

    # STT
    text = jarvis.transcribe("audio.wav")           # auto-detect
    text = jarvis.transcribe("audio.wav", lang="mn") # Монгол

    # TTS — default voice
    wav = jarvis.speak("Сайн байна уу", lang="mn")

    # TTS — voice clone
    wav = jarvis.speak("Hello world", lang="en", voice_ref="my_voice.wav")
    jarvis.save(wav, "output.wav")
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Literal

import torch
import numpy as np

# ─── STT ──────────────────────────────────────────────────────────────────────

MN_STT_MODEL = "bayartsogt/whisper-large-v2-mn-13"
EN_STT_MODEL = "openai/whisper-large-v2"

# ─── TTS ──────────────────────────────────────────────────────────────────────

LUXTTS_MODEL = "YatharthS/LuxTTS"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class STTEngine:
    """
    Bilingual Speech-to-Text engine.
    - Монгол: whisper-large-v2-mn-13 (WER ~20%)
    - Англи:  openai/whisper-large-v2
    """

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._mn_pipe = None
        self._en_pipe = None

    def _load_mn(self):
        if self._mn_pipe is None:
            logger.info("Loading Mongolian STT model...")
            from transformers import pipeline
            self._mn_pipe = pipeline(
                "automatic-speech-recognition",
                model=MN_STT_MODEL,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
                chunk_length_s=30,
                stride_length_s=5,
            )
            logger.info("Mongolian STT loaded ✓")
        return self._mn_pipe

    def _load_en(self):
        if self._en_pipe is None:
            logger.info("Loading English STT model...")
            from transformers import pipeline
            self._en_pipe = pipeline(
                "automatic-speech-recognition",
                model=EN_STT_MODEL,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
                chunk_length_s=30,
                stride_length_s=5,
                generate_kwargs={"language": "english"},
            )
            logger.info("English STT loaded ✓")
        return self._en_pipe

    def transcribe(
        self,
        audio_path: str,
        lang: Literal["mn", "en", "auto"] = "auto",
    ) -> str:
        """
        Аудио файлыг текст болгон хөрвүүлнэ.

        Args:
            audio_path: WAV/MP3 файлын зам
            lang: "mn" | "en" | "auto"
                  "auto" → Монгол загваргаар эхэлж оролдоно,
                           хэрэв үр дүн хоосон бол Англи загвар ашиглана

        Returns:
            Таних гаралт (str)
        """
        if lang == "mn":
            pipe = self._load_mn()
            result = pipe(audio_path)
            return result["text"].strip()

        elif lang == "en":
            pipe = self._load_en()
            result = pipe(audio_path)
            return result["text"].strip()

        else:  # auto
            # Try Mongolian first
            mn_pipe = self._load_mn()
            result = mn_pipe(audio_path)
            text = result["text"].strip()
            # Хэрэв Кирилл тэмдэгт байвал Монгол гэж үзнэ
            cyrillic_count = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
            if cyrillic_count > len(text) * 0.3:
                return text
            # Otherwise try English
            en_pipe = self._load_en()
            en_result = en_pipe(audio_path)
            return en_result["text"].strip()


class TTSEngine:
    """
    Bilingual Text-to-Speech engine using LuxTTS.
    - Англи: LuxTTS native (espeak EN phonemizer)
    - Монгол: LuxTTS + Монгол Кирилл phonemizer patch
    """

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._lux = None
        self._default_mn_ref = None  # optional default MN voice reference
        self._default_en_ref = None  # optional default EN voice reference

    def _load_lux(self):
        if self._lux is None:
            logger.info("Loading LuxTTS model...")
            # Add LuxTTS to path
            lux_path = Path(__file__).parent / "LuxTTS"
            if str(lux_path) not in sys.path:
                sys.path.insert(0, str(lux_path))
            from zipvoice.luxvoice import LuxTTS
            self._lux = LuxTTS(LUXTTS_MODEL, device=self.device)
            logger.info("LuxTTS loaded ✓")
        return self._lux

    def set_default_voice(self, audio_path: str, lang: Literal["mn", "en"] = "en"):
        """
        Default voice reference тохируулна — дараачийн speak() дуудлагуудад ашиглана.

        Args:
            audio_path: Reference WAV файл (≥3 секунд)
            lang: Хэлний тохиргоо
        """
        lux = self._load_lux()
        encoded = lux.encode_prompt(audio_path)
        if lang == "mn":
            self._default_mn_ref = encoded
            logger.info(f"Default Mongolian voice set from {audio_path}")
        else:
            self._default_en_ref = encoded
            logger.info(f"Default English voice set from {audio_path}")

    def speak(
        self,
        text: str,
        lang: Literal["mn", "en"] = "en",
        voice_ref: Optional[str] = None,
        num_steps: int = 4,
        t_shift: float = 0.7,
        speed: float = 1.0,
        rms: float = 0.01,
    ) -> np.ndarray:
        """
        Текстийг дуу болгон хөрвүүлнэ.

        Args:
            text: Хөрвүүлэх текст
            lang: "mn" | "en"
            voice_ref: Reference WAV файл (voice clone). None бол default voice
            num_steps: Sampling steps (3-4 оновчтой)
            t_shift: Temperature-like parameter (0.5-0.9)
            speed: Яриа хурд (1.0 = хэвийн)
            rms: Дуу чимэгний түвшин

        Returns:
            numpy array (48000 Hz)
        """
        lux = self._load_lux()

        # Voice reference тодорхойлох
        if voice_ref is not None:
            encoded = lux.encode_prompt(voice_ref, rms=rms)
        elif lang == "mn" and self._default_mn_ref is not None:
            encoded = self._default_mn_ref
        elif lang == "en" and self._default_en_ref is not None:
            encoded = self._default_en_ref
        elif self._default_en_ref is not None:
            encoded = self._default_en_ref
            logger.warning(f"No {lang} default voice, using EN voice")
        else:
            raise ValueError(
                "No voice reference provided. Use voice_ref= parameter or "
                "set_default_voice() to configure a default voice."
            )

        wav = lux.generate_speech(
            text,
            encoded,
            num_steps=num_steps,
            t_shift=t_shift,
            speed=speed,
        )
        return wav.numpy().squeeze()

    def save(self, wav: np.ndarray, path: str, sample_rate: int = 48000):
        """WAV файл хадгалах."""
        import soundfile as sf
        sf.write(path, wav, sample_rate)
        logger.info(f"Saved → {path}")


class JarvisVoice:
    """
    Нэгдсэн Jarvis/Friday дуу интерфейс.

    Жишээ:
        jarvis = JarvisVoice(device="cuda")
        jarvis.set_default_voice("my_voice.wav", lang="en")

        # STT
        text = jarvis.transcribe("question.wav", lang="mn")

        # TTS
        wav = jarvis.speak("Сайн байна уу", lang="mn")
        jarvis.save(wav, "response.wav")
    """

    def __init__(self, device: str = "cuda"):
        """
        Args:
            device: "cuda" | "cpu" | "mps"
        """
        self.device = device
        self.stt = STTEngine(device=device)
        self.tts = TTSEngine(device=device)
        logger.info(f"JarvisVoice initialized on {device}")

    def set_default_voice(self, audio_path: str, lang: Literal["mn", "en"] = "en"):
        """TTS-д default дуу хоолой тохируулна."""
        self.tts.set_default_voice(audio_path, lang=lang)

    def transcribe(
        self,
        audio_path: str,
        lang: Literal["mn", "en", "auto"] = "auto",
    ) -> str:
        """
        Аудио → текст (STT).

        Args:
            audio_path: Аудио файлын зам
            lang: "mn" | "en" | "auto"
        """
        return self.stt.transcribe(audio_path, lang=lang)

    def speak(
        self,
        text: str,
        lang: Literal["mn", "en"] = "en",
        voice_ref: Optional[str] = None,
        **kwargs,
    ) -> np.ndarray:
        """
        Текст → аудио (TTS).

        Args:
            text: Хэлэх текст
            lang: "mn" | "en"
            voice_ref: Reference WAV (voice clone)
            **kwargs: num_steps, t_shift, speed, rms
        """
        return self.tts.speak(text, lang=lang, voice_ref=voice_ref, **kwargs)

    def save(self, wav: np.ndarray, path: str):
        """Аудио файл хадгалах."""
        self.tts.save(wav, path)

    def transcribe_and_respond(
        self,
        input_audio: str,
        response_text: str,
        input_lang: Literal["mn", "en", "auto"] = "auto",
        output_lang: Optional[Literal["mn", "en"]] = None,
        voice_ref: Optional[str] = None,
        output_path: str = "response.wav",
    ) -> dict:
        """
        Бүрэн pipeline: аудио сонсоод → текст → хариу үүсгэнэ.

        Args:
            input_audio: Оролтын аудио файл
            response_text: Хариу өгөх текст (LLM-ийн гаралт гэх мэт)
            input_lang: Оролтын хэл
            output_lang: Гаралтын хэл (None бол input_lang-тай адил)
            voice_ref: Reference WAV
            output_path: Гаралтын WAV файл

        Returns:
            {"input_text": ..., "output_path": ...}
        """
        # STT
        input_text = self.transcribe(input_audio, lang=input_lang)
        logger.info(f"Transcribed: {input_text!r}")

        # TTS
        out_lang = output_lang or (input_lang if input_lang != "auto" else "en")
        wav = self.speak(response_text, lang=out_lang, voice_ref=voice_ref)
        self.save(wav, output_path)

        return {
            "input_text": input_text,
            "response_text": response_text,
            "output_path": output_path,
        }


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Хурдан тест:
        python jarvis_voice.py --test-normalizer
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-normalizer", action="store_true")
    args = parser.parse_args()

    if args.test_normalizer:
        sys.path.insert(0, str(Path(__file__).parent / "LuxTTS"))
        from zipvoice.tokenizer.mongolian_normalizer import MongolianTextNormalizer
        norm = MongolianTextNormalizer()
        tests = [
            "2024 онд 5-р сарын 15-нд",
            "1000000 төгрөг",
            "3.14 тоо",
            "УБ хотод 12 цаг болоход",
            "Сайн байна уу, та хэд дэх хүн вэ?",
            "Hello and сайн байна уу mixed text",
        ]
        print("=== Mongolian Normalizer Test ===")
        for t in tests:
            print(f"  IN:  {t}")
            print(f"  OUT: {norm.normalize(t)}")
            print()
