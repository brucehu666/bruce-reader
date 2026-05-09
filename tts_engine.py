import threading
import time
from typing import Optional, Callable, List


class TTSEngine:
    def __init__(self):
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
        self._init_engine()

    def _init_engine(self):
        try:
            import win32com.client
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            all_voices = self.engine.GetVoices()
            self.voices = []
            self.voice_names = []
            for v in all_voices:
                desc = v.GetDescription()
                if "Zira" not in desc:
                    self.voices.append(v)
                    self.voice_names.append(desc)
        except Exception as e:
            print(f"TTS引擎初始化失败: {e}")
            self.engine = None
            self.voices = []
            self.voice_names = []

    def get_voices(self) -> List[str]:
        return self.voice_names

    def set_voice(self, index: int):
        if self.engine and 0 <= index < len(self.voices):
            self.engine.Voice = self.engine.GetVoices().Item(index)

    def set_rate(self, rate: float):
        if self.engine:
            self.engine.Rate = int((rate - 1.0) * 10)

    def set_volume(self, volume: float):
        if self.engine:
            self.engine.Volume = int(volume * 100)

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

    def pause(self):
        if self.engine:
            self.engine.Pause()
        self.is_paused = True

    def resume(self):
        if self.engine:
            self.engine.Resume()
        self.is_paused = False

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        if self.engine:
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
