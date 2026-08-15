.PHONY: help build up down logs shell setup serve dev front-build test test-front lint check clean

help:
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t 16

build: ## Docker イメージをビルド
	docker compose build

up: ## コンテナを起動（http://localhost:8000）
	docker compose up

down: ## コンテナを停止
	docker compose down

logs: ## コンテナのログを追う
	docker compose logs -f

shell: ## 起動中のコンテナでシェルを開く
	docker compose exec annotorch bash

setup: ## ローカル開発の依存を入れる
	uv sync --extra server
	cd frontend && npm install

serve: front-build ## ローカルでサーバを起動（http://localhost:8000）
	uv run annotorch serve

dev: ## フロントを HMR で起動（http://localhost:5173、要 make serve）
	cd frontend && npm run dev

front-build: ## フロントをビルド
	cd frontend && npm run build

test: ## バックエンドのテスト
	uv run pytest tests/ -q

test-front: ## フロントのテスト
	cd frontend && npm run test

lint: ## フロントの lint
	cd frontend && npm run lint

check: test test-front lint ## テストと lint をまとめて実行

clean: ## ビルド成果物を削除
	rm -rf src/annotorch/server/static
