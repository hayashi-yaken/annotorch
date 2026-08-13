# annotorch 設計書

日付: 2026-08-12
ステータス: 承認済み設計（実装計画は未作成）

## 概要

UI上で画像・テキストなどにアノテーションを行い、PyTorch の MNIST のように
`DataLoader` でそのまま読めるデータセットを生成するローカルツール。

アノテーション方式はハードラベル・ソフトラベル・ペアワイズ（選好/類似性）・
グループワイズ（順位付け/グルーピング）に対応する。

## スコープと前提

- **利用形態**: 現状はローカルで使うことを想定。ただしデータモデルは
  複数アノテーターを前提に設計し、将来のチーム利用にスキーマ変更なしで対応できるようにする。
- **モダリティ**: v1 の実装は画像とテキスト。データモデル上は「Item = 任意のモダリティの1件」
  として抽象化し、音声等を後から追加できるようにする。

## アーキテクチャ

単一Pythonパッケージ + optional extras 構成。

```
annotorch/
├── src/annotorch/
│   ├── domain/           # 純粋ドメイン: models / answers(検証) / units(生成)。I/Oなし
│   ├── storage/          # 永続化: ProjectStore(Protocol) / SQLite実装 / Workspace
│   ├── services/         # ユースケース層: ProjectService / TaskService / ExportService
│   ├── server/           # HTTPアダプタ: FastAPI。routers/ はリソース単位（[server] extra）
│   │   └── static/       # React のビルド成果物を同梱
│   ├── datasets/         # torch.utils.data.Dataset 実装（エクスポート形式のみに依存）
│   └── cli.py            # CLIアダプタ: `annotorch serve` / `annotorch export`
├── frontend/             # React + TypeScript + Vite（開発時のみ。ビルドして static へ）
├── Dockerfile            # サーバー（[server] extra + ビルド済みフロント）のイメージ
├── docker-compose.yml    # `docker compose up` でアノテーションサーバーを起動
├── docs/superpowers/specs/
└── tests/
```

**レイヤーの依存規則（一方通行）:**

- `domain` → 何にも依存しない（pydanticのみ）。モデル・回答検証・Unit生成の純粋ロジック
- `storage` → `domain`。DBに触れるのはこの層だけ。`ProjectStore`（Protocol）を公開し、
  SQLite実装がそれを満たす。将来の複数人化はRDB実装の追加とservicesへの注入で行う
- `services` → `domain` + `storage`。ユースケースの唯一の入口で、CLIとHTTPの両方がここを呼ぶ
- `server` / `cli` → `services`（+ domainの型）。ロジックを書かない薄いアダプタ。
  HTTPを知るのは server だけ
- `datasets` → どのレイヤーにも依存しない。エクスポート成果物（ファイル形式）だけを読む

- コア層（domain / storage / services / datasets）の依存は
  pydantic + torch + Pillow + numpy 程度に抑える。
  `pip install annotorch[server]` で FastAPI + uvicorn が入る。
  学習環境にはコア層だけ入れればよい。
- サーバーの起動は **Docker が主経路**: `docker compose up` で FastAPI サーバーが立ち、
  `http://localhost:8000` をブラウザで開く。作業データディレクトリ（`~/.annotorch` 相当）は
  ボリュームマウントで永続化する。開発時・Dockerなし環境向けに
  `annotorch serve`（`[server]` extra）も残す。
- Docker 実行時のインポートの注意: コンテナからはホストのファイルが見えないため、
  UI からのドラッグ&ドロップアップロードを基本とする。フォルダパス指定インポートは
  compose でマウントしたディレクトリ（例: `./import` → `/import`）に対してのみ機能する。
- 作業中データは SQLite、エクスポート成果物は SQLite に依存しない自己完結のファイル群。
  この2層を完全に分離する。
- プロジェクトの作業データは `~/.annotorch/projects/<id>/` に置く
  （SQLite ファイルと取り込んだ Item の実体）。

## データモデル

