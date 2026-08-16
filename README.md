# times-Butler

<!-- tech-stack:start (auto-generated) -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
</p>
<!-- tech-stack:end -->

Slack の times チャンネルに投稿した内容を「気づき資産」に変える、個人用ナレッジ補助 Bot。

---

## 概要

**times-Butler** は、Slack 上の個人 times チャンネルを対象に、投稿内容の整理・再利用・理解促進を支援する Bot です。

- 日々の気づきや学びをその場で終わらせず、蓄積・振り返りできる形に変換する
- URL を貼るだけで内容の概要をスレッドに返してくれる
- 毎日・毎週の自動ダイジェストで、書いたことを定期的に再整理できる

初期ターゲットは **完全個人用（1チャンネル）** です。

---

## 主要機能

| 機能 | 説明 |
|------|------|
| 日次ダイジェスト | 平日 18:30 に当日の投稿をまとめて自動投稿 |
| 週次ダイジェスト | 毎週金曜 19:00 に週全体の振り返りを自動投稿 |
| URL 補助スレッド | URL を含む投稿を検知し、要約・対象読者ラベル・解説をスレッドで返信 |
| 気づき（kidzuki）抽出 | 技術的発見・実務の学び・改善気づきを LLM で自動抽出 |
| タグ管理 | Bot が自動タグ付け。スレッド内で `tag: 技術, 業務改善` のように修正可能 |
| キーワード検索 | `/times search <キーワード>` で過去投稿を SQL ベースで検索 |
| ウェルカムメッセージ | チャンネルに新規参加したメンバーへの案内を自動送信 |

### URL 補助スレッドの対象読者ラベル

URL の内容に応じて以下のラベルを付与します。

- `エンジニア向け`
- `ビジネス向け`
- `両方`

---

## 技術スタック

| カテゴリ | 採用技術 |
|----------|----------|
| 言語 | Python 3.11 |
| Web フレームワーク | FastAPI + uvicorn |
| Slack SDK | Slack Bolt for Python |
| スケジューラ | APScheduler |
| DB | SQLite |
| LLM | llm-gateway 経由の Claude（既定）／ JAPAN AI API（フォールバック） |

### LLM バックエンド

`LLM_BACKEND` で切り替えます。

| 値 | 動作 |
|----|------|
| `claude_gateway` | 同一ホストの llm-gateway（`127.0.0.1`）へ要求し、失敗時は JAPAN AI → ルールベース要約へ段階的にフォールバック |
| `japan_ai`（既定） | 従来どおり JAPAN AI のみ。失敗時はルールベース要約 |

llm-gateway は Claude のサブスクリプション枠で動くローカル API で、このリポジトリには含まれません。
未起動・未設定でも JAPAN AI 側で動作は継続します。

---

## ディレクトリ構成

```
times_butler/
├── app.py               # アプリケーションエントリポイント
├── settings.py          # 設定管理（pydantic-settings）
├── dependencies.py      # DI ヘルパー
├── routes/              # FastAPI ルーター
│   ├── events.py        # Slack イベント受信
│   ├── commands.py      # Slash Command 受信
│   └── health.py        # ヘルスチェック
├── handlers/            # Slack イベント・コマンドのハンドラー
├── services/            # ビジネスロジック
├── repositories/        # DB アクセス層（SQLite）
├── models/              # データモデル
├── jobs/                # スケジュールジョブ（日次・週次 digest）
├── prompts/             # LLM プロンプト（Markdown）
├── deploy/              # デプロイ設定サンプル（nginx / systemd）
├── docs/                # セットアップ手順・仕様書
└── tests/               # テスト
```

---

## セットアップ

### 前提条件

- Python 3.11
- Slack ワークスペースの管理権限（App 作成・インストール）
- JAPAN AI API Key

### 1. リポジトリをクローンして依存関係をインストール

