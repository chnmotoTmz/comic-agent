import sys
import asyncio
import os
import yaml
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
import google.generativeai as genai
from agents.story_tools import generate_story_for_comic
import json

# 環境変数からAPIキーを読み込む
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google AI APIを初期化
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    os.environ["GOOGLE_AI_API_KEY"] = GEMINI_API_KEY  # ADKが認識する環境変数名

async def call_agent_async(
    runner: Runner, session_id: str, user_input: str, user_id: str = "user_123"
):
    """ADKエージェントを非同期に呼び出し、やり取りを処理するヘルパー関数"""
    print(f"\nユーザー: {user_input}")
    print("-" * 20)

    response_stream = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(role="user", parts=[Part(text=user_input)]),
    )

    final_response_parts = []
    async for chunk in response_stream:
        if chunk.content:
            for part in chunk.content.parts:
                if part.text:
                    print(f"エージェント: {part.text}")
                    final_response_parts.append(part.text)
                if part.tool_code:
                    print(f"エージェント (ツールコード): {part.tool_code}")
                if part.tool_outputs:
                    print(f"エージェント (ツール出力): {part.tool_outputs}")

    final_response = "".join(final_response_parts)
    print("-" * 20)
    print(f"最終応答: {final_response}")
    print("-" * 20)
    return final_response


async def main():
    """メインの非同期関数"""
    if not GEMINI_API_KEY:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        return

    config_path = "config/agent_config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {config_path}")
        return
    except yaml.YAMLError as e:
        print(f"エラー: 設定ファイルの解析中にエラーが発生しました: {e}")
        return

    agent_id_str = "comic_story_creator_v1" # 設定ファイル内のエージェントID
    agent_config_data = config.get("adk_agents", {}).get(agent_id_str)
    if not agent_config_data:
        print(f"エラー: `{agent_id_str}` の設定が config/agent_config.yaml に見つかりません。")
        return

    # 利用可能なツールとその実装をマッピング (Agent作成前に定義)
    available_tools_map = {
        "agents.story_tools.generate_story_for_comic": generate_story_for_comic
    }

    # 設定ファイルからツールの名前リストを取得し、実際の呼び出し可能オブジェクトに解決
    config_tool_names = agent_config_data.get("tools", [])
    agent_tools_callables = []
    for tool_name in config_tool_names:
        if tool_name in available_tools_map:
            agent_tools_callables.append(available_tools_map[tool_name])
        else:
            print(f"警告: エージェント '{agent_id_str}' の設定にあるツール '{tool_name}' が、"
                  f"定義済みのavailable_tools_mapに見つかりません。")

    # ADK Agentのインスタンス化
    try:
        agent_instance = Agent(
            name=agent_id_str, 
            description=agent_config_data.get("description", "Comic story creator agent."),
            model=agent_config_data.get("model", "gemini-2.0-flash"),
            instruction=agent_config_data.get("instruction", "You are a creative story generator."),
            tools=agent_tools_callables
        )
    except Exception as e:
        print(f"Agentの初期化中にエラーが発生しました: {e}")
        return

    # SessionServiceとRunnerの準備
    session_service = InMemorySessionService()
    app_name = "ComicAgentApp" # アプリケーション名

    try:
        runner = Runner(
            session_service=session_service,
            app_name=app_name,
            agent=agent_instance
        )
    except Exception as e:
        print(f"Runnerの初期化中にエラーが発生しました: {e}")
        return
        
    # ユーザーからの入力を受け付ける
    genre = input("物語のジャンルを入力してください (例: ファンタジー, SF, コメディ): ")
    if not genre:
        print("ジャンルが入力されませんでした。処理を終了します。")
        return

    # セッションを作成
    user_id = "user_123"
    session_id = "session_123"
    
    try:
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        print(f"セッションを作成しました: {session.id}")
    except Exception as e:
        print(f"セッション作成中にエラーが発生しました: {e}")
        return

    user_message = f"ジャンル: {genre}"
    print(f"\n『{genre}』の物語を生成します...")
    
    final_agent_response_str = await call_agent_async(
        runner=runner,
        session_id=session_id,
        user_input=user_message,
        user_id=user_id
    )

    # 最終応答がJSON文字列であることを期待している
    try:
        story_json = json.loads(final_agent_response_str)
        print("\n生成された物語の詳細:")
        print(f"  タイトル: {story_json.get('title', 'N/A')}")
        print(f"  登場人物: {story_json.get('characters', 'N/A')}")
        print(f"  プロット: {story_json.get('plot', 'N/A')}")
        print(f"  テーマ: {story_json.get('themes', 'N/A')}")
    except json.JSONDecodeError:
        print("\n最終応答はJSON形式ではありませんでした。そのまま表示します。")
    except TypeError:
        print("\n最終応答の解析中に型エラーが発生しました。")

if __name__ == "__main__":
    asyncio.run(main())
