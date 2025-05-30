from typing import Dict, Any, Optional
import yaml
from pathlib import Path
import google.generativeai as genai # Gemini APIを利用する場合
import os # APIキーのため
import json # LLM応答パースのため

class PlotOptimizerAgent:
    """
    物語のプロット構造を分析し、改善提案を行うエージェント。
    """
    def __init__(self, agent_id: str = "plot_optimizer_agent_v1", config_path: str = None):
        self.agent_id = agent_id
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "agent_config.yaml")
        self.config = self._load_config() # config_path からYAML全体をロード
        # self.agent_config にはこのエージェントIDの設定を代入
        self.agent_config = self.config.get(self.agent_id, {}) if self.config else {}

        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print(f"警告 ({self.agent_id}): 環境変数 GEMINI_API_KEY が未設定。APIキーを直接設定します。")
            self.api_key = "AIzaSyDWhsY1oVCat_I1rDtInGOu764zrDObB4I" # フォールバック
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                print(f"Gemini APIキーが正常に設定されました ({self.agent_id})。")
            except Exception as e:
                print(f"Gemini APIキーの設定中にエラーが発生 ({self.agent_id}): {e}")
                self.api_key = None
        else:
            print(f"エラー ({self.agent_id}): Gemini APIキーが利用できません。LLM機能は無効になります。")

        # LLMツール設定の取得
        self.llm_tool_config = None
        llm_tool_id = self.agent_config.get("llm_tool_id")
        if llm_tool_id and self.config.get('tools'):
            for tool in self.config['tools']:
                if tool.get('id') == llm_tool_id:
                    self.llm_tool_config = tool.get('config', {})
                    break
        
        if not self.llm_tool_config:
            print(f"警告 ({self.agent_id}): LLMツール設定 '{llm_tool_id}' が見つからないか、tools設定がありません。"
                  f"agent_config: {self.agent_config}")

        print(f"PlotOptimizerAgent '{self.agent_id}' が初期化されました。")
        if not self.agent_config:
            print(f"警告: PlotOptimizerAgent '{self.agent_id}' の設定が config ファイルに見つかりません。")

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) # YAML全体をロード
        except Exception as e:
            print(f"PlotOptimizerAgent設定ファイルの読み込み中にエラーが発生: {e}")
            return {}

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.llm_tool_config:
            print(f"LLM ({self.agent_id}) のAPIキーまたは設定が不十分なため、LLM呼び出しをスキップします。")
            return None

        # agent_config からモデル名を取得し、なければ llm_tool_config から、それでもなければデフォルト値
        model_name = self.agent_config.get("model_name", self.llm_tool_config.get("model_name", "gemini-pro"))
        temperature = self.llm_tool_config.get("temperature", 0.7)
        max_tokens = self.llm_tool_config.get("max_tokens", 1500)

        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        print(f"\\\\n--- PlotOptimizerAgent ({self.agent_id}) Gemini API呼び出し ---")
        print(f"モデル: {model_name}")
        print(f"統合プロンプト抜粋: {full_prompt[:250]}...")

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
                try:
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
                    print(f"LLM応答のJSONパースに失敗 ({self.agent_id}): {e}")
                    print(f"受信したテキスト(クリーンアップ後): {cleaned_text}")
                    # JSONでなくてもテキストとして提案を返すことも検討
                    return {"suggestion_text": cleaned_text} 
            else:
                print(f"Geminiからの応答が空か、期待した形式ではありません ({self.agent_id})。")
                if response.prompt_feedback:
                    print(f"プロンプトフィードバック: {response.prompt_feedback}")
                return None
        except Exception as e:
            print(f"Gemini API呼び出し中にエラーが発生 ({self.agent_id}): {e}")
            return None

    def analyze_plot(self, plot_summary: Dict[str, str], genre: str = "指定なし") -> Optional[Dict[str, Any]]:
        """プロット概要を分析し、改善提案をLLMに問い合わせます。"""
        # use_llm の設定を agent_config から直接参照するように変更
        if not self.agent_config.get("use_llm", True): # デフォルトはTrueとするか、設定ファイルで明示
            print(f"PlotOptimizerAgent ({self.agent_id}) はLLMを使用しない設定です。")
            return {"suggestion_text": "LLMを使用しない設定です。"}
        
        if not self.llm_tool_config:
            print(f"PlotOptimizerAgent ({self.agent_id}) のLLMツール設定が不十分です。")
            return {"suggestion_text": "LLMツール設定が不十分です。"}

        # プロンプトテンプレートを agent_config から取得
        prompt_template_str = self.agent_config.get("prompt_template")
        if not prompt_template_str:
            print(f"警告 ({self.agent_id}): プロンプトテンプレートが設定されていません。デフォルトのプロンプトを使用します。")
            # デフォルトのプロンプトを設定 (もしくはエラー終了)
            prompt_template_str = "プロット概要:\n{plot_summary}\n\n改善案を提案してください。"
        
        # システムプロンプトはLLMツール設定から取得、なければデフォルト
        system_prompt = self.llm_tool_config.get('prompt_templates', {}).get('plot_optimization', {}).get('system',
            "あなたは経験豊富な編集者です。提供されたプロットの概要を分析し、具体的な改善提案をしてください。"
        )
        
        # plot_summary を文字列に変換 (LLMが扱いやすいように)
        plot_summary_text = f"導入：{plot_summary.get('setup', '')}\n葛藤：{plot_summary.get('conflict', '')}\n解決：{plot_summary.get('resolution', '')}"
        
        user_prompt = prompt_template_str.format(plot_summary=plot_summary_text, genre=genre)

        suggestion = self._call_llm(system_prompt, user_prompt)
        return suggestion

    def run(self, plot_data: Dict[str, Any], genre: str = "指定なし") -> Optional[Dict[str, Any]]:
        """エージェントの主要な実行ロジック。"""
        print(f"\n--- PlotOptimizerAgent ({self.agent_id}) 実行 ---")
        if not isinstance(plot_data, dict) or not all(k in plot_data for k in ["setup", "conflict", "resolution"]):
            print("エラー: プロットデータが不正です。'setup', 'conflict', 'resolution' を含む辞書を指定してください。")
            return None
        
        optimization_result = self.analyze_plot(plot_data, genre)
        
        if optimization_result:
            print("プロット最適化提案:")
            if "analysis_points" in optimization_result and isinstance(optimization_result["analysis_points"], list):
                for point in optimization_result["analysis_points"]:
                    print(f"  - 分析点: {point.get('point', 'N/A')}")
                    print(f"    提案: {point.get('suggestion', 'N/A')}")
            if "overall_suggestion" in optimization_result:
                print(f"  全体的な提案: {optimization_result['overall_suggestion']}")
            if "suggestion_text" in optimization_result and not ("analysis_points" in optimization_result or "overall_suggestion" in optimization_result):
                 print(f"  提案: {optimization_result['suggestion_text']}") # JSONパース失敗時のフォールバック
        else:
            print("プロット最適化の提案は得られませんでした。")
        print("------------------------------------------")
        return optimization_result

if __name__ == '__main__':
    # 簡単なテスト用
    # config_path_test = str(Path(__file__).parent.parent / "config" / "agent_config.yaml")
    # plot_agent = PlotOptimizerAgent(agent_id="plot_optimizer_agent_v1", config_path=config_path_test)
    # test_plot = {
    #     "setup": "平和な村に魔王が攻めてきた。",
    #     "conflict": "勇者が仲間と魔王を倒しに行くが、途中で仲間割れ。",
    #     "resolution": "一人になった勇者が覚醒し魔王を倒した。"
    # }
    # plot_agent.run(plot_data=test_plot, genre="ファンタジー")
    print("PlotOptimizerAgentの単体テストは、設定ファイルを読み込める環境で実行してください。")
