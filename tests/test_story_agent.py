import unittest
from pathlib import Path
import json
import yaml
from agents.story_agent import SimpleStoryAgent

class TestSimpleStoryAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        cls.test_config_path = Path(__file__).parent / "test_config.yaml"
        cls.test_genre = "ファンタジー"
        
        # テスト用の設定ファイルを作成
        test_config = {
            "default_agent_id": "simple_story_agent_v1",
            "agents": [
                {
                    "id": "simple_story_agent_v1",
                    "class": "agents.story_agent.SimpleStoryAgent",
                    "config": {
                        "story_templates": {
                            "default": {
                                "setup": "テスト用のセットアップ文",
                                "conflict": "{genre}のテスト用の展開文",
                                "resolution": "テスト用の解決文"
                            }
                        }
                    }
                }
            ]
        }
        with open(cls.test_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, allow_unicode=True)

    def setUp(self):
        """各テストケースの前に実行"""
        self.agent = SimpleStoryAgent(
            genre=self.test_genre,
            config_path=str(self.test_config_path)
        )

    def test_initialization(self):
        """初期化のテスト"""
        self.assertEqual(self.agent.genre, self.test_genre)
        self.assertTrue(Path(self.agent.config_path).exists())
        self.assertIsNotNone(self.agent.config)

    def test_story_structure_generation(self):
        """ストーリー構造生成のテスト"""
        story_data = self.agent.generate_story_structure()
        
        # 基本構造の確認
        self.assertIn("title", story_data)
        self.assertIn("characters", story_data)
        self.assertIn("plot", story_data)
        self.assertIn("themes", story_data)
        
        # プロットの構造確認
        plot = story_data["plot"]
        self.assertIn("setup", plot)
        self.assertIn("conflict", plot)
        self.assertIn("resolution", plot)
        
        # キャラクター配列の確認
        self.assertIsInstance(story_data["characters"], list)
        self.assertTrue(len(story_data["characters"]) > 0)
        
        # テーマの確認
        self.assertIsInstance(story_data["themes"], list)
        self.assertTrue(len(story_data["themes"]) > 0)

    def test_story_generation(self):
        """ストーリー生成のテスト"""
        story = self.agent.generate_story()
        
        # ストーリーテキストの基本確認
        self.assertIsInstance(story, str)
        self.assertTrue(len(story) > 0)
        
        # 必要な要素が含まれているか確認
        self.assertIn("タイトル：", story)
        self.assertIn("登場人物：", story)
        self.assertIn("あらすじ：", story)
        self.assertIn("テーマ：", story)

    def test_story_saving(self):
        """ストーリー保存機能のテスト"""
        story_data = self.agent.generate_story_structure()
        story_text = self.agent.generate_story()
        
        # 保存を実行
        saved_path = self.agent.save_story(story_data, story_text)
        self.assertTrue(Path(saved_path).exists())
        
        # JSONファイルの内容を確認
        with open(saved_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data["genre"], self.test_genre)
        self.assertIn("characters", loaded_data)
        self.assertIn("plot", loaded_data)

    def test_config_template_usage(self):
        """設定ファイルのテンプレート使用テスト"""
        story_data = self.agent.generate_story_structure()
        plot = story_data["plot"]
        
        # テスト用の設定が反映されているか確認
        self.assertEqual(plot["setup"], "テスト用のセットアップ文")
        self.assertEqual(
            plot["conflict"],
            f"{self.test_genre}のテスト用の展開文"
        )
        self.assertEqual(plot["resolution"], "テスト用の解決文")

    @classmethod
    def tearDownClass(cls):
        """テストクラスのクリーンアップ"""
        # テスト用の設定ファイルを削除
        cls.test_config_path.unlink(missing_ok=True)

def load_tests(loader, standard_tests, pattern):
    """テストスイートを定義"""
    suite = unittest.TestSuite()
    test_cases = [TestSimpleStoryAgent]
    for test_class in test_cases:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite

if __name__ == '__main__':
    unittest.main()
