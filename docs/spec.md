# times-Butler 仕様書（叩き台）

## 1. 概要

**times-Butler** は、Slack 上の個人 times チャンネル `PRIVATE_TIMES_CHANNEL` を対象に、投稿内容の整理・再利用・理解促進を支援する個人用 Bot である。

本 Bot の目的は、times に書かれた内容を単なるログで終わらせず、以下のような価値に変換することにある。

* 日々の気づきや学びの蓄積
* 投稿内容の振り返りと再検索
* URL 共有時の理解補助
* 定期ダイジェストによる知識の再整理
* 将来的な汎用 Bot 化のための実験基盤

初期ターゲットは**完全個人用**であり、対象チャンネルは **`PRIVATE_TIMES_CHANNEL` の1チャンネルのみ**とする。
将来的に他メンバーから要望があった場合は、本 Bot を横展開するのではなく、必要に応じて汎用化した新規 Bot をスクラッチで作る前提とする。

---

## 2. 開発方針

### 2.1 開発方針

* ベース実装は **Python** を採用する
* 実装は **Codex を使ったヴァイブコーディング** を主軸とする
* 深い要件整理や将来の複雑化が必要になった場合に限り Kiro の利用を検討する
* 今回は **MVP に寄りすぎず、将来拡張も見据えた設計仕様** を作る

### 2.2 実行 Python バージョン

* **Python 3.11**

理由:

* Slack Bolt for Python との相性が安定している
* 周辺ライブラリが十分こなれている
* 非同期やジョブ処理で扱いやすい
* 3.12 以上との差異を避けて実行環境を固定しやすい

---

## 3. 利用前提

### 3.1 利用対象

* 完全個人用
* チャンネル: `PRIVATE_TIMES_CHANNEL`

### 3.2 過去ログ

* 投稿開始からまだ 1 か月未満のため、**過去ログは全件取り込む**
* Bot 導入後の新規投稿だけでなく、既存の投稿も対象に含める

### 3.3 検証環境

初期検証は private channel 上で行う。
ただし、将来の運用を見据え、チャンネルの読み取り対象と投稿先を分離できる設計にする。

想定:

* `SOURCE_CHANNEL`: 取得対象チャンネル
* `POST_TARGET_CHANNEL`: Bot が投稿するチャンネル

これにより、以下のような運用を可能にする。

* private channel で挙動検証
* 問題なければ `PRIVATE_TIMES_CHANNEL` に切り替え
* 機能ごとに読み取り先 / 投稿先を切り替え

---

## 4. 利用可能スコープと活用方針

今回、Slack Bot は以下の強い権限を持つ。

### 4.1 主要スコープ

* `app_mentions:read`
* `assistant:write`
* `channels:history`
* `chat:write`
* `commands`
* `files:read`
* `files:write`
* `links:read`
* `links:write`
* `bookmarks:read`
* `bookmarks:write`
* `canvases:read`
* `canvases:write`
* `lists:read`
* `lists:write`
* `emoji:read`
* `reactions:write`
* `reminders:read`
* `reminders:write`
* `incoming-webhook`

### 4.2 初期利用方針

v1 では以下を主に使う。

* `channels:history`: 投稿取得
* `chat:write`: メッセージ / スレッド投稿
* `app_mentions:read`: メンション起点の呼び出し
* `commands`: slash command
* `links:read`: URL 抽出
* `reactions:write`: URL 投稿への誘導リアクション
* `assistant:write`: 将来的なアシスタント化への布石

v1.5 以降で活用を検討するもの:

* `canvases:write`
* `bookmarks:write`
* `files:read`
* `reminders:write`

---

## 5. Bot コンセプト

**times-Butler = times の投稿を「気づき資産」に変える Bot**

重要なのは、単なる雑談相手ではなく、次の役割を持たせることである。

* 投稿内容を整理する
* URL の理解を補助する
* 気づきやテーマを抽出する
* あとから再検索しやすくする
* 定期的に振り返らせる

---

## 6. MVP の中核機能

v1 では、以下を主機能とする。

### 6.1 定期ダイジェスト

#### daily digest

* 実行時刻: **毎日 18:30**
* 投稿先: チャンネル本体
* 基本は単発投稿
* 日ごとの投稿量に応じて内容量を調整する

#### weekly digest

* 実行時刻: **毎週金曜 19:00**
* 投稿先: チャンネル本体
* 基本は単発投稿

#### 方針

* 自動投稿は digest のみを対象とする
* 自動返信を乱発しない
* 日次 / 週次ともに、分量に応じて出力を可変化する

想定出力要素:

