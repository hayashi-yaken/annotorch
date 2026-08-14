# annotorch フロントエンド Chakra UI 全面刷新 設計書

日付: 2026-08-14
ブランチ: feature/intro_chakra（develop @ 29bec9f から分岐）
ステータス: 承認済み設計（実装計画は未作成）

## 概要

annotorch のフロントエンドは計画3でMVPとして素のCSS・最小実装で作られた。
機能は揃っているが見た目・操作性が分かりにくい（代表例: ブラウザ標準の
`<input type="file">` ボタンが「画像用」「テキスト用」のどちらか判別できない）。
本改修では UI を **Chakra UI v3 に全面刷新**して分かりにくさを解消する。

**ロジックは一切変えない。** プレゼンテーション層（各コンポーネントの
見た目）だけを Chakra UI に載せ替え、振る舞い（回答JSONの形、キーボード操作、
状態遷移、API呼び出し）は現状を維持する。

## スコープと前提

- **対象**: `frontend/src/` のUIコンポーネントとページ、グローバルスタイル、
  エントリポイント（main.tsx）。
- **変更しないもの**:
  - `frontend/src/lib/*`（splits / softlabel / groupstate）と Vitest テスト10件
    → 実装後も全件グリーンを維持する
  - `frontend/src/api.ts`（計画2バックエンドとの契約。型・メソッド・エンドポイント）
  - 各コンポーネントの**振る舞い**: onSave が emit する回答JSONの形
    （label / dist / winner 1|-1|0|null / score|same / order / groups）、
    キーボード操作（数字キー、←/→/=/space）、`key={unit.id}` によるエディタ状態リセット、
    保存→自動前進フロー、フェッチエラー処理
- **MVPからの制約変更**: 計画3の「依存追加なし」制約を意図的に外し、Chakra UI と
  その peer 依存（@emotion/react）を追加する。ユーザーが明示的に選択した方針。

## 技術選定

- **Chakra UI v3**（`@chakra-ui/react` v3）+ `@emotion/react`（peer 依存）を追加。
  v3 は v2 と API が大きく異なる（`ChakraProvider value={system}`、`createSystem`、
  コンポーネント構成）ため、**実装時は context7 で v3 の API を都度確認**しながら進める。
- **デフォルトテーマ**（`defaultSystem`）を使用。独自デザイントークンは作らない。
  ブランドテーマ化は将来の別作業として口だけ空けておく。
- `main.tsx` を Chakra の `Provider`（`ChakraProvider value={defaultSystem}`）でラップ。
- 素CSS（`frontend/src/index.css`）は撤去し、グローバルスタイルは Chakra の
  リセット/ベースに委ねる。

## 現状のフロント構成（参考）

ロジックとプレゼンテーションが分離済みで、見た目の載せ替えがしやすい:

```
frontend/src/
├── api.ts                    # バックエンド契約（変更しない）
├── lib/                      # 純関数 + Vitest（変更しない）
│   ├── splits.ts / .test.ts
│   ├── softlabel.ts / .test.ts
│   └── groupstate.ts / .test.ts
├── components/
│   ├── ItemView.tsx          # 画像/テキスト表示
│   ├── ImportPanel.tsx       # ★分かりにくさの本丸（ファイル選択）
│   ├── TaskForm.tsx
│   ├── ExportPanel.tsx
│   └── answer/               # 6エディタ + types.ts
│       ├── HardLabel / SoftLabel / Preference
│       ├── Similarity / Ranking / Grouping
│       └── types.ts (EditorProps)
├── pages/
│   ├── ProjectsPage.tsx      # 一覧・作成・削除
│   ├── ProjectPage.tsx       # items/tasks + 3パネル
│   └── AnnotatePage.tsx      # Unit提示 + エディタ出し分け
├── App.tsx                   # useState による3画面遷移
├── main.tsx                  # エントリ
└── index.css                 # 撤去対象
```

全コンポーネント合計 約666行と小さくまとまっている。

## フェーズ構成（段階刷新）

土台 → ページ順。各フェーズ末で型チェック + ビルド + 動作確認 → コミット。
フェーズはこのブランチに積み、最後にまとめて develop へマージする。

### フェーズ0: Chakra 導入（土台）

- `@chakra-ui/react` v3 + `@emotion/react` を追加
- `main.tsx` を `Provider`（`defaultSystem`）でラップ、`index.css` の import を外す
  （ファイル自体はフェーズ4で削除）
- 共通レイアウトの器（`Container` ベースのページ枠、ヘッダ）を用意
- 確認: ビルドが通り、既存UIが表示され、ロジックテスト10件がグリーン

### フェーズ1: ProjectsPage + ItemView

- プロジェクト一覧・作成・削除を Chakra 化（`Card` / `Button` / `Input`、
  削除は確認ダイアログ）
- `ItemView`（画像 `<img>` / テキスト表示）を `Image` / `Text` / `Box` に

### フェーズ2: ProjectPage の3パネル（分かりにくさの本丸）

- **ImportPanel（最優先）** — ブラウザ標準のファイル選択を Chakra v3 の
  `FileUpload` に置き換え、「画像用」「テキスト（JSONL/CSV）用」が一目で分かるUIに。
  ドラッグ&ドロップは `FileUpload` のドロップゾーンで表現。フォルダ取り込みは
  `Input` + ボタン。取り込み結果レポートも整理して表示
- **TaskForm** — presentation × question の選択を `Select` / `RadioCard` に、
  条件付き設定フォーム（labels / similarity_mode / num_units / group_size / seed）を整理
- **ExportPanel** — 出力先・splits・seed 入力と結果・サンプルコードを `Card` / `Code` で
- 進捗バーは Chakra の `Progress`

### フェーズ3: AnnotatePage + 6エディタ

- 提示レイアウト・進捗・ナビゲーションを Chakra 化
- 6エディタを Chakra コンポーネントに:
  - HardLabel: ラベルボタン群（数字キー対応は維持）
  - SoftLabel: `Slider` + 正規化表示
  - Preference: 左右並列 + 選好ボタン（←/→/=/space 維持）
  - Similarity: binary は同/違ボタン、continuous は `Slider`
  - Ranking: クリックで順位付け（`Card` の選択状態）
  - Grouping: グループ選択 + アイテムクリック割当（`Card` の色分け）
- **onSave が出す回答JSON・キーボード操作・状態遷移は不変**

### フェーズ4: 仕上げ

- `index.css` 削除、scaffold 残骸の最終確認
- 全画面の通し確認（Playwright で6方式を一巡）
- README に変更点を軽く追記（任意）

## 品質の担保

- **UIコンポーネントテストは追加しない。** 今回はプレゼンテーション層の載せ替えが
  主で、振る舞いは既存のロジックテスト＋既存バックエンドで守られている。
- 各フェーズ末の確認: `npx tsc --noEmit`（または `npm run build` = tsc + vite build）、
  ビルド成功、実際に起動しての動作確認（必要に応じて Playwright で操作）。
- ロジックテスト10件（`npm run test`）は常にグリーンを維持。
- 「都度改修して、うまくいくことを確認してからマージ」— 各フェーズを小さくコミットし、
  ブランチ全体が通し確認できた段階で develop へマージ。

## 将来の拡張（今回スコープ外）

- 独自ブランドテーマ（`createSystem` でのカラー/フォント定義）
- トースト通知・高度なローディング状態などのUX追加（MVPで削った要素）
- UIコンポーネントの自動テスト（@testing-library/react）
- E2E の自動化（CI での Playwright）
