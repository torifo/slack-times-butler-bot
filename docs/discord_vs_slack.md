# Discord Bot と Slack Bot の違い

今回の `times-Butler` を理解するために、Discord Bot と Slack Bot の通信方式の差を整理する。

## 1. いちばん大きい違い

### Discord Bot

Discord Bot は、Bot 側から Discord に接続しに行く。

イメージ:

* Bot が Discord Gateway に WebSocket 接続する
* Discord のイベントをその接続上で受け取り続ける
* ローカルで起動していれば、その間は動く

つまり:

* Bot は「取りに行く側」
* 公開 URL は不要

### Slack Bot

Slack Bot には 2 方式あるが、今回の実装は HTTP 受信方式になっている。

HTTP 受信方式のイメージ:

* Slack が Bot の URL に HTTP POST を送る
* Bot はそれを受けるサーバーとして動く

つまり:

* Bot は「受ける側」
* Slack から到達できる公開 URL が必要

## 2. なぜ Slack で URL が必要なのか

今回のコードは `FastAPI` で次の endpoint を公開する前提になっている。

* `/slack/events`
* `/slack/commands/times`

Slack はこの URL にイベントや Slash Command を送る。
そのため、Slack から見える URL が必要になる。

ローカルの `127.0.0.1:8000` は自分の PC の中だけでしか見えないので、Slack からは届かない。

## 3. Slack の 2 つの方式

### 3.1 HTTP Request URL 方式

特徴:

* Slack がアプリへイベントを送る
* 公開 URL が必要
* FastAPI や Web サーバーと相性がよい

今回の `times-Butler` はこの方式。

必要になるもの:

* `https://.../slack/events`
* `https://.../slack/commands/times`

### 3.2 Socket Mode

特徴:

* アプリ側から Slack に接続する
* 公開 URL は不要
* Discord Bot に近い感覚で扱える

必要になるもの:

* `SLACK_APP_TOKEN`
* Socket Mode 用の受信実装

補足:

* 今の `times-Butler` には Socket Mode の受信実装は入っていない
* そのため、Socket Mode を使うならコード修正が必要

## 4. Discord と Slack の比較

### Discord

* Bot が Discord に接続する
* 起動中ならローカルでも動く
* 公開 URL は不要

### Slack HTTP 方式

* Slack が Bot に送る
* 起動しているだけでは足りず、公開 URL が必要
* ローカル確認だけならできるが、Slack 実機連携は公開 URL が必要

### Slack Socket Mode

* Bot が Slack に接続する
* Discord にかなり近い
* 公開 URL は不要

## 5. 今回の選択肢

### 選択肢 A: Socket Mode を使う

向いているケース:

* ローカル中心で早く試したい
* 公開 URL をまだ持ちたくない
* Discord Bot に近い感覚で開発したい

必要なこと:

* Socket Mode を有効化する
* `SLACK_APP_TOKEN` を発行する
* Socket Mode 受信コードを実装する

注意:

* 今のコードのままでは動かない

### 選択肢 B: 公開 URL 方式を使う

向いているケース:

* 最終的に VPS 常駐を前提にしている
* FastAPI ベースの HTTP 受信で運用したい
* 本番構成をそのまま育てたい

必要なこと:

* Slack から届く URL を用意する
* Event Subscriptions と Slash Command にその URL を設定する

## 6. `riumu.net` のような独自ドメインを持っている場合

はい、そのドメインを使う形でよい。

例えば次のような URL を VPS に向ければよい。

```text
https://riumu.net/slack/events
https://riumu.net/slack/commands/times
```

またはサブドメインを切ってもよい。

```text
https://bot.riumu.net/slack/events
https://bot.riumu.net/slack/commands/times
```

必要なのは:

* ドメインまたはサブドメインを VPS に向ける
* Web サーバーまたはリバースプロキシでアプリに流す
* Slack にその URL を設定する

1 つの受け口ドメインでパス分岐する形でもよい。

例:

```text
https://socket.slack-bot.riumu.net/times/slack/events
https://socket.slack-bot.riumu.net/times/slack/commands/times
```

## 7. 今回の結論

今回の `times-Butler` は今のコードのままなら **公開 URL 方式** が自然。

つまり:

* ローカル確認だけなら今のままで進められる
* Slack 実機確認をするなら `ngrok` か VPS の公開 URL が必要
* `riumu.net` のような独自ドメインを持っているなら、それを VPS に向けて使えばよい
* Socket Mode を使うなら、先にコードをその方式へ合わせて変更する必要がある