* 主なテーマ
* 気づき / 学び
* 繰り返し出ている話題
* アクション候補
* 共有 URL の概要

### 6.2 URL 投稿時の補助スレッド

本 Bot の重要機能。

#### 目的

Slack で URL を貼って終わるのではなく、
**その URL の概要をスレッドで補足し、確認を促すこと**を目的とする。

#### 挙動

* URL を含む投稿を検知する
* 元投稿にリアクションを付ける
* 元投稿に紐づくスレッドで概要を返す

#### 返信内容

* URL の要約
* 文脈に応じた補足説明
* 対象読者ラベル
* 誘導文

#### 対象読者ラベル

初期は表示ラベルを以下の3種類に限定する。

* `エンジニア向け`
* `ビジネス向け`
* `両方`

内部的には将来の拡張を見越して、より細かい分類を持てる構造にする。
例:

* 技術
* ビジネス
* 法務
* 業務改善
* 思考法
* マナー
* ツール紹介

ただし v1 のユーザー向け表示は 3 ラベルのみとする。

#### 誘導方法

* **元投稿にリアクションを付与**
* **詳細はスレッドで返答**

誘導スタイルは以下。

* 元投稿に軽い反応をつける
* スレッド冒頭で「概要をまとめた」ことを伝える
* 中身を確認したくなるように短く誘導する

#### 投稿タイミング

発火条件・投稿タイミング・解説段階については、現時点では厳密依存を置かない。
実装上は設定可能な構造にしておくが、仕様としては柔軟運用前提とする。

### 6.3 わかりやすさレベル調整

URL 補助スレッドでは、記事内容に応じて**説明のわかりやすさレベルを調整できる構造**を持たせる。

例として、JSONC に関する記事なら以下のような段階差を持てる。

* 短く端的な説明
* 少し噛み砕いた説明
* 初学者向けにかなり平易な説明

意図:

* 読み手の知識差を吸収する
* ただ要約するだけでなく、理解しやすくする
* URL の中身を確認するハードルを下げる

v1 では、3段階程度の説明レベルを持てる設計にする。
ただし、初期運用では固定レベルから開始してよい。

### 6.4 検索機能

#### 方針

検索は **LLM を使わない範囲で正確に取得する**。
多少時間がかかってもよく、曖昧な生成より検索精度を優先する。

#### 初期実装方針

* SQL ベースの検索
* `LIKE '%keyword%'` に近い部分一致検索
* AND / OR 条件に対応
* タグ絞り込み対応
* 日付絞り込み対応
* URL有無などの条件絞り込み対応

#### 検索結果の返し方

* 要約
* 元投稿リンク

LLM は検索候補抽出には使わず、必要なら将来、検索結果の見やすい再構成にのみ使う余地を残す。

### 6.5 kidzuki 抽出

#### 位置づけ

ユーザーの times の特色として、「気づき / kidzuki」の蓄積は中核テーマである。
そのため、Bot は kidzuki 抽出機能を持つ。

#### 判定方針

初期方針は **C: 二段階方式**

* 自動抽出は広めに拾う
* 人があとで確定 / 修正できるようにする

#### 判定方法

理想は LLM を使わずに一定精度で判定することだが、現時点では文脈理解が必要なため、**初期は LLM 利用を許容**する。
将来はルールベースやキーワード辞書の比重を上げる余地を残す。

#### 典型対象

* 新しい技術用語との遭遇
* 新しく知った概念
* 実務での発見
* 仕事の進め方に関する学び
* 自分なりの改善気づき

### 6.6 タグ付け / タグ修正

#### 方針

* Bot が自動でタグ付けする
* 人が修正できるようにする
* Bot 単独判定で無理に完璧を目指さない

#### 修正方法

メッセージを毎回指定する方式は手間が大きいため、
**対象メッセージのスレッド内でタグ修正指示を返せる方式**を推奨とする。

例:

* `tag: 技術, 業務改善`
* `tag: -技術, +法務`

これにより、

* 追加
* 削除
* 修正

をスレッド返信ベースで扱えるようにする。

#### 実装上の留意点

* スレッド親メッセージをタグ対象とみなす
* Bot 自身の返信とユーザー修正指示を区別する
* タグ修正権限は初期は本人のみでよい

---

## 7. v1 の自動アクション方針

### 7.1 基本方針

自動投稿は digest のみを基本とする。
不用意な自動返信は避け、ノイズ化を防ぐ。

### 7.2 条件付きアクション

ただし、将来拡張や一部導入を見据え、**特定条件下のアクション機構**は設計に含める。

### 7.3 新規参加者への挨拶機能

