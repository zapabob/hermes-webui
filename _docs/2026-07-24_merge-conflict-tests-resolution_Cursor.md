# 実装ログ: テスト3ファイルのマージコンフリクト解消

- 日付: 2026-07-24
- 実装AI: Cursor (Composer / Auto)

## 概要

`upstream/master` マージ中のコンフリクトを、指定されたテスト3ファイルのみ解消した。方針は upstream 側の最新カバレッジを優先。

## 背景・要求

対象:

1. `tests/test_updates.py`
2. `tests/test_issue4856_android_scroll_regression.py`
3. `tests/test_issue4970_stream_done_shrink_regression.py`

ポリシー:

- 原則 `upstream/master` を採用
- `test_updates.py` の fork 固有「update remote に無い upstream-only tag を無視」系は、`api/updates.py` マージ後と整合するときのみ残す
- issue 回帰は upstream 全面（HEAD に固有 assertion があれば union）

## 前提・判断

- `api/updates.py` 側も `_remote_has_tag` / `require_remote_tag` 周りで未解消コンフリクトあり
- fork テストは `_select_apply_compare_ref(..., require_remote_tag=True)` 等 HEAD 固有シグネチャに依存
- upstream の `_select_apply_compare_ref(path, channel=..., target=None)` とは非互換 → **不確実のため fork テストは落とす**（ポリシーどおり）
- issue4856 / issue4970 の conflict 区間は HEAD 側が空、upstream のみ追加テスト → upstream 全面採用

## 変更対象ファイル

- `tests/test_updates.py` — `git checkout --theirs`（upstream）
- `tests/test_issue4856_android_scroll_regression.py` — 同上
- `tests/test_issue4970_stream_done_shrink_regression.py` — 同上

## 実装詳細

- 全 `<<<<<<<` / `=======` / `>>>>>>>` マーカー除去済み
- `ast.parse` で Python 構文確認済み
- ステージ済み（`git add`）

### 採用した upstream 追加カバレッジ

- `test_updates.py`: git lock / clear_lock / force-update lock 契約一式（PR #5688 系）
- `test_issue4856_...`: deferred release / CSS max-height extender / behavioral re-arm & hard-cap
- `test_issue4970_...`: `_prescrollSnapshot` behavioral harness

### 落とした HEAD 固有テスト（再導入候補）

- `test_check_repo_ignores_release_tag_missing_from_update_remote`
- `test_select_apply_compare_ref_falls_through_when_tag_missing_from_update_remote`

再導入条件: `api/updates.py` で `_remote_has_tag` と `require_remote_tag` が upstream API（channel/target）と整合して残る場合。

## 実行コマンド

```powershell
git checkout --theirs -- tests/test_updates.py tests/test_issue4856_android_scroll_regression.py tests/test_issue4970_stream_done_shrink_regression.py
rg -n "^<<<<<<<|^=======|^>>>>>>>" ...  # no matches
python -c "import ast; ..."  # parse ok
git add -- <three files>
```

## テスト・検証結果

- コンフリクトマーカー: なし
- `ast.parse`: 3ファイルとも OK
- pytest 実行: 未実施（本タスクはコンフリクト解消のみ）

## 残留リスク

- `api/updates.py` が fork の remote-tag ガードを残す場合、上記2テストが未カバーになる
- ステージ済みだがコミットは未実施（依頼なし）

## 次の推奨アクション

1. `api/updates.py` のコンフリクトを upstream 優先で解消
2. `_remote_has_tag` を残すなら fork テストを upstream シグネチャに合わせて再追加
3. `./scripts/test.sh` で該当テストを実行
