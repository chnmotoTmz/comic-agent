# Comic Agent アプリケーション ブロック図

## システム概要
Comic Agentは、ADK（Agent Development Kit）フレームワークを使用した漫画ストーリー生成システムです。

```mermaid
graph TB
    subgraph "外部サービス"
        GEMINI[Gemini API<br/>Google Generative AI]
        ENV[.env File<br/>環境変数管理]
    end

    subgraph "エントリーポイント"
        MAIN[run_agent.py<br/>メインアプリケーション]
        INPUT[User Input<br/>ジャンル入力]
    end

    subgraph "ADK フレームワーク層"
        AGENT[Agent Instance<br/>comic_story_creator_v1]
        RUNNER[Runner<br/>ADK実行エンジン]
        SESSION[InMemorySessionService<br/>セッション管理]
    end

    subgraph "設定管理"
        CONFIG[agent_config.yaml<br/>エージェント設定]
        TOOLS_CONFIG[Tools Configuration<br/>ツール定義]
    end

    subgraph "ツール層（ADK対応）"
        STORY_TOOL[generate_story_for_comic<br/>story_tools.py]
    end

    subgraph "レガシーエージェント層（未変換）"
        CHAR_AGENT[CharacterAgent<br/>character_agent.py]
        PLOT_AGENT[PlotOptimizerAgent<br/>plot_optimizer_agent.py]
    end

    subgraph "データ永続化"
        STORIES[stories/<br/>生成済み物語]
        DATA[data/<br/>キャラクターデータ]
    end

    subgraph "出力"
        JSON_OUT[JSON形式物語構造]
        TEXT_OUT[フォーマット済みテキスト]
    end

    %% フロー
    INPUT --> MAIN
    ENV --> MAIN
    CONFIG --> MAIN
    MAIN --> AGENT
    AGENT --> RUNNER
    RUNNER --> SESSION
    
    %% ADKツール連携
    RUNNER --> STORY_TOOL
    STORY_TOOL --> GEMINI
    GEMINI --> STORY_TOOL
    STORY_TOOL --> RUNNER
    
    %% 出力フロー
    RUNNER --> JSON_OUT
    RUNNER --> TEXT_OUT
    
    %% データ保存
    JSON_OUT --> STORIES
    CHAR_AGENT --> DATA
    
    %% 設定連携
    CONFIG --> TOOLS_CONFIG
    TOOLS_CONFIG --> STORY_TOOL

    %% スタイリング
    classDef adkFrame fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef legacyAgent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef data fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px

    class AGENT,RUNNER,SESSION adkFrame
    class CHAR_AGENT,PLOT_AGENT legacyAgent
    class GEMINI,ENV external
    class STORIES,DATA data
```

## 詳細コンポーネント説明

### 1. メインアプリケーション（run_agent.py）
- **役割**: システムのエントリーポイント
- **機能**:
  - 環境変数（.env）からGEMINI_API_KEYを読み込み
  - ADKフレームワークの初期化
  - ユーザー入力の処理
  - エージェントとの会話セッション管理

### 2. ADK フレームワーク層
#### Agent Instance (comic_story_creator_v1)
- **役割**: メインの物語生成エージェント
- **設定**: agent_config.yaml内のadk_agentsセクション
- **使用ツール**: generate_story_for_comic

#### Runner
- **役割**: ADKエージェントの実行エンジン
- **機能**: 非同期メッセージ処理、ツール呼び出し管理

#### SessionService
- **役割**: ユーザーセッションの管理
- **実装**: InMemorySessionService（メモリ内管理）

### 3. ツール層
#### generate_story_for_comic (story_tools.py)
- **役割**: 物語構造生成のADK対応ツール
- **入力**: genre, llm_model_name, temperature, max_tokens
- **出力**: JSON形式の物語構造（title, characters, plot, themes）
- **API**: Gemini API経由でLLM呼び出し

### 4. レガシーエージェント層（要変換）
#### CharacterAgent
- **役割**: キャラクター管理
- **状態**: クラスベース（ADK未対応）
- **データ**: characters.json形式で永続化

#### PlotOptimizerAgent  
- **役割**: プロット分析・改善提案
- **状態**: クラスベース（ADK未対応）
- **機能**: Gemini APIでプロット改善案生成

### 5. 設定管理
#### agent_config.yaml
```yaml
adk_agents:           # ADK対応エージェント
  comic_story_creator_v1: ...
agents:               # レガシーエージェント
  - character_agent_v1: ...
  - plot_optimizer_agent_v1: ...
tools:                # LLMツール設定
  - llm_tool_gemini_pro: ...
```

### 6. データフロー

```mermaid
sequenceDiagram
    participant User
    participant Main as run_agent.py
    participant Agent as ADK Agent
    participant Tool as story_tool
    participant Gemini as Gemini API

    User->>Main: ジャンル入力
    Main->>Agent: セッション作成・メッセージ送信
    Agent->>Tool: generate_story_for_comic呼び出し
    Tool->>Gemini: プロンプト送信
    Gemini->>Tool: JSON形式レスポンス
    Tool->>Agent: 物語構造データ
    Agent->>Main: フォーマット済み応答
    Main->>User: 物語表示
```

## システムの特徴

### ✅ ADK移行済み部分
- 物語生成機能（comic_story_creator_v1）
- ツール化された story_tools.py
- 非同期実行基盤

### 🔄 ADK移行待ち部分  
- キャラクター管理（CharacterAgent）
- プロット最適化（PlotOptimizerAgent）

### 🔒 セキュリティ
- 環境変数による API キー管理
- .env ファイルでの安全な秘密情報保存

### 📊 出力形式
- JSON構造化データ
- 人間読み取り可能なフォーマット済みテキスト
- ファイルベース永続化

## 技術スタック
- **フレームワーク**: Google ADK (Agent Development Kit)
- **LLM**: Gemini API (gemini-1.5-flash)
- **言語**: Python 3.x
- **非同期**: asyncio
- **設定**: YAML
- **データ**: JSON
- **環境管理**: python-dotenv
