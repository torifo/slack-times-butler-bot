# Public-Friendly Setup Flow

このリポジトリは将来的な public 化を前提に、公開して困る実データをコミットしない構成にしている。
実値はすべてローカルの `.env` にのみ保持し、Git には `.env.example` のプレースホルダだけを置く。

## 1. 実データとしてローカル管理するもの

* `SLACK_SIGNING_SECRET`
* `SLACK_BOT_TOKEN`
* `SLACK_APP_TOKEN`
* `JAPAN_AI_API_KEY`
* `SOURCE_CHANNEL`
* `POST_TARGET_CHANNEL`

## 2. 値の設定フロー

1. `.env.example` をコピーして `.env` を作る
2. Slack App 管理画面で `Signing Secret` と `Bot User OAuth Token` を取得する
3. `SOURCE_CHANNEL` には監視対象 channel の **ID** を入れる
4. `POST_TARGET_CHANNEL` には digest 投稿先 channel の **ID** を入れる
5. JAPAN AI の管理画面で API Key と Base URL を確認する
6. `.env` に実値を設定し、`git status` に `.env` や `data/` が出ないことを確認する

## 3. channel ID の取り方

実 channel 名そのものは public リポジトリへ残さず、ID のみをローカル設定に閉じる。

1. Slack で対象 channel を開く
2. channel 詳細または URL から `C` で始まる ID を確認する
3. `.env` に設定する

## 4. JAPAN AI 実データが未確定な場合

API の endpoint や payload 形式が未確定なら、次の順で埋める。

1. ベンダー管理画面または公式仕様から base URL を確認する
2. chat completion 相当の endpoint 名を確認する
3. request body の必須項目を確認する
4. `settings.py` の `JAPAN_AI_BASE_URL` と `services/llm_service.py` の request payload を更新する
5. 実接続テスト後にレスポンスの JSON パース項目を確定する

## 5. public 化前の確認項目

* `.env` が未追跡であること
* `data/` に実運用ログが残っていても Git 管理外であること
* docs に private な channel 名や user 名を残していないこと
* スクリーンショットやサンプルレスポンスに token が含まれていないこと
