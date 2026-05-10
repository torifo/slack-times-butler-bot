# times-Butler

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
| LLM | JAPAN AI API（OpenAI 互換） |

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

| 変数名 | 説明 |
|--------|------|
| `SLACK_SIGNING_SECRET` | Slack App の Signing Secret |
| `SLACK_BOT_TOKEN` | Bot User OAuth Token（`xoxb-...`） |
| `SLACK_APP_TOKEN` | App-Level Token（Socket Mode 使用時、`xapp-...`） |
| `JAPAN_AI_API_KEY` | JAPAN AI の API Key |
| `JAPAN_AI_BASE_URL` | JAPAN AI の Base URL |
| `JAPAN_AI_MODEL` | 使用するモデル名（例: `gpt-4o`） |
| `JAPAN_AI_ARTIFACT_IDS` | RAG 使用時の Artifact ID（不要なら空） |
| `SOURCE_CHANNEL` | 読み取り対象チャンネルの ID |
| `POST_TARGET_CHANNEL` | Bot が投稿するチャンネルの ID |
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
