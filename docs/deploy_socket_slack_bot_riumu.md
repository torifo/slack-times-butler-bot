# socket.slack-bot.riumu.net 配備メモ

`times-Butler` を `socket.slack-bot.riumu.net` 配下で運用する前提の、公開して問題ない設定メモ。

## 1. 今回の前提

このプロジェクトは Socket Mode ではなく、HTTP Request URL 方式で運用する。

そのため Slack に設定する URL は次のとおり。

* Event Subscriptions:
  `https://socket.slack-bot.riumu.net/times/slack/events`
* Slash Command `/times`:
  `https://socket.slack-bot.riumu.net/times/slack/commands/times`

## 2. パス設計

受け口ドメインは 1 つにまとめ、Bot ごとに prefix を分ける。

今回の `times-Butler` は:

* `/times/`

将来の別 Bot の例:

* `/opus/`
* `/notify/`

## 3. アプリ側のパス

`times-Butler` の FastAPI 側パスは次で固定。

* `/slack/events`
* `/slack/commands/times`
* `/health`

そのため reverse proxy 側で `/times/` prefix を剥がしてアプリへ流す。

例:

* 外向き:
  `https://socket.slack-bot.riumu.net/times/slack/events`
* アプリ内:
  `http://127.0.0.1:8000/slack/events`

## 4. DNS

必要なこと:

* `socket.slack-bot.riumu.net` を VPS に向ける
* IPv4 なら `A` レコード
* IPv6 を使うなら `AAAA` も設定

## 5. VPS 構成

役割分担:

* Nginx または Caddy が `socket.slack-bot.riumu.net` を受ける
* `times-Butler` は `127.0.0.1:8000` で待受
* systemd で常駐

サンプル:

* Nginx:
  [deploy/nginx/socket.slack-bot.riumu.net.conf.example](../deploy/nginx/socket.slack-bot.riumu.net.conf.example)
* systemd:
  [deploy/systemd/times-butler.service.example](../deploy/systemd/times-butler.service.example)

## 6. Slack 側で必要な設定

### 6.1 Socket Mode

* `OFF`

### 6.2 Event Subscriptions

* `ON`
* Request URL:
  `https://socket.slack-bot.riumu.net/times/slack/events`

### 6.3 Subscribe to bot events

private channel 検証を前提に、まず見直す候補:

* `member_joined_channel`
* private channel 用の message event

### 6.4 Slash Commands

* `/times`
* Request URL:
  `https://socket.slack-bot.riumu.net/times/slack/commands/times`

## 7. まず入れる scope の方針

最初は最小構成に絞る方が切り分けしやすい。

候補:

* `chat:write`
* `commands`
* `links:read`
* `reactions:write`
* `app_mentions:read`
* 対象 channel 種別に応じた history / message 関連 scope

## 8. `.env` で持つべきもの

最低限:

```env
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=...
JAPAN_AI_API_KEY=...
SOURCE_CHANNEL=...
POST_TARGET_CHANNEL=...
DATABASE_PATH=data/times_butler.sqlite3
```

補足:

* `SLACK_APP_TOKEN` は現構成では不要
* `PUBLIC_BASE_URL` のような環境変数は現実装では不要

## 9. ローカルと本番の違い

ローカル:

* `uvicorn app:app --host 127.0.0.1 --port 8000`
* Slack 実機疎通はできない

本番:

* same app を systemd で常駐
* reverse proxy 経由で Slack から到達可能

## 10. 今回の結論

今回の `socket.slack-bot.riumu.net` 方針では、アプリ側の大きな設計変更は不要。
必要なのは次の 3 点。

1. DNS を VPS に向ける
2. reverse proxy で `/times/` を `127.0.0.1:8000/` へ流す
3. Slack に `https://socket.slack-bot.riumu.net/times/...` を設定する
