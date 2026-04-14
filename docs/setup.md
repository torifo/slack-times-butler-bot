# times-Butler 用 Slack Bot 初期セットアップ手順書

## 1. このドキュメントの目的

このドキュメントは、**Slack Bot をまだ作ったことがない人向け**に、times-Butler を動かすための最低限のセットアップ手順をまとめたものである。

Discord Bot を作った経験がある前提で、Slack 特有の考え方や、管理画面のどこで何を設定するのかをできるだけ具体的に書く。

対象は、まず **個人用 Bot を private channel で検証し、その後 `PRIVATE_TIMES_CHANNEL` に入れる** という流れである。

---

## 2. 先に理解しておくと楽な考え方

Slack Bot は Discord Bot と似ている部分もあるが、最初に少しだけ発想の違いを理解しておくとハマりにくい。

### 2.1 Discord との大きな違い

#### Discord では

* Bot をサーバーに入れる
* イベントを受ける
* メッセージを返す
* 権限はロールや権限セットで考える

#### Slack では

* **Slack App** を作る
* その App に **Bot User** がいる
* 権限は **OAuth Scope** で与える
* イベントは **Event Subscriptions** で受ける
* Slash Command や Bot Mention も App にぶら下がる

つまり、Slack では「Bot を作る」というより、**Bot を内包した Slack App を作る** イメージに近い。

---

## 3. 全体フロー

初期セットアップは大きく分けると次の順番になる。

1. Slack App を作成する
2. Bot Token Scope を設定する
3. Event Subscriptions を有効化する
4. Slash Commands を作る
5. App をワークスペースにインストールする
6. Bot を対象チャンネルに招待する
7. ローカルサーバーを起動し、Slack からイベントを受ける
8. private channel で動作確認する
9. 問題なければ `PRIVATE_TIMES_CHANNEL` に入れる

---

## 4. 事前に用意するもの

* Slack ワークスペース管理画面にアクセスできること
* Bot を追加したいワークスペースの権限
* Python 3.11
* ngrok または VPS 上の公開URL
* JAPAN AI API Key
* `.env` で環境変数を管理できる準備

---

## 5. Slack App を作る

### 5.1 作成場所

Slack の App 管理画面を開く。

開く場所:

* Slack API の App 管理ページ
* `Your Apps`
* `Create New App`

### 5.2 作成方法

`Create New App` を押すと、通常は以下のような選択がある。

* From scratch
* From an app manifest

最初は **From scratch** でよい。

### 5.3 入力する内容

* App Name: `times-Butler` など
* Pick a workspace: 対象ワークスペース

作成すると、App の設定画面に入る。

---

## 6. まず最初に見る設定画面

Slack App 作成後、左側メニューにいろいろ並ぶ。
最初に触ることが多いのは以下。

* **Basic Information**
* **OAuth & Permissions**
* **Event Subscriptions**
* **Slash Commands**
* **App Home**
* **Socket Mode** または Request URL 系設定
* **Install App**

今回、最初に重点的に触るのは以下。

1. Basic Information
2. OAuth & Permissions
3. Event Subscriptions
4. Slash Commands
5. Install App

---

## 7. Basic Information で確認すること

### 7.1 どこを見るか

左メニューの **Basic Information**

### 7.2 主にやること

ここでは主に以下を確認する。

* App ID
* Client ID
* Client Secret
* Signing Secret

このうち、開発時にまず重要なのは:

* **Signing Secret**

これは Slack から来たリクエストが本物かを検証するために使う。

### 7.3 環境変数として保存するもの

最低限、次の値を `.env` に入れる想定。

```env
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=...
SLACK_APP_TOKEN=...
JAPAN_AI_API_KEY=...
SOURCE_CHANNEL=...
POST_TARGET_CHANNEL=...
```

この時点では `SLACK_BOT_TOKEN` と `SLACK_APP_TOKEN` はまだ未取得でもよい。

---

## 8. OAuth & Permissions を設定する

### 8.1 どこを見るか

左メニューの **OAuth & Permissions**

