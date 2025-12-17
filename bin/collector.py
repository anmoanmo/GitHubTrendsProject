import requests
from bs4 import BeautifulSoup
import json
import datetime
import os

# 定义路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")
FILE_PATH = os.path.join(DATA_DIR, f"github_trending_{DATE_STR}.json")

def fetch_data():
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        repos = []
        
        for article in soup.select('article.Box-row'):
            # 1. 获取项目名
            h1 = article.select_one('h1')
            name = h1.text.strip().replace("\n", "").replace(" ", "") if h1 else "Unknown"
            
            # 2. 获取语言
            lang_span = article.select_one('span[itemprop="programmingLanguage"]')
            lang = lang_span.text.strip() if lang_span else "Other"
            
            # 3. 获取Star数 (清洗数据，去掉逗号)
            star_a = article.select_one('a.Link--muted')
            stars = int(star_a.text.strip().replace(',', '')) if star_a else 0
            
            repos.append({"name": name, "language": lang, "stars": stars, "date": DATE_STR})
            
        # 保存为JSON文件 
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(repos, f, ensure_ascii=False, indent=4)
            
        print(f"[INFO] 成功采集 {len(repos)} 个项目到 {FILE_PATH}")
        
    except Exception as e:
        print(f"[ERROR] 采集失败: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_data()