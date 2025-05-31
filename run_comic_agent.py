#!/usr/bin/env python3
"""
Comic Agent直接実行スクリプト
"""
import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.multi_tool_agent.agent import root_agent as comic_agent

def main():
    """Comic Agentを直接実行"""
    print("🎭 Comic Agent起動中...")
    print("=" * 50)
    
    # エージェントの初期化確認
    print(f"エージェント名: {comic_agent.name}")
    print(f"モデル: {comic_agent.model}")
    print(f"利用可能ツール: {[tool.__name__ for tool in comic_agent.tools]}")
    print("=" * 50)
    
    # 対話開始
    print("💬 エージェントと対話を開始します")
    print("（終了するには 'quit' または 'exit' を入力）")
    print()
    
    while True:
        try:
            user_input = input("あなた: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '終了']:
                print("👋 Comic Agentを終了します")
                break
                
            if not user_input:
                continue            # エージェントに質問
            print("🤖 Comic Agent: 考え中...")
            
            # ADK用のasync実行関数
            import asyncio
            from google.genai import types
            from google.adk.sessions import InMemorySessionService
            from google.adk.runners import Runner
            
            async def run_agent_async():
                # セッション管理の設定
                session_service = InMemorySessionService()
                APP_NAME = "comic_agent_app"
                USER_ID = "user_1"
                SESSION_ID = "session_001"
                
                # セッション作成
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID
                )
                
                # ランナー作成
                runner = Runner(
                    agent=comic_agent,
                    app_name=APP_NAME,
                    session_service=session_service
                )
                
                # ユーザーメッセージの準備
                content = types.Content(role='user', parts=[types.Part(text=user_input)])
                
                # エージェント実行（正しいAPIに修正）
                events = runner.run_async(
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    content=content
                )
                
                # レスポンスの取得
                async for event in events:
                    if event.is_final_response():
                        return event.response.candidate.content.parts[0].text
                        
                return "エージェントからの応答がありませんでした。"
            
            # 非同期実行
            response = asyncio.run(run_agent_async())
            print(f"🤖 Comic Agent: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Comic Agentを終了します")
            break
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            print("再試行してください")

if __name__ == "__main__":
    main()