### 8.2 ここでやること

* Bot Token Scopes を設定する
* 必要なら User Token Scopes を見る
* インストール後に Bot Token を取得する

今回の基本は **Bot Token Scopes** の設定だけでよい。

### 8.3 Bot Token Scopes に追加するもの

今回の仕様上、最低限は次を設定する。

#### コア機能用

* `app_mentions:read`
* `channels:history`
* `chat:write`
* `commands`
* `links:read`
* `reactions:write`

#### 今後使う予定があるもの

* `assistant:write`
* `files:read`
* `files:write`
* `bookmarks:read`
* `bookmarks:write`
* `canvases:read`
* `canvases:write`
* `lists:read`
* `lists:write`
* `reminders:read`
* `reminders:write`
* `emoji:read`
* `incoming-webhook`

### 8.4 注意点

Scope を追加しただけでは有効にならない。
**App をワークスペースに再インストール**して初めて反映される。

これは Slack で最初にハマりやすいポイント。

---

## 9. App をインストールする

### 9.1 どこでやるか

通常は次のどちらか。

* 左メニューの **Install App**
* OAuth & Permissions 内の **Install to Workspace** ボタン

### 9.2 実行内容

* `Install to Workspace` を押す
* 権限確認画面が出る
* 許可する

### 9.3 取得できるもの

インストール後、`OAuth & Permissions` に戻ると **Bot User OAuth Token** が表示される。

これを `.env` の以下に入れる。

```env
SLACK_BOT_TOKEN=replace-with-bot-token
```

### 9.4 再インストールが必要なタイミング

以下を変えた時は再インストールを疑う。

* Scope を追加した
* 権限を変更した
* 一部の連携機能が効かない

---

## 10. Event Subscriptions を設定する

### 10.1 どこを見るか

左メニューの **Event Subscriptions**

### 10.2 何をする場所か

Slack からアプリへイベントを飛ばす設定を行う場所。

例:

* メッセージ投稿を受ける
* Bot Mention を受ける
* チャンネル参加イベントを受ける

### 10.3 最初に必要なもの

ここを有効化するには **Request URL** が必要になる。
つまり、**Slack から見える公開URL** が必要。

ローカル開発なら普通は以下のどちらか。

* ngrok
* VPS 上の一時デプロイ

### 10.4 Request URL の例

たとえば FastAPI + Slack Bolt で `/slack/events` を受けるなら、

```text
https://xxxx.ngrok-free.app/slack/events
```

のような URL を入れる。

Slack が challenge を送り、URL 検証が成功すると有効化できる。

### 10.5 Subscribe to bot events に追加するもの

最低限おすすめは以下。

* `app_mention`
* `member_joined_channel`
* `message.channels`

必要に応じて今後追加:

* `link_shared` 系のイベントを使う場合は関連設定も検討
* private channel を扱う場合は対象イベントの種類を見直す

### 10.6 注意点

`message.channels` は public channel 向け。
private channel を本格的に読む場合、イベントの種類や Bot が実際に参加しているかを確認すること。

また、**チャンネルに Bot が入っていないと履歴取得やイベント受信が期待通りにならない**ことがある。

---

## 11. Slash Commands を設定する

### 11.1 どこを見るか

左メニューの **Slash Commands**

### 11.2 何を設定するか

例えば次のようなコマンドを作る。

* `/times`

最初は 1 コマンドに集約して、サブコマンドで分岐するのが楽。

例:

* `/times digest today`
* `/times digest week`
* `/times search 稟議`
* `/times kidzuki`
* `/times level 2`

### 11.3 設定項目

新しく Slash Command を作ると、通常以下を入れる。

* Command: `/times`
* Request URL: `https://<公開URL>/slack/commands`
* Short Description: 何をするコマンドか
* Usage Hint: 使い方

### 11.4 最初のおすすめ

最初は `/times` だけ作り、引数を解釈して分岐させる。
そうすると管理が楽。

---

## 12. App Home は後で良いが見ておく

