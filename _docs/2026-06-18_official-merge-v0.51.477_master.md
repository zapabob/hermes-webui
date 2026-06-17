# 実装ログ: 公式 upstream v0.51.477 マージ（fork 独自機能維持）

- **日時**: 2026-06-18（ローカル作業環境）
- **実装AI**: Cursor Auto
- **ブランチ**: `master`
- **マージコミット**: `f65add87`

## 概要

`scripts/merge_official_updates.py` で公式 `nesquena/hermes-webui` の `master`（タグ `v0.51.477`）を取り込み、fork 独自の OpenCode / Windows ラッパー / 更新チェック調整を維持した。ローカルは `v0.51.434` 相当から **43 リリース分**（v0.51.435〜v0.51.477）を追従。

## 背景・要求

- 公式の最新機能・脆弱性修正・バグフィックスを取り込む
- 独自機能は公式 API に追従し、同等なら公式実装をベースに fork の利点だけ残す
- Python マージスクリプトで再現可能な手順にする

## 前提・判断

| 項目 | 判断 |
|------|------|
| マージ手段 | 既存 `scripts/merge_official_updates.py`（fetch → merge-tree プレビュー → `git merge`） |
| memory write シンボリックリンク | **公式方針を採用**: ターゲットファイル（MEMORY.md 等）のみ拒否。親 `memories/` ディレクトリの symlink は許可（#4242 maintainer decision） |
| ローカル独自の「memories ディレクトリ symlink 拒否」 | 公式と同等領域のため **削除して公式に追従** |
| OPENCODE_API_KEY 共有検出 | `api/config.py` でマージ後も維持（公式 per-key と併存） |
| Windows ラッパー / 更新チェック fork 修正 | `CHANGELOG [Unreleased]` に記録しコードは維持 |

## 変更対象ファイル（競合解消）

- `CHANGELOG.md` — 公式 v0.51.435〜477 エントリ + fork `[Unreleased]` 節
- `README.md` — 追跡バージョン `v0.51.193` → `v0.51.477`
- `api/routes.py` — `_handle_memory_write` を公式 API 形に統一
- `tests/test_memory_write_symlink_guard.py` — 公式テスト（親 dir symlink 許可）に統一
- `tests/test_bootstrap_python_selection.py` — 公式の `_repo_venv_python` ヘルパー採用

その他 **100+ ファイル** は公式側の自動マージ（競合なし）。

## 取り込んだ主な公式変更（v0.51.435 → v0.51.477）

- **#4362** Gateway runs-API ルーティングを opt-in 化（デフォルト off、コンテキスト喪失防止）
- **#4363** クロスプロバイダモデル選択のサイレント revert 修正
- **#4356** 非 git インストールの更新チェックを「Can't check」表示に
- **#3510** ElevenLabs TTS エンジン
- **#4348** WebUI セッション source フラグの state.db 整合
- **#4341** キャンセル済み user context チェーンのクリーンアップ
- **#4339** 画像+テキスト同時ペースト
- **#3850** 設定検索
- **#4325** トランスクリプト仮想化（デフォルト OFF + opt-out）
- **#3970** オンボーディング OAuth single-flight
- **#4242** memory write symlink ターゲット拒否（skills/file と同系列）
- **#3908** `scripts/test.sh` + `requirements-dev.txt`（サポート Python 3.11–3.13）

## 維持した fork 独自機能

- `scripts/merge_official_updates.py`
- `OPENCODE_API_KEY` による Zen/Go 共有検出（`api/config.py`）
- `scripts/windows/start-hermes-webui-native.ps1`（パスワード注入・ブラウザ起動）
- fork 向け更新チェック（upstream-only タグ無視、`api/updates.py` 周辺）
- Windows ネイティブ起動時の Agent `.venv` 優先

## 実行コマンド

```powershell
cd "C:\Users\downl\Documents\New project\hermes-WebUI"
git fetch upstream --prune --tags
py -3 scripts/merge_official_updates.py --dry-run --log-limit 40
py -3 scripts/merge_official_updates.py
# 競合解消後
git commit --no-edit
```

検証（隔離 agent dir + repo `.venv`）:

```powershell
$tmpdir = Join-Path $env:TEMP "hermes-webui-merge-test"
$env:HERMES_WEBUI_AGENT_DIR = $tmpdir
$env:HERMES_WEBUI_PYTHON = ".\.venv\Scripts\python.exe"
$env:HERMES_HOME = Join-Path $tmpdir "home"
$env:HERMES_WEBUI_STATE_DIR = Join-Path $tmpdir "state"
.\.venv\Scripts\python.exe -m pytest tests/test_memory_write_symlink_guard.py `
  tests/test_bootstrap_python_selection.py tests/test_issue4356_no_git_update_check.py -q
```

## テスト・検証結果

- `py -3.12 -m venv --clear .venv` + `pip install -r requirements-dev.txt` で repo venv 再構築（旧 venv が別ユーザー path を参照していたため）
- 上記 focused pytest: **10 passed, 2 skipped**（symlink 非対応環境で skip）
- `git merge-base --is-ancestor official/master HEAD` → **成功**（公式 master を完全包含）

未実施:

- フルスイート（~7150 tests）— CI / `./scripts/test.sh` 推奨
- 手動ブラウザ smoke（gateway / ElevenLabs TTS / 設定検索）

## 残留リスク

- 大規模マージのため、未実行の回帰テスト領域（gateway chat、仮想化スクロール、OAuth）は手動確認余地あり
- ローカル `hermes-agent` venv が壊れている環境では conftest の test_server が失敗する（`HERMES_WEBUI_AGENT_DIR` 隔離で回避可能）
- `origin/master` への push は未実施

## 次の推奨アクション

1. `git push origin master` で fork リモートへ反映
2. `./scripts/test.sh` または CI でフルスイート確認
3. 次回も `py -3 scripts/merge_official_updates.py --dry-run` で公式差分を定期確認
