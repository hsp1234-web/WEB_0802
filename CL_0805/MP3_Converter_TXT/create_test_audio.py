import wave
import struct

# --- 參數 ---
output_filename = "test_audio.wav"
duration_seconds = 1
sample_rate = 16000  # 語音辨識常用的取樣率
num_channels = 1  # 單聲道
sampwidth = 2  # 2 bytes = 16 bits
num_frames = duration_seconds * sample_rate

# --- 產生無聲的音訊資料 ---
# 產生一個全部是 0 的位元組序列
silent_frame = struct.pack('<h', 0)  # '<h' 代表小端序的短整數 (16-bit)
frames = silent_frame * num_frames

# --- 寫入 WAV 檔案 ---
with wave.open(output_filename, 'wb') as wf:
    wf.setnchannels(num_channels)
    wf.setsampwidth(sampwidth)
    wf.setframerate(sample_rate)
    wf.writeframes(frames)

print(f"成功建立測試音訊檔: {output_filename}")