```bash
git clone <repository-url>
cd times_butler
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 環境変数を設定

`.env.example` をコピーして各値を入力します。

```bash
cp .env.example .env
```

**Slack**

| 変数名 | 説明 |
|--------|------|
| `SLACK_SIGNING_SECRET` | Slack App の Signing Secret |
| `SLACK_BOT_TOKEN` | Bot User OAuth Token（`xoxb-...`） |
| `SLACK_APP_TOKEN` | App-Level Token（Socket Mode 使用時、`xapp-...`） |

**チャンネル**

| 変数名 | 説明 |
|--------|------|
| `SOURCE_CHANNEL` | 読み取り対象チャンネルの ID |
| `SOURCE_CHANNEL_NAME` | ダイジェスト見出しに表示するチャンネル名（未設定なら ID を表示） |
| `POST_TARGET_CHANNEL` | Bot が投稿するチャンネルの ID |
| `WEEKLY_SUMMARY_CANVAS_ID` | 週次サマリーを書き込む Canvas の ID（不要なら空） |

**LLM（llm-gateway）**

| 変数名 | 説明 |
|--------|------|
| `LLM_BACKEND` | `claude_gateway` または `japan_ai`（デフォルト: `japan_ai`） |
| `LLM_GATEWAY_URL` | llm-gateway のベース URL（デフォルト: `http://127.0.0.1:8100`） |
| `LLM_GATEWAY_URL_BACKUP` | 本命ポートが塞がっていた場合の接続先（デフォルト: `http://127.0.0.1:8101`） |
| `LLM_GATEWAY_TIMEOUT_SECONDS` | llm-gateway の応答待ち秒数（デフォルト: `180.0`） |

**LLM（JAPAN AI）**

| 変数名 | 説明 |
|--------|------|
| `JAPAN_AI_API_KEY` | JAPAN AI の API Key |
| `JAPAN_AI_BASE_URL` | JAPAN AI の Base URL |
| `JAPAN_AI_MODEL` | 使用するモデル名（例: `gpt-4o`） |
| `JAPAN_AI_USER_ID` | リクエストに付与するユーザー ID |
| `JAPAN_AI_CHAT_ENDPOINT` | チャット API のパス（デフォルト: `/chat/v2`） |
| `JAPAN_AI_TEMPERATURE` | 生成温度（デフォルト: `0.1`） |
| `JAPAN_AI_ARTIFACT_IDS` | RAG 使用時の Artifact ID（不要なら空） |
| `REQUEST_TIMEOUT_SECONDS` | JAPAN AI の応答待ち秒数（デフォルト: `20.0`） |

**動作設定**

| 変数名 | 説明 |
|--------|------|
| `DATABASE_PATH` | SQLite ファイルのパス（デフォルト: `data/times_butler.sqlite3`） |
| `DAILY_DIGEST_CRON` | 日次ダイジェストの実行時刻（cron 形式、デフォルト: `30 18 * * *`） |
| `WEEKLY_DIGEST_CRON` | 週次ダイジェストの実行時刻（cron 形式、デフォルト: `0 19 * * FRI`） |
| `DEFAULT_EXPLANATION_LEVEL` | URL 解説のわかりやすさレベル（1〜3、デフォルト: `2`） |
| `URL_REACTION_NAME` | URL 投稿へのリアクション絵文字名（デフォルト: `eyes`） |

### 3. 起動

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

> Slack App の設定（OAuth Scope・Event Subscriptions・Slash Commands）の詳細手順は [docs/setup.md](docs/setup.md) を参照してください。

---

## Slash Commands

`/times` コマンドにサブコマンドを組み合わせて使います。

| コマンド | 説明 |
|----------|------|
| `/times digest today` | 当日のダイジェストを手動実行 |
| `/times digest week` | 今週のダイジェストを手動実行 |
| `/times search <キーワード>` | 過去投稿をキーワード検索 |
| `/times kidzuki` | 気づき一覧を表示 |
| `/times tags` | タグ一覧を表示 |
| `/times level <1\|2\|3>` | URL 解説のわかりやすさレベルを変更 |

---

## デプロイ

VPS へのデプロイを想定しています。`deploy/` 配下に設定例があります。

- `deploy/nginx/` — リバースプロキシ設定サンプル
- `deploy/systemd/` — systemd サービスユニットサンプル

詳細は [docs/deploy_socket_slack_bot_riumu.md](docs/deploy_socket_slack_bot_riumu.md) を参照してください。