これは欲しい機能として扱い、**v1 簡易版（C）** として設計に含める。

要件:

* チャンネル上では、みんなに見える welcome メッセージを投稿できる
* Bot の説明や自己紹介は、新規参加者本人だけに送れるようにしたい
* 毎回全体に長い説明を流さないようにする

補足:

Slack の実装方式に応じて、以下の候補を比較する。

* チャンネル投稿 + DM
* チャンネル投稿 + App Home 的案内
* チャンネル投稿 + ephemeral 相当の個別案内

v1 では簡易版を視野に入れ、詳細実装は段階導入でもよい。

---

## 8. Canvas 方針

Canvas は魅力的な機能だが、見せ方にこだわりたい前提があるため、v1 の中核にはしない。
ただし、**簡易版導入を視野に入れる（B）**。

### 8.1 位置づけ

* v1 の主役ではない
* v1.5 的な拡張ポイント
* Slack 上の digest / URL 補助 / 検索が安定した後に厚くする

### 8.2 将来やりたいこと

* times のまとめを Canvas に蓄積
* スイムレーン形式で整理
* 螺旋レイアウトのような見せ方
* テーマ別ナレッジ整理

### 8.3 v1 での扱い

* Canvas に出しやすい構造化データを内部で持てるようにする
* ただし初期は必須機能にしない

---

## 9. LLM 利用方針（JAPAN AI API）

### 9.1 基本方針

JAPAN AI の API Key を chat 形式 LLM として利用できる前提で、Bot の要約・説明・分類に活用する。

### 9.2 コスト方針

* **ある程度抑えたい**
* 無制限に呼ばず、価値が高い箇所に絞る

### 9.3 LLM を使う処理

* URL 内容の要約
* URL 内容の噛み砕き説明
* URL の対象読者ラベル判定補助
* kidzuki 抽出補助
* daily / weekly digest 生成

### 9.4 LLM を使わない処理

* 通常検索
* 基本的なタグ管理
* メッセージ / スレッド対応づけ
* スケジュール実行
* ルールベースの軽い分類

### 9.5 利用最適化

* キャッシュを持つ
* URL 単位で再利用可能な要約結果を保持する
* 同一 URL の再要約を避ける
* digest 生成時は必要な投稿だけを渡す

---

## 10. データ保存方針

### 10.1 DB 選定

* **SQLite** を採用する

理由:

* 個人用で十分
* 構築が簡単
* ローカルや VPS で運用しやすい

### 10.2 保存範囲

**A: 投稿本文 + メタ情報 + タグ + 要約キャッシュ** を保存する。

保存対象例:

* message_ts
* thread_ts
* channel_id
* user_id
* text
* normalized_text
* permalink
* has_url
* extracted_urls
* created_at
* tags
* kidzuki_flag
* url_summary_cache
* digest_cache

### 10.3 保持期間

* **永続保存**

理由:

* データ量は大きくない想定
* 個人用であり、後から見返す価値が高い

---

## 11. 検索対象と将来拡張

### 11.1 v1 の検索対象

* `PRIVATE_TIMES_CHANNEL` のメッセージ
* スレッド情報
* 保存済みタグ
* 保存済み URL メタ情報

### 11.2 将来の拡張優先順

1. Slack 内の `files / links / bookmarks / canvas`
2. Notion
3. Google Workspace

v1 時点では、将来これらに拡張できるようサービス層を分離する。

---

## 12. 推奨アーキテクチャ

```text
Slack Event / Slash Command
    ↓
Slack Bolt Handler
    ↓
UseCase / Service Layer
    ├─ HistoryService
    ├─ DigestService
    ├─ UrlSummaryService
    ├─ TagService
    ├─ SearchService
    ├─ KidzukiService
    ├─ ReactionService
    ├─ WelcomeService
    └─ LlmService
    ↓
Repository Layer
    ├─ MessageRepository
    ├─ UrlSummaryRepository
    ├─ TagRepository
    ├─ DigestRepository
    └─ SettingsRepository
    ↓
SQLite
```

---

## 13. 推奨技術スタック

### 13.1 必須

* Python 3.11
* Slack Bolt for Python
* FastAPI
* uvicorn
* SQLite
* JAPAN AI API client（独自ラッパー）

### 13.2 補助

* APScheduler
* SQLAlchemy または sqlite3
* pydantic
* requests / httpx

### 13.3 デプロイ

静的ホスティングは不適。
GitHub Pages は対象外。
Cloudflare 系はサブリクエスト制約などで相性に懸念がある。

現状の有力候補:

* **VPS へデプロイ**

