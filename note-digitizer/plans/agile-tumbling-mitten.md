# 重複処理バグ修正計画

## Context

Google Drive の一括スキャン同期時に、同一PDFが Obsidian に複数回出力される問題が発生した。
109ファイル中53件が重複（清掃済み）。再発防止と根本修正が目的。

---

## 根本原因（2つ）

### 原因1: タイマーとPollingObserverの競合
- `PollingObserver(timeout=3秒)` と `debounce_seconds=3秒` が同値
- タイマー発火とポーリングサイクルが重なり、`on_created`・`on_modified` が同時に `_process()` を起動
- `threading.Timer.cancel()` は発火済みには無効 → 並行処理が発生

### 原因2: `(n)` サフィックスを別ファイルと判定
- Google Drive 同期競合で `スキャン_1013 (1).pdf`、`(2).pdf` … が自動生成
- 現在は完全一致ファイル名をキーにするため全バリアントを処理

---

## 修正方針（Geminiアドバイス全実装）

| Geminiアドバイス | 実装内容 |
|---|---|
| キュー導入 | `queue.Queue` + 単一ワーカースレッド（並行排除） |
| 完了の永続化 | `_queued.discard()` は `mark_processed()` 完了後の `finally` で実行 |
| ファイル名正規化 | `normalize_filename()` で `(n)` を除去し正規化キーを使用 |
| ハッシュ以外の判定 | ファイルサイズ5%誤差許容チェックを追加 |

---

## 変更ファイル

### 1. `scripts/processed_tracker.py`

#### 1-1. モジュールレベル関数 `normalize_filename` を追加

```python
import re
_GDRIVE_SUFFIX_RE = re.compile(r'\s*\(\d+\)(?=\.[^.]+$)')

def normalize_filename(name: str) -> str:
    """Google Drive の (n) 競合サフィックスを除去した正規化キーを返す。
    例: 'スキャン_1013 (1).pdf' -> 'スキャン_1013.pdf'
    """
    return _GDRIVE_SUFFIX_RE.sub('', name)
```

正規表現の解説:
- `\s*\(\d+\)` : スペース + `(数字)` にマッチ
- `(?=\.[^.]+$)` : 直後に `.拡張子` が末尾にある場合のみ（本文中の括弧は除去しない）

#### 1-2. JSONスキーマ変更

**Before:** `{ "スキャン_1013 (1).pdf": "md5hash" }`

**After:** `{ "スキャン_1013.pdf": { "hash": "md5hash", "size": 204800 } }`

キーは正規化済みファイル名。値は `hash`（MD5）と `size`（バイト数）のオブジェクト。

#### 1-3. `_load()` に自動マイグレーション処理を追加

```python
def _load(self):
    if self.db_path.exists():
        try:
            raw = json.loads(self.db_path.read_text(encoding="utf-8"))
            # 旧形式 {filename: md5str} を検出して自動移行
            if raw and isinstance(next(iter(raw.values())), str):
                migrated = {}
                for filename, md5 in raw.items():
                    norm_key = normalize_filename(filename)
                    if norm_key not in migrated:  # 同一正規化キーは最初のものを採用
                        migrated[norm_key] = {"hash": md5, "size": None}
                self._processed = migrated
                self._save()
                logger.info("DBを新形式に移行: %d件 -> %d件", len(raw), len(migrated))
            else:
                self._processed = raw
        except Exception as e:
            logger.warning("DB読み込み失敗: %s", e)
            self._processed = {}
```

#### 1-4. `is_processed()` を更新（正規化キー + サイズ判定）

```python
_SIZE_TOLERANCE = 0.05  # 5%誤差許容

def is_processed(self, path: Path) -> bool:
    norm_key = normalize_filename(path.name)
    if norm_key not in self._processed:
        return False
    try:
        entry = self._processed[norm_key]
        # ハッシュ完全一致
        if entry["hash"] == self._hash(path):
            return True
        # サイズ近似（5%以内）→ 同一スキャンとみなす
        stored_size = entry.get("size")
        if stored_size is not None:
            current_size = path.stat().st_size
            ratio = abs(stored_size - current_size) / max(stored_size, current_size, 1)
            if ratio <= _SIZE_TOLERANCE:
                logger.info("サイズ近似で重複検出: %s (%d vs %d bytes)", path.name, stored_size, current_size)
                return True
        return False
    except Exception:
        return False
```

#### 1-5. `mark_processed()` を更新（正規化キー・サイズ保存）

```python
def mark_processed(self, path: Path):
    try:
        norm_key = normalize_filename(path.name)
        self._processed[norm_key] = {
            "hash": self._hash(path),
            "size": path.stat().st_size,
        }
        self._save()
        logger.info("処理済み登録: %s (キー: %s)", path.name, norm_key)
    except Exception as e:
        logger.warning("処理済み登録失敗: %s (%s)", path.name, e)
```

---

### 2. `scripts/watcher.py`

#### 2-1. インポートと `__init__` 変更

```python
import queue  # 追加
from processed_tracker import ProcessedTracker, normalize_filename  # normalize_filename 追加

class NoteHandler(FileSystemEventHandler):
    def __init__(self, ...):
        self._timers: dict[str, threading.Timer] = {}
        self._queued: set[str] = set()              # 正規化キーで二重エンキュー防止
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()    # 処理待ちキュー
        # ワーカースレッド起動（daemon=Trueでメイン終了時に自動停止）
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="note-worker"
        )
        self._worker.start()
        # ※ _in_progress は削除（Queueの単一ワーカーが代替）
```

