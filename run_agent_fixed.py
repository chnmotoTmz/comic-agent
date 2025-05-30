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
from datetime import datetime
from pathlib import Path

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

# Helper functions for formatting story elements
def _format_characters_rf(characters: list) -> str:
    """Formats character list into a string, including their roles."""
    if not characters:
        return "登場人物情報なし"
    return "\n".join([f"- {char.get('name', '名前なし')} (役割: {char.get('role', '役割不明')}): {char.get('description', '詳細なし')}" for char in characters])

def _format_themes_rf(themes: list) -> str:
    """Formats theme list into a string."""
    if not themes:
        return "テーマ情報なし"
    return "\n".join([f"- {theme}" for theme in themes])

def save_story_artifacts(story_json_str: str, genre: str, config_path: str):
    """
    Saves the generated story as JSON and a human-readable text file,
    including genre and metadata.
    """
    try:
        story_data = json.loads(story_json_str)
    except json.JSONDecodeError as e:
        print(f"エラー: Story JSONのパースに失敗しました: {e}")
        print(f"受信した文字列: {story_json_str}")
        # Attempt to save even partial/malformed string as text for debugging
        timestamp_err = datetime.now().strftime("%Y%m%d_%H%M%S")
        story_dir_err = Path("stories")
        story_dir_err.mkdir(exist_ok=True)
        err_filename = f"error_story_{timestamp_err}_{genre.replace(' ', '_').lower()}.txt"
        err_text_path = story_dir_err / err_filename
        with open(err_text_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error parsing JSON. Original string:\n{story_json_str}")
        print(f"エラーが発生したため、受信した生の文字列を {err_text_path} に保存しました。")
        return

    # Add genre and metadata
    story_data['genre'] = genre
    
    metadata = {
        'agent_version': "v1_adk_refactored",
        'config_path': config_path,
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"), # Consistent timestamp
        'generation_type': "adk_agent"
    }
    story_data['metadata'] = metadata
    
    # Filename generation (timestamp from metadata for consistency if preferred)
    timestamp = metadata['timestamp'] 
    story_dir = Path("stories")
    story_dir.mkdir(exist_ok=True) 

    base_filename = f"story_{timestamp}_{genre.replace(' ', '_').lower()}"

    # Save modified JSON (with genre and metadata)
    json_path = story_dir / f"{base_filename}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(story_data, f, ensure_ascii=False, indent=2)
    
    # Generate and save human-readable text version using modified story_data
    text_story = f"""タイトル：{story_data.get('title', 'タイトルなし')}

登場人物：
{_format_characters_rf(story_data.get('characters', []))}

あらすじ：
{story_data.get('plot', {}).get('setup', '導入なし')}
{story_data.get('plot', {}).get('conflict', '葛藤なし')}
{story_data.get('plot', {}).get('resolution', '解決なし')}

テーマ：
{_format_themes_rf(story_data.get('themes', []))}
"""
    text_path = story_dir / f"{base_filename}.txt"
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text_story)

    print(f"\n物語を保存しました:")
    print(f"  JSON: {json_path}")
    print(f"  テキスト: {text_path}")

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
        
        # Save the story artifacts
        save_story_artifacts(final_agent_response_str, genre, config_path)
        
    except json.JSONDecodeError:
        print("\n最終応答はJSON形式ではありませんでした。そのまま表示します。")
        # Even if not perfect JSON, try to save what we got, identified by genre
        save_story_artifacts(final_agent_response_str, f"{genre}_partial_output", config_path)
    except TypeError: # Should be less likely if JSON parsing is robust
        print("\n最終応答の解析中に型エラーが発生しました。")
        # Try to save what we got
        save_story_artifacts(final_agent_response_str, f"{genre}_type_error_output", config_path)


if __name__ == "__main__":
    asyncio.run(main())
