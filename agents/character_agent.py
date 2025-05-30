from typing import Dict, Any, List, Optional
import yaml
import json # JSONモジュールをインポート
from pathlib import Path

class CharacterAgent:
    """
    物語の登場キャラクター情報を管理するエージェント。
    """
    def __init__(self, agent_id: str = "character_agent_v1", config_path: str = None):
        self.agent_id = agent_id
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "agent_config.yaml")
        self.config = self._load_config() # config には agent_config.yaml の全内容がロードされる
        # agent_config には、self.agent_id をキーとする設定を代入
        self.agent_config = self.config.get(self.agent_id, {}) if self.config else {}
        
        # データ永続化のための設定
        self.data_dir = Path(__file__).parent.parent / "data" / self.agent_id
        self.data_file_path = self.data_dir / "characters.json"
        self._ensure_data_dir_exists()

        self.characters: List[Dict[str, Any]] = self._load_characters_from_file() # ファイルから読み込む
        
        print(f"CharacterAgent '{self.agent_id}' が初期化されました。データパス: {self.data_file_path}")
        if not self.agent_config:
            print(f"警告: CharacterAgent '{self.agent_id}' の設定が config ファイルに見つかりません。")

    def _ensure_data_dir_exists(self):
        """データ保存用ディレクトリが存在することを確認し、なければ作成します."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"データディレクトリの作成中にエラーが発生しました ({self.data_dir}): {e}")

    def _load_characters_from_file(self) -> List[Dict[str, Any]]:
        """JSONファイルからキャラクターリストを読み込みます."""
        if not self.data_file_path.exists():
            return []
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                characters = json.load(f)
                if isinstance(characters, list):
                    print(f"{len(characters)} 件のキャラクターデータを '{self.data_file_path}' から読み込みました。")
                    return characters
                else:
                    print(f"エラー: '{self.data_file_path}' のデータ形式が不正です（リストではありません）。空のリストを返します。")
                    return []
        except FileNotFoundError:
            print(f"キャラクターデータファイル '{self.data_file_path}' が見つかりません。新規に作成されます。")
            return []
        except json.JSONDecodeError as e:
            print(f"キャラクターデータファイル '{self.data_file_path}' のJSONデコード中にエラー: {e}")
            return []
        except Exception as e:
            print(f"キャラクターデータの読み込み中に予期せぬエラーが発生: {e}")
            return []

    def _save_characters_to_file(self):
        """現在のキャラクターリストをJSONファイルに保存します."""
        self._ensure_data_dir_exists() # 保存前にディレクトリ確認
        try:
            with open(self.data_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.characters, f, ensure_ascii=False, indent=2)
            print(f"キャラクターデータを '{self.data_file_path}' に保存しました。")
        except Exception as e:
            print(f"キャラクターデータの保存中にエラーが発生 ({self.data_file_path}): {e}")

    def add_character(self, name: str, role: str, description: str) -> Dict[str, Any]:
        """キャラクターを追加し、ファイルに保存します."""
        # 既存キャラクターとの重複チェック (名前で判断)
        if any(char['name'] == name for char in self.characters):
            print(f"キャラクター '{name}' は既に存在するため、追加をスキップします。")
            existing_char = next((char for char in self.characters if char['name'] == name), None)
            return existing_char # 既存のキャラクター情報を返すか、Noneを返すか、仕様による

        character = {"name": name, "role": role, "description": description}
        self.characters.append(character)
        print(f"キャラクター追加: {name} ({role}) - {description}")
        self._save_characters_to_file() # 変更をファイルに保存
        return character

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """指定された名前のキャラクター情報を取得します."""
        for char in self.characters:
            if char["name"] == name:
                return char
        return None

    def list_characters(self) -> List[Dict[str, Any]]:
        """登録されている全キャラクターのリストを返します."""
        return self.characters

    def run(self, action: str = "list", **kwargs):
        """エージェントの主要な実行ロジック（ダミー）。"""
        print(f"\n--- CharacterAgent ({self.agent_id}) 実行 ---")
        if action == "add":
            name = kwargs.get("name")
            role = kwargs.get("role")
            description = kwargs.get("description")
            if name and role and description:
                self.add_character(name, role, description)
            else:
                print("キャラクター追加に必要な情報が不足しています。")
        elif action == "get":
            name = kwargs.get("name")
            if name:
                char_info = self.get_character(name)
                if char_info:
                    print(f"キャラクター情報: {char_info}")
                else:
                    print(f"キャラクター '{name}' は見つかりません。")
            else:
                print("キャラクター名が指定されていません。")
        elif action == "list":
            all_chars = self.list_characters()
            if all_chars:
                print("登録キャラクター一覧:")
                for char in all_chars:
                    print(f"- {char['name']} ({char['role']}): {char['description']}")
            else:
                print("登録されているキャラクターはいません。")
        else:
            print(f"未定義のアクション: {action}")
        print("------------------------------------")

if __name__ == '__main__':
    # 簡単なテスト用
    # このファイル単体で実行する場合、設定ファイルパスを適切に指定する必要がある
    # config_path_test = str(Path(__file__).parent.parent / "config" / "agent_config.yaml")
    # char_agent = CharacterAgent(agent_id="character_agent_v1", config_path=config_path_test)
    # char_agent.run(action="add", name="主人公A", role="勇者", description="伝説の剣を探す若者")
    # char_agent.run(action="add", name="ライバルB", role="魔剣士", description="主人公の前に立ちはだかる謎の剣士")
    # char_agent.run(action="list")
    # char_agent.run(action="get", name="主人公A")
    print("CharacterAgentの単体テストは、設定ファイルを読み込める環境で実行してください。")
