# times-Butler デバッグチェックリスト

private channel に Bot を招待したのに機能していない場合の確認順を、現状実装に合わせて整理する。

## 1. 最初に切り分けること

まず、次の 3 系統のどこで止まっているかを分ける。

1. サーバーが起動していない
2. Slack からイベントやコマンドが届いていない
3. 届いているが、アプリ内ロジックが動いていない

## 2. 起動確認

### 2.1 FastAPI が起動しているか

この Bot は HTTP の Request URL 方式が前提。
そのため、ローカルまたはサーバーで FastAPI が起動していないと何も起きない。

確認項目:

* `uvicorn app:app --reload` などでアプリが起動しているか
* `/health` にアクセスして `{"status":"ok"}` が返るか

期待値:

* `GET /health` が成功する

## 3. 環境変数確認

### 3.1 最低限必要な値

確認項目:

* `SLACK_BOT_TOKEN`
* `SLACK_SIGNING_SECRET`
* `SOURCE_CHANNEL`
* `POST_TARGET_CHANNEL`

補足:

* 現状コードは HTTP 受信前提なので `SLACK_APP_TOKEN` は未使用
* `SOURCE_CHANNEL` と `POST_TARGET_CHANNEL` が空でも一部イベントは受かるが、運用上は設定しておく方がよい

### 3.2 Python バージョン

確認項目:

* `python --version`
* `python3 --version`
* `.python-version`

期待値:

* `Python 3.11.x`

## 4. Slack 側の到達確認

### 4.1 Event Subscriptions の Request URL が通っているか

確認項目:

* `Event Subscriptions` が ON
* Request URL が `Verified` になっている
* `/slack/events` に向いている

補足:

* ここが通っていないと URL 投稿補助も welcome も動かない

### 4.2 Slash Command の Request URL が通っているか

確認項目:

* `/times` が設定済み
* Request URL が `/slack/commands/times` に向いている

補足:

* `routes/commands.py` の実装は `/slack/commands/times`
* `/slack/commands` ではない

## 5. private channel で特に疑う点

### 5.1 scope が private channel に足りていない

現状の仕様書は `channels:history` を中心に書いているが、private channel を読むにはそれだけでは足りない可能性が高い。

優先確認:

* private channel 向けの閲覧 scope があるか
* Bot が private channel のイベントを受け取れる設定になっているか

今回まず疑うべき点:

* `channels:history` だけで済む前提になっている
* private channel 用の scope が不足している

### 5.2 イベント種別が public channel 前提になっている

`docs/setup.md` でも触れている通り、`message.channels` は public channel 向け。
private channel で URL 投稿を拾いたいなら、private channel 側のイベント種別を確認する必要がある。

確認項目:

* `message.channels` だけを購読していないか
* private channel 向けイベントを購読すべき状態ではないか

## 6. 現状実装で動く機能と前提

### 6.1 URL 投稿補助

動作条件:

* Slack の `message` event が `/slack/events` に届く
* 投稿本文に URL が含まれる
* Bot Token でリアクション追加とスレッド投稿ができる

確認方法:

1. private channel に URL 付きメッセージを投稿する
2. サーバーログに `/slack/events` の受信があるか確認する
3. リアクションが付くか確認する
4. スレッド返信が付くか確認する

止まりやすい箇所:

* Event が届いていない
* private channel 用権限が不足している
* Bot がその channel で投稿権限を持っていない

### 6.2 Welcome

動作条件:

* `member_joined_channel` event が届く

確認方法:

* Bot ではなく別ユーザーを channel に入れて event が飛ぶか確認する

補足:

* 既存参加者がいるだけでは発火しない

### 6.3 Slash Command

動作条件:

* `/times` が Slack 側で設定済み
* Request URL が `/slack/commands/times`

確認方法:

* `/times digest today`
* `/times digest week`
* `/times search test`

止まりやすい箇所:

* Request URL のパス違い
* Slash Command 未作成
* Workspace 側で command 利用が止められている

### 6.4 Digest

動作条件:

* アプリ起動時に scheduler が動いている
* `POST_TARGET_CHANNEL` が設定されている
* DB に digest 対象メッセージがある

重要:

* 現状実装には `HistoryService.sync_history()` を自動実行する導線がまだない
* そのため、過去ログ取り込みをしていなければ digest の材料が空の可能性が高い

つまり:

* 「何も投稿されない」だけでなく
* 「投稿されても中身が薄い」ことが起こりうる

## 7. 実装上の注意点

### 7.1 app mention は未接続

`handlers/mention_handler.py` は存在するが、現状の `routes/events.py` では `app_mention` event を処理していない。

つまり:

* `@times-butler` と mention しても、今のコードでは反応しない可能性が高い

### 7.2 履歴同期は未接続

`services/history_service.py` はあるが、起動時やコマンド経由で同期する入口がまだない。

つまり:

* 検索
* digest

は、DB にメッセージが入っていないと期待どおりに動かない。

### 7.3 署名検証は未実装

現状の `/slack/events` と `/slack/commands/times` は、Slack 署名検証をまだ入れていない。

今すぐの不具合原因ではないが、公開運用前には実装が必要。

## 8. 今日の確認順

1. FastAPI が起動していて `/health` が通るか確認する
2. `.env` に `SLACK_BOT_TOKEN` などが入っているか確認する
3. Slack の Event Subscriptions が `Verified` か確認する
4. private channel 用の scope と event 種別が足りているか確認する
5. `/times` command の URL が `/slack/commands/times` になっているか確認する
6. private channel に URL を貼って、イベント到達の有無をサーバーログで見る
7. DB にメッセージが入っているか確認する

## 9. いま最有力の仮説

現状で最も疑わしいのは次の 3 点。

1. private channel 向け権限またはイベント購読が不足している
2. FastAPI は起動していても Slack の Request URL 設定が未完了
3. DB への履歴取り込み導線が未接続なので、検索や digest はまだ実質動かない