#### 2-2. `_schedule()` の変更（呼び出し先を `_enqueue` に変更）

`_process` → `_enqueue` に1箇所変更するのみ。構造は変えない。

```python
timer = threading.Timer(
    self.config.debounce_seconds, self._enqueue, args=[path]  # _process → _enqueue
)
```

#### 2-3. `_enqueue()` を新設

```python
def _enqueue(self, path: Path):
    """デバウンス完了後に呼ばれる。正規化キーで重複チェックしてキューに積む。"""
    with self._lock:
        self._timers.pop(str(path), None)

    if not path.exists():
        return

    norm_key = normalize_filename(path.name)

    with self._lock:
        if norm_key in self._queued:
            logger.info("スキップ（キュー登録済み）: %s -> %s", path.name, norm_key)
            return
        if self.tracker.is_processed(path):
            logger.info("スキップ（処理済み）: %s", path.name)
            return
        self._queued.add(norm_key)

    logger.info("キューに追加: %s (キー: %s)", path.name, norm_key)
    self._queue.put(path)
```

`_queued` セットは正規化キーを使うため、`スキャン_1013.pdf` がキューにある状態で `スキャン_1013 (1).pdf` が届いても同じキーで弾かれる。

#### 2-4. `_worker_loop()` を新設

```python
def _worker_loop(self):
    """単一ワーカー。キューから1件ずつ取り出して逐次処理する。"""
    while True:
        try:
            path = self._queue.get(timeout=1)
        except queue.Empty:
            continue
        if path is None:  # シャットダウンシグナル
            break
        try:
            self._process(path)
        finally:
            self._queue.task_done()
```

#### 2-5. `_process()` を簡略化

並行制御が不要になるため、`_in_progress` 関連コードを削除してシンプルに。

```python
def _process(self, image_path: Path):
    """ワーカースレッドから逐次呼ばれる。並行処理なし。"""
    norm_key = normalize_filename(image_path.name)

    # 最終防御チェック（エンキュー後にファイル消失 or 別バリアントが先処理された場合）
    if not image_path.exists():
        logger.warning("ファイルが見つかりません: %s", image_path.name)
        with self._lock:
            self._queued.discard(norm_key)
        return
    if self.tracker.is_processed(image_path):
        logger.info("スキップ（処理済み、処理開始時確認）: %s", image_path.name)
        with self._lock:
            self._queued.discard(norm_key)
        return

    try:
        logger.info("=== パイプライン開始: %s ===", image_path.name)
        content = self.analyzer.analyze(image_path)
        output_path = self.writer.write(content, image_path.name)
        self.notifier.notify(content, output_path)
        self.tracker.mark_processed(image_path)
        logger.info("=== パイプライン完了: %s -> %s ===", image_path.name, output_path.name)
    except Exception:
        logger.exception("パイプライン処理中にエラー: %s", image_path.name)
    finally:
        with self._lock:
            self._queued.discard(norm_key)  # エラー時もリセット → 次回再試行可能
```

---

## 変更しないファイル

- `scripts/main.py` — 変更不要（シャットダウンは `daemon=True` で対応）
- `scripts/analyzer.py` — 変更不要
- `scripts/markdown_writer.py` — 変更不要
- `scripts/discord_notify.py` — 変更不要
- `scripts/config.py` — 変更不要

---

## 処理フロー（After）

```
ファイル検出 (on_created/on_modified)
  └─ _schedule() → debounceタイマー（3秒）
       └─ _enqueue()
            ├─ normalize_filename() でキー正規化
            ├─ _queued チェック → 登録済みならスキップ
            ├─ tracker.is_processed() → 処理済みならスキップ
            └─ _queue.put(path) + _queued.add(norm_key)
                  └─ _worker_loop() [単一スレッド、逐次]
                       └─ _process()
                            ├─ analyzer.analyze() [Gemini API]
                            ├─ writer.write() [Obsidian保存]
                            ├─ notifier.notify() [Discord]
                            ├─ tracker.mark_processed() [DB保存]
                            └─ finally: _queued.discard(norm_key)
```

---

## 動作確認手順

### 1. DBバックアップ
```bash
cp data/processed_files.json data/processed_files.json.bak
```

### 2. normalize_filename の単体確認
```bash
py -c "
import sys; sys.path.insert(0, 'scripts')
from processed_tracker import normalize_filename
cases = [
    ('スキャン_1013 (1).pdf', 'スキャン_1013.pdf'),
    ('スキャン_1013 (2).pdf', 'スキャン_1013.pdf'),
    ('スキャン_1013.pdf',     'スキャン_1013.pdf'),
    ('report(v2).pdf',       'report(v2).pdf'),
]
for name, expected in cases:
    r = normalize_filename(name)
    print('OK' if r == expected else 'FAIL', repr(name), '->', repr(r))
"
```

### 3. マイグレーション確認
```bash
# 起動ログで以下が出ることを確認
# "DBを新形式に移行: 55件 -> 43件" 等
py -m scripts.main  # 数秒で Ctrl+C
```

### 4. 重複防止の動作確認
- 監視フォルダに新しい PDF をコピー
- 直後に同ファイルを `(1)` サフィックスでコピー
- ログで `スキップ（キュー登録済み）` が出ることを確認
- Obsidian に1件のみ作成されることを確認

### 5. エラーリカバリー確認
- Gemini API キーを一時的に無効化して処理させる
- エラー後に同ファイルが再キューされることを確認（`mark_processed` が呼ばれない → 次回再試行）
