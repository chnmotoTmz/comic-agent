import json
import os
import requests
from typing import Dict, Any
from pathlib import Path

class RedmineSetup:
    def __init__(self):
        self.url = 'http://192.168.1.40:3000'
        self.api_key = '6a8cf88d2a4e912477e8f82053ec383850f63572'
        self.headers = {
            'X-Redmine-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.project_id = None

    def create_project(self, project_data: Dict[str, Any]) -> int:
        """プロジェクトを作成"""
        url = f"{self.url}/projects.json"
        data = {'project': project_data}
        print(f"\nPOST {url}")
        print("Headers:", json.dumps(self.headers, indent=2))
        print("Data:", json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post(url, headers=self.headers, json=data)
        print(f"Status: {response.status_code}")
        print("Response:", response.text)
        
        response.raise_for_status()
        self.project_id = response.json()['project']['id']
        return self.project_id

    def get_project_id(self, identifier: str) -> int:
        """既存のプロジェクトIDを取得"""
        url = f"{self.url}/projects/{identifier}.json"
        print(f"\nGET {url}")
        response = requests.get(url, headers=self.headers)
        print(f"Status: {response.status_code}")
        print("Response:", response.text)
        
        response.raise_for_status()
        return response.json()['project']['id']

    def create_version(self, project_id: str, version_data: Dict[str, Any]) -> int:
        """バージョンを作成"""
        url = f"{self.url}/projects/{project_id}/versions.json"
        data = {'version': version_data}
        print(f"\nPOST {url}")
        print("Data:", json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post(url, headers=self.headers, json=data)
        print(f"Status: {response.status_code}")
        print("Response:", response.text)
        
        response.raise_for_status()
        return response.json()['version']['id']

    def create_issue(self, issue_data: Dict[str, Any]) -> int:
        """チケットを作成"""
        issue_data['project_id'] = self.project_id
        url = f"{self.url}/issues.json"
        data = {'issue': issue_data}
        print(f"\nPOST {url}")
        print("Data:", json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post(url, headers=self.headers, json=data)
        print(f"Status: {response.status_code}")
        print("Response:", response.text)
        
        response.raise_for_status()
        return response.json()['issue']['id']

    def test_connection(self):
        """Redmine接続をテスト"""
        url = f"{self.url}/users/current.json"
        print(f"\nGET {url}")
        response = requests.get(url, headers=self.headers)
        print(f"Status: {response.status_code}")
        print("Response:", response.text)
        return response.status_code == 200

def main():
    redmine = RedmineSetup()
    print("Redmine接続テスト中...")
    
    if not redmine.test_connection():
        print("Redmineサーバーへの接続に失敗しました。")
        return

    print("接続成功！プロジェクトのセットアップを開始します。")
    
    script_dir = Path(__file__).parent.parent
    setup_file = script_dir / 'docs' / 'redmine' / 'project_setup.json'
    
    with open(setup_file, 'r', encoding='utf-8') as f:
        setup_data = json.load(f)
        
    try:
        try:
            project_id = redmine.create_project(setup_data['project'])
            print(f"\nプロジェクトを作成しました: ID {project_id}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422 and "Identifier has already been taken" in e.response.text:
                print("プロジェクトは既に存在します。既存のプロジェクトを使用します。")
                project_id = redmine.get_project_id(setup_data['project']['identifier'])
                redmine.project_id = project_id
            else:
                raise

        for version in setup_data['versions']:
            try:
                version_id = redmine.create_version(setup_data['project']['identifier'], version)
                print(f"バージョンを作成しました: {version['name']} (ID: {version_id})")
            except requests.exceptions.HTTPError as e:
                print(f"バージョン '{version['name']}' の作成中にエラー: {str(e)}")
                continue

        for issue in setup_data['issues']:
            try:
                issue_id = redmine.create_issue(issue)
                print(f"チケットを作成しました: {issue['subject']} (ID: {issue_id})")
            except requests.exceptions.HTTPError as e:
                print(f"チケット '{issue['subject']}' の作成中にエラー: {str(e)}")
                continue

    except requests.exceptions.RequestException as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == '__main__':
    main()
