\
from typing import Dict, Any, Optional
import google.generativeai as genai
import json
import os

def generate_story_for_comic(genre: str, llm_model_name: str, temperature: float, max_tokens: int) -> Optional[Dict[str, Any]]:
    """
    指定されたジャンルに基づいて、漫画の物語構造（タイトル、キャラクター、プロット、テーマ）を生成します。

    Args:
        genre (str): 物語のジャンル (例: "ファンタジー", "SF", "学園コメディ")。
        llm_model_name (str): 使用するLLMのモデル名。
        temperature (float): 生成時のランダム性を制御する温度。
        max_tokens (int): 生成する最大トークン数。

    Returns:
        Optional[Dict[str, Any]]: 生成された物語の構造を含む辞書。
                                   要素は "title", "characters", "plot", "themes"。
                                   エラー時は None を返します。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー (generate_story_for_comic): 環境変数 GEMINI_API_KEY が設定されていません。")
        return None

    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"エラー (generate_story_for_comic): Gemini APIキーの設定中にエラー: {e}")
        return None

    system_prompt = """あなたはクリエイティブなストーリージェネレーターです。
ユーザーから指定されたジャンルに基づいて、漫画に適した物語の構造を考案してください。
物語の構造は以下のキーを持つJSONオブジェクトとして返してください:
- title: str (物語のタイトル)
- characters: list[dict] (登場人物のリスト、各辞書は {"name": "キャラ名", "description": "簡単な説明"} を持つ)
- plot: dict (物語のプロット、{"setup": "導入", "conflict": "葛藤・展開", "resolution": "結末"} を持つ)
- themes: list[str] (物語の主要なテーマのリスト)
"""
    user_prompt = f"ジャンル： {genre}"

    full_prompt = f"{system_prompt}\\n\\nユーザーの指示:\\n{user_prompt}\\n\\nJSON形式で物語の構造を生成してください。"

    print(f"--- generate_story_for_comic: LLM呼び出し ---")
    print(f"モデル: {llm_model_name}, ジャンル: {genre}")

    try:
        model = genai.GenerativeModel(
            llm_model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" # JSON出力を期待
            )
        )
        response = model.generate_content(full_prompt)

        if response.parts:
            generated_text = response.text
            print(f"LLM応答テキスト(raw): {generated_text[:300]}...") # 長すぎる場合があるので一部表示
            try:
                # response_mime_type="application/json" を指定した場合、
                # response.text は既にパース可能なJSON文字列のはず
                story_data = json.loads(generated_text)
                
                # 必須キーの存在チェック (簡易的)
                required_keys = ["title", "characters", "plot", "themes"]
                if all(key in story_data for key in required_keys):
                    print("物語構造の生成に成功しました。")
                    return story_data
                else:
                    print(f"エラー: LLM応答に必要なキーが含まれていません。受信データ: {story_data}")
                    return None
            except json.JSONDecodeError as e:
                print(f"LLM応答のJSONパースに失敗: {e}")
                print(f"受信したテキスト: {generated_text}")
                return None
        else:
            print("LLMからの応答が空か、期待した形式ではありません。")
            if response.prompt_feedback:
                print(f"プロンプトフィードバック: {response.prompt_feedback}")
            return None
    except Exception as e:
        print(f"LLM API呼び出し中にエラーが発生: {e}")
        return None

if __name__ == '__main__':
    # 簡単なテスト用 (環境変数 GEMINI_API_KEY を設定して実行)
    if not os.environ.get("GEMINI_API_KEY"):
        print("テスト実行のため、環境変数 GEMINI_API_KEY を設定してください。")
    else:
        print("テスト: ファンタジーの物語を生成")
        fantasy_story = generate_story_for_comic("壮大なファンタジー")
        if fantasy_story:
            print("\\n生成された物語構造:")
            print(json.dumps(fantasy_story, indent=2, ensure_ascii=False))

        print("\\nテスト: SFの物語を生成")
        sf_story = generate_story_for_comic("宇宙を舞台にしたSFアドベンチャー")
        if sf_story:
            print("\\n生成された物語構造:")
            print(json.dumps(sf_story, indent=2, ensure_ascii=False))
