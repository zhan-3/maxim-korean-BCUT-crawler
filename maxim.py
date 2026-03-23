from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import os
import time
import re

# ---------------------- 基础配置（练习用） ----------------------
TARGET_URL = "https://bcut.maximkorea.net/##"  # 替换为实际练习页面URL
SAVE_FOLDER = "practice_jpg_images"        # 图片保存文件夹
LOAD_MORE_BTN_SELECTOR = "button.view-more"# 加载更多按钮选择器
IMG_SELECTOR = "div.work-cell img.width-100p"  # jpg图片选择器
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# --------------------------------------------------------------

def init_browser():
    """初始化浏览器（绕过前端限制）"""
    # 配置国内镜像源下载驱动
    os.environ['WDM_MIRROR'] = 'cn'
    os.environ['WDM_LOG'] = '0'
    
    # Chrome配置（禁用反爬检测）
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # 可选：禁用图片自动加载（加快页面加载，最后下载时再请求）
    # chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    
    # 初始化驱动
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)  # 等待元素加载
    return driver

def get_all_jpg_urls(driver):
    """提取页面中所有jpg图片链接"""
    img_urls = []
    # 定位所有图片元素
    img_elems = driver.find_elements(By.CSS_SELECTOR, IMG_SELECTOR)
    for elem in img_elems:
        img_url = elem.get_attribute("src")
        # 过滤仅保留jpg格式
        if img_url and img_url.endswith(".jpg"):
            # 清理URL中的token参数（避免重复）
            clean_url = re.sub(r'\?.*$', '', img_url)
            if clean_url not in img_urls:
                img_urls.append(clean_url)
    return img_urls

def download_jpg(img_url, save_path):
    """下载单张jpg图片（带防盗链）"""
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": TARGET_URL  # 适配网站防盗链
    }
    try:
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()  # 检测HTTP错误
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"✅ 下载成功：{os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"❌ 下载失败：{img_url} | {str(e)[:50]}")
        return False

def crawl_jpg_practice():
    # 1. 初始化浏览器
    driver = init_browser()
    driver.get(TARGET_URL)
    time.sleep(3)  # 等待页面加载
    
    # 2. 创建保存文件夹
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    # 3. 循环加载更多+提取图片
    all_img_urls = []
    load_count = 0
    max_load = 5  # 练习用：最多加载5次（避免爬取过多）
    
    while load_count < max_load:
        # 提取当前页面的jpg链接
        current_img_urls = get_all_jpg_urls(driver)
        new_urls = [url for url in current_img_urls if url not in all_img_urls]
        all_img_urls.extend(new_urls)
        
        print(f"\n第{load_count+1}次加载：")
        print(f"  - 新增jpg链接：{len(new_urls)}个")
        print(f"  - 累计jpg链接：{len(all_img_urls)}个")
        
        # 尝试点击“MORE”按钮加载更多
        try:
            load_more_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
            load_more_btn.click()
            time.sleep(2)  # 等待新内容加载
            load_count += 1
        except:
            print("⚠️ 无更多加载按钮，终止加载")
            break
    
    # 4. 批量下载所有jpg图片
    print(f"\n开始下载{len(all_img_urls)}张jpg图片...")
    success_count = 0
    for idx, img_url in enumerate(all_img_urls):
        # 生成保存文件名（用索引+图片名）
        img_name = f"practice_{idx+1}_{os.path.basename(img_url)}"
        save_path = os.path.join(SAVE_FOLDER, img_name)
        if download_jpg(img_url, save_path):
            success_count += 1
    
    # 5. 收尾
    driver.quit()
    print(f"\n📊 练习完成：")
    print(f"  - 累计提取jpg链接：{len(all_img_urls)}个")
    print(f"  - 成功下载：{success_count}张")
    print(f"  - 保存路径：{os.path.abspath(SAVE_FOLDER)}")

if __name__ == "__main__":
    # 安装依赖（首次运行前执行）
    # pip install selenium webdriver-manager requests
    crawl_jpg_practice()