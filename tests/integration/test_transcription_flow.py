# tests/integration/test_transcription_flow.py
import pytest
from fastapi.testclient import TestClient
import wave
import io
from pathlib import Path

# 由於我們是從 tests 目錄執行，需要將 src 加入 sys.path
# conftest.py 通常會處理這個，但為了明確起見，我們可以在這裡做
import sys
# 假設專案根目錄是 tests/../
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 現在我們可以從 phoenix_core 導入 app
# 注意：直接從 main 導入 app 會觸發所有模組的加載
# 這也是一個很好的方法來檢查是否有任何啟動時的 import 錯誤
try:
    from phoenix_core.main import app
except RuntimeError as e:
    # 如果在導入時就發生了 'python-multipart' 相關的錯誤，
    # pytest 會捕獲它並顯示，這有助於早期診斷。
    pytest.fail(f"無法導入 FastAPI app，可能是因為相依性問題: {e}")


client = TestClient(app)

@pytest.fixture(scope="module")
def dummy_wav_file() -> tuple[str, bytes]:
    """
    在記憶體中建立一個假的 WAV 檔案內容。

    Returns:
        一個包含 (檔名, 檔案內容 bytes) 的元組。
    """
    file_name = "test_audio.wav"
    # 使用 io.BytesIO 在記憶體中操作二進位數據
    buffer = io.BytesIO()

    # WAV 檔案參數
    nchannels = 1
    sampwidth = 2  # 16-bit
    framerate = 16000
    nframes = 16000  # 1 second of audio

    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.setnframes(nframes)
        # 寫入一些靜音的 frame
        wf.writeframes(b'\x00' * nframes * nchannels * sampwidth)

    # 取得 buffer 中的 bytes 內容
    file_content = buffer.getvalue()
    return file_name, file_content

def test_upload_audio_file_creates_transcription_task(dummy_wav_file):
    """
    測試上傳音訊檔案的 API 端點 (`/transcription/upload`)。

    這個測試會：
    1. 使用 fixture 建立一個假的 WAV 檔案。
    2. 模擬一個 multipart/form-data 的 POST 請求來上傳檔案。
    3. 驗證 API 回應的狀態碼是否為 202 (Accepted)。
    4. 驗證回應的 JSON body 中是否包含一個 'task_id' 鍵。
    5. 驗證 'task_id' 的值是一個字串 (通常是 UUID)。
    """
    file_name, file_content = dummy_wav_file

    # FastAPI TestClient 需要檔案以 ('filename', file_content, 'content_type') 的形式提供
    files = {'file': (file_name, file_content, 'audio/wav')}

    # 發送請求
    response = client.post("/transcription/upload", files=files)

    # 驗證回應
    assert response.status_code == 202, f"預期狀態碼為 202，但收到 {response.status_code}。回應內容: {response.text}"

    response_json = response.json()
    assert "task_id" in response_json, "回應的 JSON 中缺少 'task_id' 欄位"
    assert isinstance(response_json["task_id"], str), "'task_id' 應該是一個字串"
    assert len(response_json["task_id"]) > 0, "'task_id' 不應該是空的"