SQLite の5テーブル。`schema_version` を持ち、将来の変更はマイグレーションで対応する。

### Project

1つのデータセット作成作業の単位。名前・説明。

### Item

アノテーション対象1件。

- `modality`: `image` / `text`（拡張可能）
- 実体参照: 画像はプロジェクトデータディレクトリにコピーしたファイルパス、
  テキストは本文そのもの
- 任意のメタデータ JSON

UIの表示だけが modality に依存し、他の層は Item を不透明に扱う。

### Task

「どういう質問で注釈するか」の定義。直交する2軸で表す:

- `presentation`: `single` / `pair` / `group`
- `question`:
  - single 用: `hard_label` / `soft_label`
  - pair 用: `preference` / `similarity`
  - group 用: `ranking` / `grouping`

加えて質問ごとの設定を JSON で持つ: ラベルスキーマ（クラス名と色）、
similarity の二値/連続の別、group のサイズ、Unit生成方法（v1はランダム）など。
1プロジェクトに複数 Task を作れる（同じ Item 集合に対して別方式の注釈が可能）。

### Unit

アノテーションの提示1回分。Task 作成時に生成され、対象 Item（1個/2個/N個）の
並びを保持する。「どのペア・グループを見せたか」の記録を兼ねる。

- single: 全 Item 分を生成
- pair / group: 指定件数をランダムサンプリングで生成（生成戦略は差し替え可能な設計にする）

### Annotation

Unit に対する回答。`annotator_id` + 回答 JSON + タイムスタンプ。
同じ Unit に複数 Annotator の回答を付けられる。

回答 JSON の形式（質問タイプごとに固定、サーバー側で Pydantic により厳密に検証）:

| question   | 回答JSONの例                             | 検証                                    |
| ---------- | ---------------------------------------- | --------------------------------------- |
| hard_label | `{"label": "cat"}`                       | ラベルスキーマに存在するクラス          |
| soft_label | `{"dist": {"cat": 0.7, "dog": 0.3}}`     | 合計 ≈ 1                                |
| preference | `{"winner": 1}` — 1=item_idsの1番目の勝ち, -1=2番目, 0=tie, null=skip | 1 / -1 / 0 / null |
| similarity | `{"score": 0.8}` または `{"same": true}` | Task設定（二値/連続）に一致             |
| ranking    | `{"order": [item_id, ...]}`              | Unit の Item 集合の順列                 |
| grouping   | `{"groups": [[item_id, ...], ...]}`      | Unit の Item 集合の分割（網羅・非重複） |

### Annotator

回答者。v1 ではデフォルト1人を自動使用し、UIには出さない（設定で名前のみ変更可）。

## UI とフロー

画面は5系統。キーボード主体で高速に回せることを重視する。
**作り込みは最小限でよい**（素朴なスタイリング・最低限のコンポーネントで、
全アノテーション方式が一通り操作できることを優先する）。

1. **プロジェクト画面** — 一覧・作成・削除
2. **インポート画面** — 画像: フォルダパス指定 or ドラッグ&ドロップアップロード。
   テキスト: JSONL/CSV アップロード。取り込んだ実体はプロジェクトデータディレクトリに
   コピーし、元ファイルの移動・削除の影響を受けない
3. **Task作成画面** — presentation × question を選択し、質問タイプに応じた設定フォームを表示。
   作成時に Unit を生成
4. **アノテーション画面** — Unit を順に提示。presentation ごとのレイアウト:
   - single: アイテムを大きく表示 + ラベルボタン。hard_label は数字キー 1〜9 で即答→自動で次へ。
     soft_label は各クラスのスライダー + 正規化して保存
   - pair: 左右に並べて表示。←/→/= キーで A/B/tie、スペースでスキップ
   - group: ranking は並べ替え、grouping はグループ枠への振り分け（枠はその場で追加可能）。
     最小実装ではドラッグ&ドロップではなくクリック操作でよい
   - 共通: 進捗バー（済/全Unit数）、戻って修正、中断・再開自由（回答は都度 SQLite に保存）
