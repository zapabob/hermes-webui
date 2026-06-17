# 実装ログ: Irodori TTS エンジン追加

- **日時**: 2026-06-18
- **実装AI**: Cursor Auto
- **ブランチ**: master（未コミット）

## 概要

Settings → Preferences の TTS エンジンに **Irodori TTS (server)** を追加。Hermes Agent の irodori プラグイン / ローカル OpenAI 互換サーバー（`POST /v1/audio/speech`）へ WebUI から読み上げ可能にした。

## 背景・要求

- ユーザー要望: TTS に irodoriTTS を追加
- 既存 ElevenLabs / Edge TTS と同じ `/api/tts` 契約に乗せ、fork 独自機能として Hermes Agent 側設定を追従

## 実装詳細

### Backend (`api/routes.py`)

- `engine=irodori` 分岐を追加
- 設定解決: `IRODORI_TTS_*` / `IRODORI_API_KEY` 環境変数、`~/.hermes/.env`、`config.yaml` の `tts.irodori` または `tts.provider: irodori`
- OpenAI 互換 `POST {base}/v1/audio/speech`（`response_format: mp3`）
- `speed` 0.25–4.0、`voice` / `model` は安全な ID 文字のみ許可
- `IRODORI_API_KEY` はループバック URL のみ送信（`IRODORI_TTS_ALLOW_REMOTE_API_KEY=1` で緩和）

### Frontend

- `static/index.html`: エンジン選択肢追加
- `static/panels.js`: irodori 用 voice リスト（none / hakua）
- `static/ui.js`: `_playIrodoriTts`、メッセージ読み上げ・自動読み上げ対応
- `static/boot.js`: ボイスモード対応
- `static/i18n.js`: en / ja の説明文更新

### Tests

- `tests/test_irodori_tts_engine.py`（5 passed）

## 実行コマンド

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_irodori_tts_engine.py -q
```

## 手動確認

1. Irodori-TTS-Server を `http://127.0.0.1:8088` で起動
2. Settings → Preferences → TTS Engine → **Irodori TTS (server)**
3. Voice を選択、メッセージ 🔊 または自動読み上げを試す

## 設定例

```yaml
# ~/.hermes/config.yaml
tts:
  provider: irodori
  irodori:
    base_url: http://127.0.0.1:8088
    voice: hakua
    model: irodori-tts
    speed: 1.0
```

または環境変数: `IRODORI_TTS_BASE_URL`, `IRODORI_TTS_VOICE`, `IRODORI_TTS_MODEL`, `IRODORI_API_KEY`

## 残留リスク

- voice 一覧は UI 固定（none/hakua）。サーバー側 voices.json からの動的取得は未実装
- 長文は 5000 文字 cap（Edge/ElevenLabs と同じ）。サーバー側 chunking に依存
