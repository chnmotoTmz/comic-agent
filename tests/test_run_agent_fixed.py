import unittest
from unittest.mock import patch, MagicMock
import asyncio
import json
from pathlib import Path
import os
import sys
from datetime import datetime

# Add the project root to sys.path to allow importing run_agent_fixed
# This assumes the test is run from the project root or the 'tests' directory.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # Attempt to import the main function from run_agent_fixed
    # It's important that run_agent_fixed.py can be imported without
    # immediately running asyncio.run(main()) if it's also the main script.
    # For this test, we will call main() explicitly.
    from run_agent_fixed import main as run_agent_main
except ImportError as e:
    print(f"Error importing run_agent_fixed: {e}")
    print("Ensure run_agent_fixed.py is in the project root and sys.path is correct.")
    # Define a dummy main if import fails, so the rest of the test structure can be parsed
    async def run_agent_main():
        print("Dummy run_agent_main called due to import error.")
        pass 

class TestRunAgentFixed(unittest.TestCase):

    def setUp(self):
        # Ensure the stories directory exists
        self.stories_dir = Path("stories")
        self.stories_dir.mkdir(exist_ok=True)
        
        # Store current time to help identify files created during the test
        self.test_start_time = datetime.now()

        # Set a dummy API key if not present, as ADK might require it.
        # The actual LLM call will be mocked if this is a true unit test,
        # but if it's an integration test, a key might be needed.
        # For now, we assume the test environment might provide it,
        # or the call to the agent in run_agent_fixed.main would be mocked
        # in a more granular test. This test is more of an integration test
        # for run_agent_fixed.py's main logic.
        if "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = "test_api_key_for_run_agent_fixed"


    @patch('run_agent_fixed.call_agent_async') # Mock the actual agent call
    @patch('builtins.input', return_value='テストジャンル')
    def test_generate_and_save_story(self, mock_input, mock_call_agent_async):
        # Mock the response from the agent to control test data
        # This response should be what the agent is expected to return as a string
        mock_story_data = {
            "title": "テストの物語",
            "characters": [{"name": "主人公", "role": "主役", "description": "テスト用の主人公"}],
            "plot": {"setup": "導入部", "conflict": "葛藤部", "resolution": "解決部"},
            "themes": [] # Crucially, themes should be empty as per recent changes
        }
        mock_agent_response_str = json.dumps(mock_story_data)
        
        # Configure the mock for call_agent_async
        # It's an async function, so its mock needs to be an AsyncMock
        # or return an awaitable if it's called with await.
        # Since we are mocking it directly, we can make it return the desired string.
        async def mock_async_call(*args, **kwargs):
            return mock_agent_response_str
        mock_call_agent_async.side_effect = mock_async_call

        # Run the main function from run_agent_fixed.py
        try:
            asyncio.run(run_agent_main())
        except Exception as e:
            self.fail(f"run_agent_main() raised an exception: {e}")

        # Find the created files
        # We need to be careful here to find files created *after* test_start_time
        # or use a more robust way if filenames are very predictable.
        # For simplicity, we'll glob and assume the latest one is ours if multiple match.
        
        # A short delay to ensure files are written
        # asyncio.run(asyncio.sleep(0.1)) # May not be needed depending on filesystem timing

        json_files = sorted(
            [f for f in self.stories_dir.glob(f"story_*_テストジャンル.json") 
             if datetime.fromtimestamp(f.stat().st_ctime) >= self.test_start_time],
            key=lambda f: f.stat().st_ctime, reverse=True
        )
        txt_files = sorted(
            [f for f in self.stories_dir.glob(f"story_*_テストジャンル.txt")
             if datetime.fromtimestamp(f.stat().st_ctime) >= self.test_start_time],
            key=lambda f: f.stat().st_ctime, reverse=True
        )

        self.assertTrue(json_files, "No JSON file found for 'テストジャンル'")
        self.assertTrue(txt_files, "No TXT file found for 'テストジャンル'")

        latest_json_file = json_files[0]
        latest_txt_file = txt_files[0]

        # Verify JSON content
        with open(latest_json_file, 'r', encoding='utf-8') as f:
            saved_story_data = json.load(f)

        self.assertIn("title", saved_story_data)
        self.assertIsInstance(saved_story_data["title"], str)
        self.assertIn("characters", saved_story_data)
        self.assertIsInstance(saved_story_data["characters"], list)
        self.assertIn("plot", saved_story_data)
        self.assertIsInstance(saved_story_data["plot"], dict)
        
        self.assertIn("genre", saved_story_data)
        self.assertEqual(saved_story_data["genre"], "テストジャンル")
        
        self.assertIn("metadata", saved_story_data)
        self.assertIsInstance(saved_story_data["metadata"], dict)
        
        self.assertIn("themes", saved_story_data)
        self.assertEqual(saved_story_data["themes"], []) # Verify themes is an empty list

        # Verify TXT file
        self.assertTrue(latest_txt_file.exists(), f"TXT file {latest_txt_file} does not exist.")
        self.assertTrue(latest_txt_file.stat().st_size > 0, f"TXT file {latest_txt_file} is empty.")

        # Cleanup: Delete the generated files
        try:
            os.remove(latest_json_file)
            os.remove(latest_txt_file)
        except OSError as e:
            print(f"Warning: Could not delete test files {latest_json_file}, {latest_txt_file}: {e}")

    def tearDown(self):
        # Clean up any environment variables set for the test if necessary
        if os.environ.get("GEMINI_API_KEY") == "test_api_key_for_run_agent_fixed":
            del os.environ["GEMINI_API_KEY"]


if __name__ == '__main__':
    unittest.main()
