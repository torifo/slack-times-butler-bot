# times-Butler デバッグ状況メモ

`docs/debug_checklist.md` に沿って、ローカルで確認できる範囲を実施した結果をまとめる。

確認日: 2026-04-15

## 1. 起動確認

結果:

* OK

確認内容:

* `127.0.0.1:8000` で `python3.11` の待受を確認
* `GET /health` が `{"status":"ok"}` を返した

補足:

* Bot プロセス自体は起動している
* 「起動していない」は現在の主因ではない

## 2. Python バージョン確認

結果:

* 部分的に注意あり

確認内容:

* `python --version` は `Python 3.11.11`
* `python3 --version` は `Python 3.13.7`
* `.python-version` は `3.11.11`

意味:

* `python` は 3.11 を向いている
* ただし `python3` は 3.13 のままなので、コマンドによって実行系がずれる

## 3. 環境変数確認

結果:

* OK

確認できた項目:

* `SLACK_BOT_TOKEN`
* `SLACK_SIGNING_SECRET`
* `SOURCE_CHANNEL`
* `POST_TARGET_CHANNEL`
* `JAPAN_AI_API_KEY`

補足:

* 値の中身は秘匿したまま、設定済みであることだけ確認した

## 4. ローカル HTTP ルーティング確認

結果:

* OK

確認内容:

* `POST /slack/events` に `url_verification` を送ると `challenge` を返した
* `POST /slack/commands/times` に `digest today` を送ると応答した

確認結果の意味:

* FastAPI のルーティング自体は動いている
* Slack から適切に到達すれば、少なくとも endpoint は受けられる

## 5. Digest 動作確認

結果:

* 応答はするがデータなし

確認内容:

* `/slack/commands/times` に `digest today` を送ると応答は返る
* ただし内容は `投稿 0 件` だった

意味:

* digest 機能の入口は動いている
* ただし DB に材料が入っていない

## 6. DB 状況確認

結果:

* 初期テーブルはあるが、メッセージデータは空

確認内容:

* テーブル:
  * `messages`
  * `tags`
  * `url_summaries`
  * `digests`
* `messages` 件数は `0`

意味:

* Slack メッセージがまだ保存されていない
* 検索や digest が期待どおりに動かない主因の一つ

## 7. ここまでで確定したこと

1. Bot サーバー自体は起動している
2. ローカル endpoint は受信できる
3. 環境変数の基本項目は入っている
4. DB に Slack メッセージが 1 件も入っていない

## 8. 次に疑うべき点

優先度順:

1. Slack の Event Subscriptions が Bot に到達していない
2. private channel 用の scope またはイベント種別が不足している
3. 履歴同期導線が未接続なので、過去ログが入っていない

## 9. 実装上の現時点の制約

### 9.1 履歴同期が自動で走らない

`HistoryService.sync_history()` はあるが、起動時や command から呼ばれていない。

影響:

* 過去ログは DB に入らない
* digest と検索の材料が増えない

### 9.2 app mention は未接続

`app_mention` event の処理がまだ `routes/events.py` に入っていない。

影響:

* mention しても反応しない可能性が高い

## 10. 現時点の結論

ローカル起動は通っている。
今の主な問題は「Slack 側からイベントが本当に届いているか」と「届いたメッセージを DB にためる導線が不足しているか」の切り分けに移っている。