### 12.1 どこを見るか

左メニューの **App Home**

### 12.2 今回の位置づけ

v1 では必須ではないが、将来的に次の用途に使える。

* Bot の自己紹介
* コマンド一覧
* 使い方案内
* 個別設定の UI

新規参加者への個別案内の置き場としても候補になる。

---

## 13. Socket Mode を使うかどうか

### 13.1 どこを見るか

左メニューの **Socket Mode**

### 13.2 ざっくり違い

Slack Bot の受信方法は大きく次の2択がある。

#### A. HTTP Request URL 方式

* Slack から自分のサーバーに webhook で飛んでくる
* 公開 URL が必要
* FastAPI と相性が良い

#### B. Socket Mode

* Slack に対してアプリ側がソケット接続する
* 公開 URL が不要なケースもある
* `SLACK_APP_TOKEN` が必要

### 13.3 今回どちらが良いか

今回の構成だと、最終的に **VPS デプロイ予定**なので、
**HTTP Request URL 方式** を第一候補にしてよい。

ただし、最初にローカルだけで雑に動かしたい場合は Socket Mode も便利。

### 13.4 Socket Mode を使う場合

* Socket Mode を ON にする
* App-Level Token を作る
* 通常は `connections:write` 相当を持つ App Token を使う
* `.env` に `SLACK_APP_TOKEN` を入れる

```env
SLACK_APP_TOKEN=replace-with-app-token
```

### 13.5 どちらを採用するか

この Bot では、

* 本番: HTTP Request URL 方式
* 開発初期: 必要なら Socket Mode も可

という整理でよい。

---

## 14. Bot をチャンネルに入れる

### 14.1 やること

App を作っただけでは、対象チャンネルで何もできないことがある。
Bot をチャンネルに入れる必要がある。

Slack 上で対象チャンネルを開き、通常は以下のようにする。

```text
/invite @times-Butler
```

またはチャンネルのメンバー追加 UI から Bot を追加する。

### 14.2 今回のおすすめ運用

1. private channel を作る
2. そこに Bot を入れる
3. テストする
4. 問題なければ `PRIVATE_TIMES_CHANNEL` に Bot を入れる

### 14.3 注意点

* Bot がチャンネルにいないと `channels:history` でも見えないことがある
* private channel は特に Bot 参加が重要

---

## 15. private channel デバッグ運用

今回の要件では、最初に private channel で検証したい。
そのため、設定値で次を分ける前提にする。

```env
SOURCE_CHANNEL=C1234567890
POST_TARGET_CHANNEL=C1234567890
```

後から次のように変えられるようにする。

```env
SOURCE_CHANNEL=C_PRIVATE_TIMES_CHANNEL
POST_TARGET_CHANNEL=C_debug_private
```

または最終的に

```env
SOURCE_CHANNEL=C_PRIVATE_TIMES_CHANNEL
POST_TARGET_CHANNEL=C_PRIVATE_TIMES_CHANNEL
```

とする。

### 15.1 チャンネルIDの調べ方

Slack のチャンネルIDは URL や詳細画面で確認できる。
わからない場合はブラウザで Slack を開き、URL 内の `C...` や `G...` を見るとよい。

---

## 16. 最低限必要な環境変数

```env
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=...
SLACK_APP_TOKEN=...
JAPAN_AI_API_KEY=...
SOURCE_CHANNEL=...
POST_TARGET_CHANNEL=...
DAILY_DIGEST_CRON=30 18 * * *
WEEKLY_DIGEST_CRON=0 19 * * FRI
DEFAULT_EXPLANATION_LEVEL=2
DATABASE_PATH=data/times_butler.sqlite3
```

補足:

* `SLACK_APP_TOKEN` は Socket Mode を使わないなら不要な場合もある
* `DEFAULT_EXPLANATION_LEVEL` は URL 解説のわかりやすさ初期値

---

## 17. 最初に動かす最小構成

Slack Bot 初学者なら、いきなり全部作らず次の順で確認すると安全。

### Step 1

