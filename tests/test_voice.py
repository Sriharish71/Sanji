"""
Test suite for SANJI Phase 2 Voice Subsystem.
Verifies Audio Manager hardware detection, Faster-Whisper transcription,
and Piper TTS speech synthesis.
"""

import os
import sys
from pathlib import Path
import numpy as np
import unittest

# Add project root
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication

from voice.audio_manager import AudioManager
from voice.speech_recognition import SpeechRecognizer
from voice.text_to_speech import TextToSpeech, clean_text_for_speech


class TestSanjiVoice(unittest.TestCase):
    """Voice subsystem automated test suite."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.audio_mgr = AudioManager()
        self.speech_rec = SpeechRecognizer(model_size="tiny.en", device="cpu", compute_type="int8")
        self.tts = TextToSpeech(
            audio_manager=self.audio_mgr,
            model_path="voice/models/piper/en_US-lessac-medium.onnx"
        )

    def test_audio_devices_enumeration(self):
        """Verify microphone and speaker hardware detection."""
        devices = self.audio_mgr.get_devices()
        self.assertIn("inputs", devices)
        self.assertIn("outputs", devices)
        self.assertGreater(len(devices["inputs"]), 0, "No audio input devices detected!")
        self.assertGreater(len(devices["outputs"]), 0, "No audio output devices detected!")

    def test_text_cleaning_for_speech(self):
        """Verify markdown and code fence removal for natural spoken delivery."""
        raw = "Hello! **This is bold** and `inline_code`. Here is a block:\n```python\nprint(1)\n```\nAll done!"
        cleaned = clean_text_for_speech(raw)
        self.assertNotIn("```", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertIn("This is bold", cleaned)
        self.assertIn("All done!", cleaned)

    def test_piper_tts_synthesis(self):
        """Verify Piper TTS synthesizes text to a valid audio array."""
        test_phrase = "System online. Voice test in progress."
        audio_data, sample_rate = self.tts.synthesize_sync(test_phrase)

        self.assertIsNotNone(audio_data)
        self.assertIsInstance(audio_data, np.ndarray)
        self.assertEqual(sample_rate, 22050)
        self.assertGreater(len(audio_data), 1000)

    def test_faster_whisper_transcription(self):
        """Verify Faster-Whisper initializes and handles audio array."""
        # 0.5s of silence
        dummy_audio = np.zeros(8000, dtype=np.float32)
        transcription = self.speech_rec.transcribe_sync(dummy_audio)
        self.assertIsInstance(transcription, str)

    def test_tts_mute_control(self):
        """Verify TTS mute state management."""
        self.assertFalse(self.tts.is_muted)
        self.tts.set_muted(True)
        self.assertTrue(self.tts.is_muted)
        self.tts.toggle_muted()
        self.assertFalse(self.tts.is_muted)


if __name__ == "__main__":
    unittest.main()
