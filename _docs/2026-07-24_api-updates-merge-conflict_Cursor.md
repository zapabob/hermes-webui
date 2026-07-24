# 2026-07-24_api-updates-merge-conflict_Cursor.md

## 概要

`api/updates.py` の upstream/master マージコンフリクト（7箇所）を解消した。upstream のチャネル対応コア更新チェックを採用しつつ、fork の remote-tag フィルタ（`_remote_has_tag` / `require_remote_tag`）を再適用した。

## 背景・要求

- Prefer official upstream behavior/APIs for core update-check logic
- Preserve fork advantage: ignore local release tags missing from the configured update remote
- When both sides change the same function: upstream structure + re-apply fork tag-filtering
- Remove all conflict markers; no syntax errors
- Verify with `python -m py_compile api/updates.py` (`py -3` on Windows)

## 前提・判断

- upstream は stable/experimental チャネル、`_channel_up_to_date_info`、stable fallthrough 抑制を持つ
- fork は `_remote_has_tag`（`ls-remote`）と `require_remote_tag=True` でローカル専用タグ広告を防ぐ
- hybrid: upstream シグネチャ/ボディに `*, require_remote_tag=False` を追加

## 変更対象ファイル

- `api/updates.py`

## 実装詳細（コンフリクトサイト）

| # | 箇所 | 選択 |
|---|------|------|
| 1 | `_remote_has_tag` 定義 vs `_select_apply_compare_ref` シグネチャ | **hybrid**: fork の `_remote_has_tag` を残し、upstream の `(path, channel, target)` + fork の `require_remote_tag` |
| 2 | `_select_apply_compare_ref` ボディ | **hybrid**: upstream の channel/behind/stable ロジック + fork の remote-tag 未所持時 fallthrough |
| 3 | `_channel_up_to_date_info` / `_check_repo_release` 定義 | **hybrid**: upstream の `_channel_up_to_date_info` + channel 付き `_check_repo_release` + fork の `require_remote_tag` |
| 4 | `_check_repo_release` latest_tag 直後 | **hybrid**: fork の remote-tag gate + upstream の `_current_release_tag(path, channel)` |
| 5 | check 呼び出し `release_info = _check_repo_release(...)` | **hybrid**: `(path, name, channel, require_remote_tag=True)` |
| 6 | force-update `compare_ref` | **hybrid**: upstream の channel/target + None early-return + `require_remote_tag=True` |
| 7 | apply/pull `compare_ref` | **hybrid**: 同上 |

## 実行コマンド

```powershell
py -3.12 -m py_compile api\updates.py
# 補足: 既定の py -3 は Python 3.14 を指し、本環境では起動がハングしたため 3.12 で検証
```

## テスト・検証結果

- コンフリクトマーカー: 0（解消済み）
- `py -3.12 -m py_compile api/updates.py`: **成功**（exit 0）
- AST parse: **成功**

## 残留リスク

- Python 3.14（`py -3` 既定）が本機でハングするため、日常検証は `py -3.12` またはリポジトリ `.venv` を推奨
- remote-tag フィルタはネットワーク `ls-remote` を伴う（timeout=10）。オフライン時はタグ経路をスキップして branch 比較へ fallthrough

## 次の推奨アクション

- 必要なら `tests/test_updates.py` に remote-tag 欠落ケースの回帰テストを追加
- 他ファイルのマージコンフリクトが残っていれば同様に解消