* App を作る
* Scope を追加する
* インストールする
* Bot を private channel に入れる

### Step 2

* `app_mention` を受ける
* `@times-Butler test` に返事できるようにする

### Step 3

* `/times` コマンドを作る
* `/times digest today` でダミー応答する

### Step 4

* `message.channels` を読めるようにする
* URL を含む投稿を検知する
* スレッド返信する

### Step 5

* SQLite に保存する
* 検索できるようにする

### Step 6

* digest ジョブを回す

この順番なら、問題が起きても原因の切り分けがしやすい。

---

## 18. Slack 側でハマりやすいポイント

### 18.1 Scope を足したのに動かない

原因候補:

* 再インストールしていない

対応:

* `Install to Workspace` をもう一度行う

### 18.2 イベントが来ない

原因候補:

* Request URL が外から見えない
* challenge 応答ができていない
* Bot が対象チャンネルに入っていない
* Event Subscriptions が OFF

### 18.3 Slash Command が来ない

原因候補:

* Request URL が間違っている
* コマンド設定保存後の反映待ち
* 署名検証失敗

### 18.4 private channel でうまく動かない

原因候補:

* Bot が channel に招待されていない
* イベント種別が想定と違う
* チャンネルIDの取り違え

### 18.5 Bot Token と Signing Secret を混同する

役割は別。

* `SLACK_BOT_TOKEN`: Slack API を呼ぶためのトークン
* `SLACK_SIGNING_SECRET`: Slack から来たリクエスト検証用

---

## 19. 最初に確認するべき Slack 側チェックリスト

### App 作成直後

* [ ] App が作成されている
* [ ] 対象ワークスペースが正しい

### OAuth & Permissions

* [ ] 必要 Scope を追加した
* [ ] Install to Workspace を実行した
* [ ] Bot User OAuth Token を取得した

### Event Subscriptions

* [ ] Enable を ON にした
* [ ] Request URL の challenge が通った
* [ ] `app_mention` を追加した
* [ ] `message.channels` を追加した
* [ ] `member_joined_channel` を追加した

### Slash Commands

* [ ] `/times` を作成した
* [ ] Request URL を設定した

### Slack 本体

* [ ] Bot を private channel に招待した
* [ ] 必要なら `PRIVATE_TIMES_CHANNEL` にも招待した

### ローカル / サーバー

* [ ] `.env` がある
* [ ] 公開 URL が有効
* [ ] FastAPI / Bolt が起動している

---

## 20. 初期実装のおすすめ進め方

Slack Bot が初めてなら、最初は **「Slack 側設定が正しいかを確認するだけの最小Bot」** を作るのがよい。

最初の成功条件はこれで十分。

* `@times-Butler test` と言うと返事が来る
* `/times` に返事が来る
* URL を貼るとスレッド返信される

ここまで通れば、あとは業務ロジックを積んでいける。

---

## 21. 今回の最小セットアップ結論

今回の times-Butler で最初に必要な Slack 側設定は次の通り。

### 必須設定

* App 作成
* OAuth & Permissions
* Bot Token Scopes 追加
* Install to Workspace
* Event Subscriptions 有効化
* `/times` Slash Command 作成
* Bot を private channel に招待

### 先に入れておくと良い設定

* `assistant:write`
* `canvases:read`
* `canvases:write`
* `bookmarks:read`
* `bookmarks:write`
* `files:read`
* `files:write`

### 本番前の推奨流れ

1. private channel で検証
2. URL スレッド返信を確認
3. digest の定期投稿を確認
4. 検索を確認
5. `PRIVATE_TIMES_CHANNEL` に移行

---

## 22. 次に作るべきもの

このドキュメントの次に用意すると良いのは以下。

1. **ローカル実行用の最小 Python テンプレート**
2. **`.env.example`**
3. **Slack Bolt + FastAPI の最小コード**
4. **SQLite の初期スキーマ**
5. **`/times` コマンドの最小実装**

この順で進めると、Slack 側設定とコード側設定を切り分けながら進めやすい。
