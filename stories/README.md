# Comic Agent ストーリーディレクトリ

このディレクトリには、Comic Agentによって生成されたストーリーが保存されます。

## ディレクトリ構造

- `/stories`: ストーリーのルートディレクトリ
  - `/[genre]`: ジャンルごとのサブディレクトリ
    - `story_[timestamp].json`: 生成されたストーリーのJSON形式のデータ
    - `story_[timestamp].txt`: 生成されたストーリーのテキスト形式の出力

## ファイル形式

### JSON形式 (story_[timestamp].json)

```json
{
  "title": "ストーリーのタイトル",
  "characters": [
    {
      "name": "キャラクター名",
      "role": "役割（protagonist/support/antagonist等）",
      "description": "キャラクターの説明"
    }
  ],
  "plot": {
    "setup": "導入部の説明",
    "conflict": "展開部の説明",
    "resolution": "結末部の説明"
  },
  "themes": [
    "テーマ1",
    "テーマ2"
  ],
  "genre": "ジャンル",
  "metadata": {
    "agent_version": "エージェントのバージョン",
    "config": "使用された設定ファイルのパス",
    "timestamp": "生成日時"
  }
}
```

### テキスト形式 (story_[timestamp].txt)

生成されたストーリーの読みやすいテキスト形式での出力が含まれます。
