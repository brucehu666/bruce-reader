import threading
import time
import asyncio
from typing import Optional, Callable, List
from pathlib import Path


class TTSEngine:
    def __init__(self, engine_type: str = "sapi"):
        self.engine_type = engine_type
        self.engine = None
        self.is_playing = False
        self.is_paused = False
        self.current_text = ""
        self.current_position = 0
        self.sentences: List[str] = []
        self.current_sentence_index = 0
        self.play_thread: Optional[threading.Thread] = None
        self.on_play_start: Optional[Callable] = None
        self.on_play_end: Optional[Callable] = None
        self.on_sentence_change: Optional[Callable[[int, str], None]] = None
        self.voice_combo_index = 0
        self._init_engine()

    def _init_engine(self):
        if self.engine_type == "edge":
            self._init_edge()
        else:
            self._init_sapi()

    def _init_sapi(self):
        try:
            import win32com.client
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            all_voices = self.engine.GetVoices()
            self.voices = []
            self.voice_names = []
            for v in all_voices:
                desc = v.GetDescription()
                self.voices.append(v)
                self.voice_names.append(desc)
            print(f"SAPI引擎初始化成功，检测到 {len(self.voices)} 个语音")
        except Exception as e:
            print(f"SAPI引擎初始化失败: {e}")
            self.engine = None
            self.voices = []
            self.voice_names = []

    def _init_edge(self):
        try:
            import edge_tts
            self.voices = [
                "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunxiNeural",
                "zh-CN-YunyangNeural",
                "zh-CN-liaoning-XiaobrainNeural",
                "zh-CN-shaanxi-XiaoniNeural",
                "zh-HK-HiuMaanNeural",
                "zh-TW-HsiaoYuNeural"
            ]
            self.voice_names = [
                "晓晓 (女声)",
                "云希 (男声)",
                "云扬 (男声)",
                "辽宁小脑 (女声)",
                "陕西小妮 (女声)",
                "香港晓曼 (女声)",
                "台湾晓雨 (女声)"
            ]
            self.engine = edge_tts
            print("Edge-TTS引擎初始化成功")
        except ImportError:
            print("Edge-TTS未安装，请运行: pip install edge-tts")
            self.engine = None
            self.voices = []
            self.voice_names = []
        except Exception as e:
            print(f"Edge-TTS引擎初始化失败: {e}")
            self.engine = None
            self.voices = []
            self.voice_names = []

    def get_voices(self) -> List[str]:
        return self.voice_names

    def set_voice(self, index: int):
        if self.engine_type == "sapi" and hasattr(self.engine, 'GetVoices'):
            if 0 <= index < len(self.voices):
                self.engine.Voice = self.engine.GetVoices().Item(index)
        self.voice_combo_index = index

    def set_rate(self, rate: float):
        pass

    def set_volume(self, volume: float):
        pass

    def _split_into_sentences(self, text: str) -> List[str]:
        import re
        sentences = re.split(r'[。！？.!?\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def play(self, text: str, start_position: int = 0):
        if not self.engine:
            if self.on_play_end:
                self.on_play_end()
            return

        if self.is_playing:
            self.stop()

        self.current_text = text
        self.current_position = start_position
        self.sentences = self._split_into_sentences(text)
        self.current_sentence_index = 0
        self.is_playing = True
        self.is_paused = False

        if self.on_play_start:
            self.on_play_start()

        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()

    def _play_loop(self):
        try:
            while self.is_playing and self.current_sentence_index < len(self.sentences):
                if self.is_paused:
                    time.sleep(0.1)
                    continue

                if not self.is_playing:
                    break

                sentence = self.sentences[self.current_sentence_index]
                if not sentence.strip():
                    self.current_sentence_index += 1
                    continue

                if self.on_sentence_change:
                    try:
                        self.on_sentence_change(self.current_sentence_index, sentence)
                    except Exception:
                        pass

                try:
                    if self.engine_type == "edge":
                        asyncio.run(self._edge_speak(sentence))
                    else:
                        self.engine.Speak(sentence)
                except Exception as e:
                    print(f"TTS播放错误: {e}")
                    break

                if self.is_playing:
                    self.current_sentence_index += 1
        except Exception as e:
            print(f"播放线程异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_playing = False
            if self.on_play_end:
                try:
                    self.on_play_end()
                except Exception:
                    pass

    async def _edge_speak(self, text: str):
        import edge_tts
        import tempfile
        import os

        try:
            voice_name = self.voices[self.voice_combo_index] if self.voice_combo_index < len(self.voices) else self.voices[0]
            output_path = Path(tempfile.mktemp(suffix='.mp3'))

            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(str(output_path))

            if output_path.exists():
                import winsound
                winsound.PlaySound(str(output_path), winsound.SND_FILENAME)
                os.remove(output_path)
        except Exception as e:
            print(f"Edge-TTS播放错误: {e}")

    def pause(self):
        if self.engine_type == "sapi" and hasattr(self.engine, 'Pause'):
            self.engine.Pause()
        self.is_paused = True

    def resume(self):
        if self.engine_type == "sapi" and hasattr(self.engine, 'Resume'):
            self.engine.Resume()
        self.is_paused = False

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        if self.engine_type == "sapi" and hasattr(self.engine, 'Speak'):
            try:
                self.engine.Speak("", 1)
                self.engine.WaitUntilDone(100)
            except Exception as e:
                print(f"停止TTS错误: {e}")

    def jump_to_sentence(self, index: int):
        if 0 <= index < len(self.sentences):
            self.current_sentence_index = index

    def get_current_sentence_index(self) -> int:
        return self.current_sentence_index

    def is_playing_status(self) -> bool:
        return self.is_playing

    def is_paused_status(self) -> bool:
        return self.is_paused

    def switch_engine(self, engine_type: str):
        if engine_type != self.engine_type:
            self.stop()
            self.engine_type = engine_type
            self._init_engine()

    def set_voice_combo_index(self, index: int):
        self.voice_combo_index = index