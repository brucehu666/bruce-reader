# -*- coding: utf-8 -*-
"""
TTS 引擎 - 支持 32 位语音通过 subprocess 调用
"""

import threading
import time
import subprocess
import os
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
        
        # 新增：32位语音支持
        self.voices_64bit = []      # 64位可用语音
        self.voices_32bit = []      # 仅32位可用语音
        self.voice_names = []       # 所有可用语音名称
        self.current_voice_type = "64bit"  # 当前选择的语音类型
        self.current_voice_index = 0
        
        self._init_engine()

    def _init_engine(self):
        try:
            import win32com.client
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            all_voices = self.engine.GetVoices()
            
            for v in all_voices:
                desc = v.GetDescription()
                print(f"检测到语音: {desc}")
                
                # 测试语音是否可用（64位环境）
                if self._test_voice(v):
                    self.voices_64bit.append(v)
                    self.voice_names.append(desc)
                    print(f"  -> 64位可用")
                else:
                    # 标记为仅32位可用
                    self.voices_32bit.append(desc)
                    self.voice_names.append(f"{desc} (32位)")
                    print(f"  -> 仅32位可用")
                    
        except Exception as e:
            print(f"TTS引擎初始化失败: {e}")
            self.engine = None
            self.voices_64bit = []
            self.voices_32bit = []
            self.voice_names = []

    def _test_voice(self, voice) -> bool:
        """测试语音是否可用"""
        try:
            original_voice = self.engine.Voice
            self.engine.Voice = voice
            self.engine.Speak("", 1)
            self.engine.WaitUntilDone(100)
            self.engine.Voice = original_voice
            return True
        except Exception:
            return False

    def get_voices(self) -> List[str]:
        return self.voice_names

    def set_voice(self, index: int):
        """设置语音"""
        if index < len(self.voices_64bit):
            self.current_voice_type = "64bit"
            self.current_voice_index = index
            if self.engine:
                self.engine.Voice = self.engine.GetVoices().Item(index)
        else:
            # 32位语音
            self.current_voice_type = "32bit"
            self.current_voice_index = index - len(self.voices_64bit)

    def set_rate(self, rate: float):
        if self.engine:
            self.engine.Rate = int((rate - 1.0) * 10)
        self._rate = rate

    def set_volume(self, volume: float):
        if self.engine:
            self.engine.Volume = int(volume * 100)
        self._volume = volume

    def _split_into_sentences(self, text: str) -> List[str]:
        import re
        sentences = re.split(r'[。！？.!?\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def play(self, text: str, start_position: int = 0):
        if self.is_playing:
            self.stop()
        
        self.current_text = text
        self.current_position = start_position
        self.sentences = self._split_into_sentences(text)
        self.current_sentence_index = start_position
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
                    if self.current_voice_type == "64bit":
                        # 使用64位引擎
                        self.engine.Speak(sentence)
                    else:
                        # 使用32位PowerShell
                        self._play_32bit(sentence)
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

    def _play_32bit(self, text: str):
        """通过32位PowerShell播放语音"""
        ps32_path = "C:\\Windows\\SysWOW64\\WindowsPowerShell\\v1.0\\powershell.exe"
        
        if not os.path.exists(ps32_path):
            print("未找到32位PowerShell")
            return
        
        # 获取语音名称
        voice_name = self.voices_32bit[self.current_voice_index]
        
        ps_command = f'''
        $speaker = New-Object -ComObject SAPI.SpVoice
        foreach ($v in $speaker.GetVoices()) {{
            if ($v.GetDescription() -match "{voice_name.replace(' ', ' ')}") {{
                $speaker.Voice = $v
                break
            }}
        }}
        $speaker.Speak("{text.replace('"', '\\"')}")
        '''
        
        try:
            subprocess.run(
                [ps32_path, "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='gbk'
            )
        except Exception as e:
            print(f"32位播放失败: {e}")

    def pause(self):
        if self.current_voice_type == "64bit" and self.engine:
            self.engine.Pause()
        self.is_paused = True

    def resume(self):
        if self.current_voice_type == "64bit" and self.engine:
            self.engine.Resume()
        self.is_paused = False

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        if self.current_voice_type == "64bit" and self.engine:
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