5. **エクスポート画面** — Task を選んで「データセット作成」。オプション: 出力先、
   train/val/test 分割比（任意）、乱数シード。完了後、出力パスと読み込みサンプルコードを表示

## エクスポート形式

1 Task = 1 データセット。自己完結なファイル群（zip で配布可能）。

```
my-dataset/
├── manifest.json        # 形式バージョン、presentation/question、クラス一覧、split定義、集約設定、エンコード規約
├── items/               # 画像ファイル群（テキストの場合は items.jsonl）
└── annotations.jsonl    # 1行 = 1 Unit 分の確定アノテーション（参照item + 回答 + split名）
```

**複数アノテーターの集約**: エクスポート時に選択する。

- `raw`: 全回答をそのまま出力（annotator_id 付き）
- `aggregate`: ハードは多数決、ソフトは平均、選好は勝率などで1行に集約

v1 は1人利用なので実質パススルーだが、manifest とスキーマには最初から集約設定を記録する。
「複数人のハード投票 → ソフトラベルとしてエクスポート」も集約の一種として将来入れられる
（v1 では実装しない）。

## Dataset API（学習コード側）

```python
from annotorch.datasets import load
from torch.utils.data import DataLoader

ds = load("path/to/my-dataset", split="train", transform=my_transform)
loader = DataLoader(ds, batch_size=32, shuffle=True)
```

`load()` は manifest を見て適切な Dataset クラスを返す。`ds[i]` の返り値:

| question           | 返り値                                                                                                                        |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| hard_label         | `(image, label_idx)`                                                                                                          |
| soft_label         | `(image, dist_tensor)` — shape `(num_classes,)`                                                                               |
| preference         | `((img_a, img_b), winner)` — 保存値そのまま（1=1番目, -1=2番目, 0=tie。skip=null はエクスポート時に除外済み） |
| similarity         | `((img_a, img_b), score)`                                                                                                     |
| ranking / grouping | `(images_list, order / group_ids)` — 可変長のため `ds.collate_fn` を同梱し、`DataLoader(ds, collate_fn=ds.collate_fn)` で使う |

共通属性: `ds.classes`（クラス名リスト、分類系のみ）、`ds.manifest`（メタ情報）。
transform は Item ごとに適用される（pair/group では各アイテムに適用）。

## エラー処理

- **インポート**: 読めない・非対応のファイルはスキップし、
  「取り込みN件、スキップM件（理由つき）」のレポートを返す。全滅でもクラッシュしない
- **回答の検証**: 上記テーブルの通り Pydantic でサーバー側検証。不正は UI にエラー表示
- **エクスポート**: 一時ディレクトリに書き切ってから rename で確定
  （途中失敗で壊れた成果物を残さない）。未回答 Unit がある場合は警告を出し、
  「回答済み分のみで作成」を選択可能
- **スキーマ変更**: `schema_version` によるマイグレーション

## テスト戦略

- **ラウンドトリップテスト（最重要）**: コードでプロジェクト作成 → Item 投入 →
  アノテーション付与 → エクスポート → `annotorch.datasets.load()` で読み込み →
  `DataLoader` を1周回して shape と値を検証。全質問タイプ × 画像/テキストで用意する
- core / export / datasets: pytest ユニットテスト
- API: FastAPI TestClient
- フロントエンド: v1 は重要ロジックのみ Vitest（ソフトラベル正規化、
  グルーピング操作の状態管理）。E2E は後回し
- 実装は TDD（superpowers:test-driven-development）で進める

## v1 に含めないもの（将来の拡張）

- 複数アノテーターの UI・ユーザー管理（データモデルは対応済み）
- 投票からのソフトラベル集約（集約機構の口だけ用意）
- 音声等の追加モダリティ（Item 抽象化で対応可能）
- ペア/グループ Unit のアクティブサンプリング等の高度な生成戦略（差し替え可能な設計のみ）
- E2E テスト
