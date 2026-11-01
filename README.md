# annotorch

画像・テキストにブラウザ上でアノテーション（ハードラベル / ソフトラベル /
ペアワイズ選好・類似性 / グループ順位付け・グルーピング）を行い、
PyTorch の `DataLoader` でそのまま読めるデータセットを作るローカルツール。

## 起動（Docker）

```bash
docker compose up --build
# → http://localhost:8000 をブラウザで開く
```

作業データは volume `annotorch-data` に永続化される。
フォルダ取り込みを使う場合はホストの `./import` に画像を置き、
UI では `./import` からの相対パス（例: `swan`）を指定する。`./import` の外は読めない。
エクスポートは、UI で指定したデータセット名のフォルダとしてホストの `./export` に出力される。
「ZIP でダウンロード」を使うと、ブラウザから手元の好きな場所に保存できる。

## 起動（Docker なし・開発用）

```bash
uv sync --extra server
cd frontend && npm install && npm run build && cd ..
uv run annotorch serve
```

フォルダ取り込みはホームディレクトリの内側だけ、エクスポートは `~/.annotorch/exports` の下だけに限られる。
変えるときは `--import-root` / `--export-root` を指定する。CLI の `annotorch export --out` はどこにでも書き出せる。

## 作ったデータセットを使う

```bash
pip install -e ".[torch]"   # 学習環境に
```

```python
from torch.utils.data import DataLoader
from annotorch.datasets import load

ds = load("path/to/exported-dataset", split="train", transform=my_transform)
loader = DataLoader(ds, batch_size=32, shuffle=True)
```

質問タイプごとの `ds[i]` の形式や preference の符号規約
（1 = 1番目の勝ち, -1 = 2番目, 0 = tie）は
`docs/superpowers/specs/2026-08-12-annotorch-design.md` を参照。

## 開発

```bash
uv run pytest tests/ -v          # バックエンド
cd frontend && npm run test      # フロントのロジックテスト
```

フロントエンドは React + Chakra UI v3。`cd frontend && npm run dev` で :5173 に起動、
`npm run build` で `src/annotorch/server/static` に出力する。
