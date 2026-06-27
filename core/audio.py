# core/audio.py

import math
import os
from array import array

import pygame

from config import (
    AUDIO_PATHS,
    STATE_EXECUTING,
    STATE_MENU,
    STATE_PLANNING,
    STATE_RESULT,
)


class GameAudio:
    SAMPLE_RATE = 44100
    SAMPLE_SIZE = -16
    CHANNELS = 2
    BUFFER = 512

    LOOP_FOR_STATE = {
        STATE_MENU: "menu_music",
        STATE_PLANNING: "game_music",
        STATE_EXECUTING: "firetruck_siren",
        STATE_RESULT: None,
    }

    LOOP_VOLUMES = {
        "menu_music": 0.45,
        "game_music": 0.42,
        "firetruck_siren": 0.72,
    }

    def __init__(self):
        self.enabled = False
        self.current_loop_key = None
        self.click_sound = None
        self.result_win_sound = None
        self.result_fail_sound = None
        self._init_mixer()
        if self.enabled:
            self._create_ui_sounds()

    @classmethod
    def pre_init(cls):
        pygame.mixer.pre_init(cls.SAMPLE_RATE, cls.SAMPLE_SIZE, cls.CHANNELS, cls.BUFFER)

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(self.SAMPLE_RATE, self.SAMPLE_SIZE, self.CHANNELS, self.BUFFER)
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def _create_ui_sounds(self):
        self.click_sound = self._make_tone([
            (780, 0.035, 0.22),
            (1120, 0.045, 0.16),
        ], volume=0.42)
        self.result_win_sound = self._make_tone([
            (523, 0.10, 0.24),
            (659, 0.12, 0.25),
            (784, 0.14, 0.27),
            (1046, 0.20, 0.22),
        ], volume=0.55)
        self.result_fail_sound = self._make_tone([
            (392, 0.14, 0.25),
            (330, 0.22, 0.22),
        ], volume=0.52)

    def _make_tone(self, parts, volume=0.5):
        mixer = pygame.mixer.get_init()
        if not mixer:
            return None
        sample_rate, sample_size, channels = mixer
        if sample_size != -16:
            return None

        samples = array("h")
        for frequency, duration, amplitude in parts:
            total = max(1, int(sample_rate * duration))
            attack = max(1, int(sample_rate * 0.006))
            release = max(1, int(sample_rate * 0.018))
            for i in range(total):
                fade_in = min(1.0, i / attack)
                fade_out = min(1.0, (total - i) / release)
                envelope = min(fade_in, fade_out)
                value = 0
                if frequency > 0:
                    angle = 2 * math.pi * frequency * (i / sample_rate)
                    value = int(32767 * volume * amplitude * envelope * math.sin(angle))
                for _ in range(channels):
                    samples.append(value)

        try:
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def sync_state(self, state):
        self.play_loop(self.LOOP_FOR_STATE.get(state))

    def play_loop(self, key):
        if not self.enabled:
            return
        if key == self.current_loop_key and pygame.mixer.music.get_busy():
            return
        if key is None:
            self.stop_loop()
            return

        path = AUDIO_PATHS.get(key, "")
        if not path or not os.path.exists(path):
            self.stop_loop()
            return

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.LOOP_VOLUMES.get(key, 0.5))
            pygame.mixer.music.play(loops=-1)
            self.current_loop_key = key
        except pygame.error:
            self.current_loop_key = None

    def stop_loop(self):
        if not self.enabled:
            return
        try:
            pygame.mixer.music.fadeout(180)
        except pygame.error:
            pass
        self.current_loop_key = None

    def play_click(self):
        self._play_sound(self.click_sound)

    def play_result(self, won):
        self._play_sound(self.result_win_sound if won else self.result_fail_sound)

    def _play_sound(self, sound):
        if not self.enabled or sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass
