import os
from dotenv import load_dotenv
from google.adk.agents import Agent

# .envファイルから環境変数を読み込み
load_dotenv()

def generate_story_for_comic(genre: str) -> dict:
    """指定されたジャンルに基づいて漫画の物語構造を生成します。
    
    Args:
        genre (str): 物語のジャンル（例: ファンタジー, SF, コメディ）
        
    Returns:
        dict: 物語構造（タイトル、キャラクター、プロット、テーマ）
    """
    import google.generativeai as genai
    import json
    
    # APIキーを設定
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"status": "error", "error_message": "GEMINI_API_KEY not found in environment variables."}
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
あなたはプロの漫画ストーリー作家です。{genre}ジャンルの魅力的な漫画の基本構造を作成してください。

以下のJSON形式で回答してください：

```json
{{
  "title": "魅力的なタイトル",
  "characters": [
    {{
      "name": "キャラクター名",
      "role": "主人公/ヒロイン/敵役等",
      "description": "キャラクターの簡単な説明"
    }}
  ],
  "plot": {{
    "setup": "物語の始まり・設定",
    "conflict": "葛藤・展開・困難",
    "resolution": "結末・解決"
  }},
  "themes": ["テーマ1", "テーマ2"]
}}
```

JSON以外の余計な文字は含めないでください。
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # ```json``` マークダウンを削除
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        story_data = json.loads(response_text.strip())
        return {
            "status": "success", 
            "story": story_data
        }
        
    except json.JSONDecodeError as e:
        return {
            "status": "error", 
            "error_message": f"JSON parsing failed: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error_message": f"Story generation failed: {str(e)}"
        }

def get_weather(city: str) -> dict:
    """天気情報を取得します（デモ用のモックデータ）。
    
    Args:
        city (str): 都市名
        
    Returns:
        dict: 天気情報
    """
    mock_weather = {
        "tokyo": {"status": "success", "report": "東京は晴れ、気温25度です。"},
        "newyork": {"status": "success", "report": "ニューヨークは曇り、気温15度です。"},
        "london": {"status": "success", "report": "ロンドンは雨、気温12度です。"}
    }
    
    city_key = city.lower().replace(" ", "")
    if city_key in mock_weather:
        return mock_weather[city_key]
    else:
        return {"status": "error", "error_message": f"申し訳ありません、{city}の天気情報はありません。"}

# Comic Story Creator Agent
root_agent = Agent(
    name="comic_story_creator",
    model="gemini-1.5-flash",
    description="Creates comic story structures based on specified genres.",
    instruction=(
        "あなたは創造的な漫画ストーリージェネレーターです。"
        "ユーザーからジャンルを指定されたら、'generate_story_for_comic'ツールを使用して、"
        "そのジャンルに合った魅力的な物語構造を生成してください。"
        "天気について聞かれた場合は、'get_weather'ツールを使用してください。"
        "生成された物語は分かりやすく整理して表示してください。"
    ),
    tools=[generate_story_for_comic, get_weather],
)
