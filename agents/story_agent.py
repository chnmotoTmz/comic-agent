from typing import Optional, Dict, Any
import yaml
import json
import os
from datetime import datetime
from pathlib import Path
import google.generativeai as genai

class SimpleStoryAgent:
    """
    指定されたジャンルに基づいて物語のアイデアを生成する簡単なエージェント。
    """
    def __init__(self, genre: str, config_path: str = None):
        self.genre = genre
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "agent_config.yaml")
        self.config = self.load_config()
        # エージェント固有の設定を取得
        self.agent_id = self.config.get("default_agent_id", "simple_story_agent_v1")
        self.agent_config = self._get_agent_specific_config()

        # LLMツール設定の初期化
        self.llm_tool_config = None
        self.api_key = os.environ.get("GEMINI_API_KEY") # 環境変数からAPIキーを取得
        if not self.api_key:
            print("警告: 環境変数 GEMINI_API_KEY が設定されていません。APIキーを直接設定します。")
            self.api_key = "AIzaSyDWhsY1oVCat_I1rDtInGOu764zrDObB4I" # 提供されたAPIキーを直接使用
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                print("Gemini APIキーが正常に設定されました。")
            except Exception as e:
                print(f"Gemini APIキーの設定中にエラーが発生しました: {e}")
                self.api_key = None # エラー時はAPIキーを無効化
        else:
            print("エラー: Gemini APIキーが利用できません。LLM機能は無効になります。")

        if self.config.get('tools'):
            for tool in self.config['tools']:
                if tool.get('id') == "llm_tool_gemini_pro": 
                    self.llm_tool_config = tool.get('config', {})
                    break
        
        self.story_structure = {
            "title": "",
            "characters": [],
            "plot": {
                "setup": "",
                "conflict": "",
                "resolution": ""
            },
            "themes": [],
            "genre": self.genre,
            "metadata": {
                "agent_version": "v0.1",
                "agent_id": self.agent_id,
                "config": str(self.config_path)
            }
        }

    def _get_agent_specific_config(self) -> Dict[str, Any]:
        """
        エージェント固有の設定を取得します。
        """
        if not self.config or 'agents' not in self.config:
            print("設定ファイルに 'agents' キーが存在しないか、設定が空です。")
            return {}
        
        for agent_config in self.config.get('agents', []):
            if agent_config.get('id') == self.agent_id:
                return agent_config.get('config', {})
        
        print(f"エージェントID '{self.agent_id}' に対応する設定が見つかりませんでした。")
        return {}

    def load_config(self) -> Dict[str, Any]:
        """
        設定ファイルを読み込みます。
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"設定ファイルの読み込み中にエラーが発生: {e}")
            return {}

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        実際にGemini APIを呼び出して物語の要素を生成します。
        """
        if not self.api_key or not self.llm_tool_config:
            print("LLMのAPIキーまたは設定が不十分なため、LLM呼び出しをスキップします。")
            return None

        model_name = self.llm_tool_config.get("model_name", "gemini-2.0-flash") # デフォルトを gemini-2.0-flash に戻す
        temperature = self.llm_tool_config.get("temperature", 0.7)
        max_tokens = self.llm_tool_config.get("max_tokens", 1000)

        print("\n--- Gemini API呼び出し ---")
        print(f"モデル: {model_name}")
        # システムプロンプトとユーザープロンプトを結合
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        print(f"統合プロンプト抜粋: {full_prompt[:200]}...")

        try:
            model = genai.GenerativeModel(
                model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            
            response = model.generate_content(full_prompt)
            
            if response.parts:
                generated_text = response.text
                print(f"Gemini応答テキスト(raw): {generated_text}")
                # LLMからの応答がJSON形式の文字列であることを期待
                try:
                    # 応答テキストの最初と最後にあるマークダウンのJSONブロック表記を削除
                    cleaned_text = generated_text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[len("```json"):]

                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-len("```")]
                    cleaned_text = cleaned_text.strip()
                    
                    llm_data = json.loads(cleaned_text)
                    print(f"Gemini応答JSON(parsed): {llm_data}")
                    return llm_data
                except json.JSONDecodeError as e:
                    print(f"LLM応答のJSONパースに失敗しました: {e}")
                    print(f"受信したテキスト(クリーンアップ後): {cleaned_text}")
                    return None
            else:
                print("Geminiからの応答が空か、期待した形式ではありません。")
                if response.prompt_feedback:
                    print(f"プロンプトフィードバック: {response.prompt_feedback}")
                return None
        except Exception as e:
            print(f"Gemini API呼び出し中にエラーが発生しました: {e}")
            return None

    def generate_story_structure(self) -> Dict[str, Any]:
        """
        物語の構造化データを生成します。
        LLM利用が有効な場合はLLMを使用し、そうでない場合や失敗した場合はテンプレートベースのロジックにフォールバックします。
        """
        use_llm = self.agent_config.get('use_llm', False)
        llm_generated_data = None

        if use_llm and self.llm_tool_config:
            prompt_templates = self.llm_tool_config.get('prompt_templates', {}).get('story', {})
            system_prompt = prompt_templates.get('system', "あなたは有能なストーリーテラーです。")
            user_prompt_template = prompt_templates.get('user', "ジャンル：{genre}\\\n物語を生成してください。") # 要素のプレースホルダーを削除
            
            # 要素に関する記述を削除
            # genre_elements = self.agent_config.get('genre_elements', {})
            # elements = genre_elements.get(self.genre, self.agent_config.get('llm_elements_placeholder', '未定義の要素'))
            
            user_prompt = user_prompt_template.format(genre=self.genre) # elementsを削除
            
            try:
                llm_response = self._call_llm(system_prompt, user_prompt)
                if llm_response and isinstance(llm_response, dict):
                    llm_generated_data = llm_response
                else:
                    print("LLMからの応答が無効か、期待した形式ではありません。")
            except Exception as e:
                print(f"LLM呼び出し中にエラーが発生しました: {e}")
                llm_generated_data = None # エラー時はフォールバック

        if llm_generated_data:
            print("LLM生成データを使用して物語構造を更新します。")
            self.story_structure.update({
                "title": llm_generated_data.get("title", f"{self.genre}の不思議な冒険（LLM）"),
                "plot": llm_generated_data.get("plot", self.story_structure['plot']) # plot全体を更新
            })
            # キャラクターやテーマもLLMに生成させる場合はここに追加
        else:
            if use_llm: # LLM使用設定だが、生成に失敗した場合
                print("LLMデータ生成に失敗したため、テンプレートベースのロジックにフォールバックします。")
            # 既存のテンプレートベースのロジック
            story_templates = self.agent_config.get('story_templates', {})
            if self.genre in story_templates:
                templates = story_templates[self.genre]
            else:
                templates = story_templates.get('default', {})
            
            default_plot = {
                "setup": "平和な世界で暮らしていた主人公は、ある日突然、不思議な出来事に巻き込まれます。",
                "conflict": "{genre}の要素を活かしながら、仲間たちと共に冒険を繰り広げ、ライバルとの対立や困難な課題に直面します。",
                "resolution": "知恵と勇気で困難を乗り越え、真の目的を達成します。"
            }

            plot = {
                "setup": templates.get("setup", default_plot["setup"]),
                "conflict": templates.get("conflict", default_plot["conflict"]).format(genre=self.genre),
                "resolution": templates.get("resolution", default_plot["resolution"])
            }
            self.story_structure.update({
                "title": f"{self.genre}の不思議な冒険（テンプレート）", # タイトルも更新
                "plot": plot
            })

        # キャラクターとテーマは当面固定（LLMで生成する場合は上記if/else内で処理）
        # metadata の更新もここで行う
        self.story_structure.update({
            "characters": [
                {"name": "主人公", "role": "protagonist", "description": "若き冒険者"},
                {"name": "賢者", "role": "support", "description": "主人公を導く賢者"},
                {"name": "仮面の人物", "role": "antagonist", "description": "謎めいたライバル"}
            ],
            "themes": ["友情の大切さ", "成長の物語", "正義と真実の追求"],
            "metadata": {
                "agent_version": self.story_structure.get("metadata", {}).get("agent_version", "v0.1"),
                "agent_id": self.agent_id,
                "config": str(self.config_path),
                "generation_type": "llm" if llm_generated_data else "template"
            }
        })
        return self.story_structure

    def generate_story(self, story_data: Dict[str, Any]) -> str:
        """
        物語のアイデアを生成します。
        """
        # story_data は run メソッドから渡される self.story_structure を想定
        
        story = f"""
タイトル：{story_data['title']}

登場人物：
{self._format_characters(story_data['characters'])}

あらすじ：
{story_data['plot']['setup']}
{story_data['plot']['conflict']}
{story_data['plot']['resolution']}

テーマ：
{self._format_themes(story_data['themes'])}

Note: 設定ファイル: {story_data['metadata']['config']}
生成タイプ: {story_data['metadata']['generation_type']}
"""
        return story
    
    def _format_characters(self, characters: list) -> str:
        return "\n".join([f"- {char['name']}：{char['description']}" for char in characters])

    def _format_themes(self, themes: list) -> str:
        return "\n".join([f"- {theme}" for theme in themes])
    
    def save_story(self, story_data: Dict[str, Any], story_text: str) -> str:
        """
        生成されたストーリーを保存します。
        
        Args:
            story_data: 構造化されたストーリーデータ
            story_text: 生成されたストーリーテキスト
            
        Returns:
            str: 保存されたファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        story_dir = Path(__file__).parent.parent / "stories"
        story_dir.mkdir(exist_ok=True)
        
        # 構造化データをJSONとして保存
        json_path = story_dir / f"story_{timestamp}_{self.genre}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(story_data, f, ensure_ascii=False, indent=2)
            
        # テキストファイルとして保存
        text_path = story_dir / f"story_{timestamp}_{self.genre}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(story_text)
            
        return str(json_path)
        
    def run(self):
        """
        エージェントを実行し、物語のアイデアを生成して保存します。
        """
        try:
            # 最初に物語構造を生成・更新
            current_story_data = self.generate_story_structure()
            # 更新されたstory_dataを使って物語テキストを生成
            generated_story_text = self.generate_story(current_story_data)
            
            print("\\n=== 生成されたストーリー ===")
            print(generated_story_text)
            print("==========================\\n")
            
            # ストーリーを保存
            saved_path = self.save_story(current_story_data, generated_story_text)
            print(f"\\nストーリーを保存しました: {saved_path}")
            
            return generated_story_text
        except Exception as e:
            print(f"ストーリー生成中にエラーが発生しました: {e}")
            return None