開発初期はローカル + ngrok でもよいが、本命は VPS 想定とする。

---

## 14. ディレクトリ構成案

```text
times_butler/
├─ app.py
├─ settings.py
├─ routes/
│  ├─ events.py
│  ├─ commands.py
│  └─ health.py
├─ handlers/
│  ├─ mention_handler.py
│  ├─ digest_handler.py
│  ├─ url_handler.py
│  ├─ search_handler.py
│  ├─ tag_handler.py
│  └─ welcome_handler.py
├─ services/
│  ├─ slack_service.py
│  ├─ history_service.py
│  ├─ digest_service.py
│  ├─ url_summary_service.py
│  ├─ tag_service.py
│  ├─ search_service.py
│  ├─ kidzuki_service.py
│  ├─ reaction_service.py
│  ├─ welcome_service.py
│  └─ llm_service.py
├─ repositories/
│  ├─ message_repository.py
│  ├─ digest_repository.py
│  ├─ url_summary_repository.py
│  ├─ tag_repository.py
│  └─ settings_repository.py
├─ prompts/
│  ├─ summarize_url.md
│  ├─ digest_daily.md
│  ├─ digest_weekly.md
│  ├─ extract_kidzuki.md
│  └─ classify_audience.md
├─ jobs/
│  ├─ daily_digest_job.py
│  └─ weekly_digest_job.py
├─ models/
│  ├─ message.py
│  ├─ tag.py
│  ├─ digest.py
│  └─ url_summary.py
└─ tests/
```

---

## 15. 主な機能仕様詳細

### 15.1 メンション機能

例:

* `@times_support 今日のtimesを要約`
* `@times_support 今週の気づきは？`
* `@times_support 稟議の話を出して`

v1 では補助的機能とし、主役は digest / URL 補助 / 検索とする。

### 15.2 Slash Command 候補

* `/times digest today`
* `/times digest week`
* `/times search <keyword>`
* `/times kidzuki`
* `/times tags`
* `/times level <1|2|3>`

### 15.3 URL 補助スレッドの出力例

* 冒頭: ラベルと短い導入
* 要点 2〜4 点
* 必要なら用語のやさしい説明
* この投稿を見る価値の一言

### 15.4 検索結果出力例

* 該当件数
* 上位数件の要約
* 元投稿リンク
* 日付
* 付与タグ

---

## 16. リアクション方針

v1 では、URL 投稿への誘導のための軽いリアクション付与を対象とする。

一方、投稿内容評価のような高度なリアクション自動付与は、
学習データ不足のため v2 以降の準備事項とする。

方針:

* 今ある投稿 / リアクションの傾向は分析しておく
* 十分な学習データが貯まったら v2 で活用する

---

## 17. 非機能要件

### 17.1 保守性

* Slack I/O と業務ロジックを分離する
* LLM 呼び出しを一箇所に集約する
* DB アクセスを repository に分離する

### 17.2 コスト管理

* URL 要約はキャッシュする
* digest は必要最小限のテキストを渡す
* 検索では LLM を使わない

### 17.3 テスト容易性

* private channel で機能ごとの検証ができる
* channel source / post target を分離する
* URL 処理やタグ処理はサービス単位でテスト可能にする

---

## 18. 今回やらないこと

* 全社向けの権限設計
* 複数チャンネル横断の本格分析
* ベクトル検索
* 感情分析
* 高度な個人レコメンド
* Canvas を主役にした UI 設計
* リアクション学習ベースの自動判定

---

## 19. 今回の実装優先順位

### Phase 1

* 過去ログ全件取り込み
* DB 保存
* daily digest
* weekly digest
* URL 投稿補助スレッド
* 基本タグ付け
* 検索

### Phase 2

* kidzuki 抽出の精度改善
* タグ修正のスレッド操作
* URL ラベル判定改善
* Welcome 機能簡易版

### Phase 3

* Canvas 簡易出力
* bookmark / files 連携
* Notion 連携検討
* Google Workspace 連携検討

---

## 20. 最終方針まとめ

本 Bot は、まずは `PRIVATE_TIMES_CHANNEL` 向けの**個人専用ナレッジ補助 Bot**として立ち上げる。

中核価値は以下の3点に置く。

1. **定期的な振り返りを可能にすること**
2. **URL共有の理解ハードルを下げること**
3. **times の内容を後から再利用しやすくすること**

初期は Slack 内で完結する構成とし、
将来的に files / bookmarks / canvas / Notion / Google Workspace へ拡張できるよう土台だけ残す。

設計としては、**個人用 MVP を素早く作れる現実性**と、**将来の整理された拡張性**の両立を目指す。
