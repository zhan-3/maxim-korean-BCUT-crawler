from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import requests
import os
import time
import re

# ---------------------- 核心配置（可按需调整） ----------------------
# 目标站点
TARGET_URL = "https://bcut.maximkorea.net/##"
# 保存路径
SAVE_FOLDER = "firefox_145_practice_jpg"
CRAWLED_URLS_FILE = "crawled_urls.txt"  # 断点续爬文件
# 驱动路径
GECKO_DRIVER_PATH = "C:\\geckodriver\\geckodriver.exe"
# 选择器
LOAD_MORE_BTN_SELECTOR = "button.view-more"
# Firefox 145专属配置
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"
# 爬取限制（突破78张核心配置）
TARGET_TOTAL = 200  # 目标爬取总数
NO_NEW_URLS_THRESHOLD = 3  # 连续3次无新链接终止
# 反爬间隔（延长所有操作间隔）
KEY_DELAY = 4         # PageDown按键后等待
LOAD_BTN_DELAY = 5    # 点击按钮后等待
DOWNLOAD_DELAY = 3    # 下载间隔
INIT_LOAD_DELAY = 6   # 页面初始加载等待
# ----------------------------------------------------------------------

def init_firefox_145():
    """初始化Firefox 145.0.2（反爬+稳定适配）"""
    firefox_options = Options()
    # 核心反爬配置
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("browser.execute_script", True)
    firefox_options.set_preference("browser.cache.disk.enable", True)
    # 网络适配
    firefox_options.set_preference("network.proxy.type", 0)
    firefox_options.set_preference("security.ssl.enable_ocsp_stapling", False)
    firefox_options.set_preference("security.ssl.override_security_restrictions", True)
    # 性能优化
    firefox_options.add_argument(f"user-agent={USER_AGENT}")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-extensions")
    firefox_options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(
        executable_path=GECKO_DRIVER_PATH,
        log_path=os.devnull
    )
    driver = webdriver.Firefox(service=service, options=firefox_options)
    driver.implicitly_wait(15)  # 延长元素等待
    driver.set_page_load_timeout(30)
    return driver

def trigger_page_down(driver, extend_count):
    """PageDown按键触发加载（反爬优化）"""
    print(f"\n📌 第{extend_count+1}次触发PageDown加载")
    try:
        # 随机小延迟，模拟人工操作
        time.sleep(1 + extend_count % 2)
        body_elem = driver.find_element(By.TAG_NAME, "body")
        body_elem.click()
        
        # 模拟人工不规则按键
        press_times = 2 if extend_count % 3 == 0 else 1
        for _ in range(press_times):
            body_elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(KEY_DELAY)
        return True
    except Exception as e:
        print(f"⚠️ PageDown触发失败：{str(e)[:50]}")
        return False

def get_jpg_urls(driver):
    """提取JPG链接（模糊匹配，避免漏抓）"""
    img_urls = []
    try:
        # 先滚动触发渲染
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 模糊匹配所有含jpg的图片（兼容data-src/src）
        img_elems = driver.find_elements(By.XPATH, 
            "//img[contains(@src, '.jpg') or contains(@data-src, '.jpg')]")
        
        for elem in img_elems:
            # 优先取data-src（动态加载），再取src
            img_url = elem.get_attribute("data-src") or elem.get_attribute("src")
            if not img_url or ".jpg" not in img_url:
                continue
            
            # 清理URL参数，避免重复
            clean_url = re.sub(r'\?.*$', '', img_url)
            # 过滤无效链接
            if clean_url.startswith("http") and clean_url not in img_urls:
                img_urls.append(clean_url)
                if len(img_urls) % 10 == 0:  # 每提取10个打印一次，减少日志
                    print(f"🔍 已提取{len(img_urls)}个JPG链接（最新：{clean_url[:50]}...）")
                    
    except Exception as e:
        print(f"⚠️ 提取链接出错：{str(e)[:60]}")
    return img_urls

def download_jpg(img_url, save_path):
    """下载JPG（防盗链+稳定分块）"""
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": TARGET_URL,
        "Accept": "image/jpeg,image/png,*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Sec-Fetch-Dest": "image",  # 模拟浏览器图片请求
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site"
    }
    try:
        response = requests.get(
            img_url,
            headers=headers,
            timeout=25,
            verify=False,
            stream=True,
            allow_redirects=True  # 允许重定向，提高成功率
        )
        response.raise_for_status()
        
        # 分块写入，适配大图片
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=2048):
                if chunk:
                    f.write(chunk)
        
        print(f"✅ 下载成功：{os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"❌ 下载失败：{img_url[:60]} | {str(e)[:40]}")
        return False

# 断点续爬相关函数
def save_crawled_urls(urls):
    """保存已爬链接，避免重复"""
    with open(CRAWLED_URLS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    print(f"\n💾 已保存{len(urls)}个已爬链接到：{CRAWLED_URLS_FILE}")

def load_crawled_urls():
    """加载历史爬取链接"""
    if os.path.exists(CRAWLED_URLS_FILE):
        with open(CRAWLED_URLS_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and line.startswith("http")]
        print(f"📜 加载历史爬取链接：{len(urls)}个")
        return urls
    return []

def crawl_firefox_145():
    """完整爬取逻辑（突破78张限制+断点续爬）"""
    # 1. 前置检查
    if not os.path.exists(GECKO_DRIVER_PATH):
        print(f"❌ GeckoDriver路径不存在：{GECKO_DRIVER_PATH}")
        return
    
    # 2. 加载历史链接（断点续爬）
    all_urls = load_crawled_urls()
    success_count = len([f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")]) if os.path.exists(SAVE_FOLDER) else 0
    print(f"📊 初始状态：已爬{len(all_urls)}个链接 | 已下载{success_count}张图片")
    
    # 3. 初始化浏览器
    driver = None
    try:
        driver = init_firefox_145()
    except Exception as e:
        print(f"❌ 启动Firefox 145失败：{str(e)[:60]}")
        print("   检查：1.GeckoDriver版本 2.Firefox是否安装 3.以管理员运行")
        return
    
    # 4. 访问页面
    try:
        driver.get(TARGET_URL)
        time.sleep(INIT_LOAD_DELAY)  # 延长初始加载
        print(f"✅ 成功访问页面：{TARGET_URL}")
    except Exception as e:
        print(f"❌ 访问页面失败：{str(e)[:60]}")
        driver.quit()
        return
    
    # 5. 创建保存文件夹
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    # 6. 核心爬取逻辑（突破78张限制）
    extend_count = 0
    no_new_count = 0
    restart_count = 0  # 浏览器重启计数
    
    print(f"\n🚀 开始爬取（目标{TARGET_TOTAL}张，连续{NO_NEW_URLS_THRESHOLD}次无新链接终止）")
    print("-" * 80)
    
    while len(all_urls) < TARGET_TOTAL and no_new_count < NO_NEW_URLS_THRESHOLD:
        # 触发PageDown加载
        trigger_page_down(driver, extend_count)
        extend_count += 1
        
        # 提取链接
        current_urls = get_jpg_urls(driver)
        # 筛选新增链接
        new_urls = [u for u in current_urls if u not in all_urls]
        
        # 判定无新链接
        if len(new_urls) == 0:
            no_new_count += 1
            print(f"\n⚠️ 第{no_new_count}次无新链接（累计已爬{len(all_urls)}个）")
            
            # 尝试点击MORE按钮最后一次
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY)
                print("🔄 尝试点击MORE按钮加载最后一次")
            except:
                pass
            
            # 浏览器重启策略（突破会话限制）
            if no_new_count >= 2 and restart_count < 2:
                print("\n🔄 尝试重启浏览器突破会话限制...")
                driver.quit()
                time.sleep(10)  # 重启间隔
                driver = init_firefox_145()
                driver.get(TARGET_URL)
                time.sleep(INIT_LOAD_DELAY)
                restart_count += 1
                no_new_count = 0  # 重置无新链接计数
                print(f"✅ 浏览器重启完成（第{restart_count}次）")
        else:
            no_new_count = 0  # 重置无新链接计数
            # 合并新链接
            all_urls.extend(new_urls)
            # 去重（防止重复）
            all_urls = list(dict.fromkeys(all_urls))
            # 保存进度
            save_crawled_urls(all_urls)
            
            print(f"\n🔄 本次新增{len(new_urls)}个链接 | 累计{len(all_urls)}个（目标{TARGET_TOTAL}个）")
            
            # 尝试点击MORE按钮加载更多
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY)
            except:
                print("ℹ️ 未找到MORE按钮，仅使用PageDown加载")
        
        # 达到目标数量提前终止
        if len(all_urls) >= TARGET_TOTAL:
            print(f"\n🎉 已达到目标爬取数量：{TARGET_TOTAL}个链接")
            break
    
    # 7. 批量下载（断点续爬，跳过已下载）
    print("\n" + "-"*80)
    print(f"📥 开始下载图片（共{len(all_urls)}个链接）")
    print("-"*80)
    
    # 过滤已下载的链接
    downloaded_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")] if os.path.exists(SAVE_FOLDER) else []
    to_download = []
    for url in all_urls:
        url_filename = os.path.basename(url)
        if not any(url_filename in f for f in downloaded_files):
            to_download.append(url)
    
    print(f"📊 需下载：{len(to_download)}张 | 已下载：{len(all_urls)-len(to_download)}张")
    
    if to_download:
        for idx, url in enumerate(to_download):
            # 生成安全的文件名（避免特殊字符）
            safe_filename = re.sub(r'[^\w\.]', '_', os.path.basename(url))
            img_name = f"firefox145_{len(all_urls)-len(to_download)+idx+1}_{safe_filename}"
            save_path = os.path.join(SAVE_FOLDER, img_name)
            
            if download_jpg(url, save_path):
                success_count += 1
            
            # 下载间隔，反爬
            time.sleep(DOWNLOAD_DELAY)
            
            # 每下载10张保存一次进度
            if (idx+1) % 10 == 0:
                print(f"\n📌 下载进度：{idx+1}/{len(to_download)} | 累计成功：{success_count}张")
    
    # 8. 收尾
    driver.quit()
    save_crawled_urls(all_urls)  # 最后保存一次进度
    
    print("\n" + "="*80)
    print("🎉 爬取任务完成！")
    print(f"📊 最终统计：")
    print(f"   • 累计提取链接：{len(all_urls)}个")
    print(f"   • 成功下载图片：{success_count}张")
    print(f"   • 图片保存路径：{os.path.abspath(SAVE_FOLDER)}")
    print(f"   • 断点续爬文件：{os.path.abspath(CRAWLED_URLS_FILE)}")
    print("="*80)

if __name__ == "__main__":
    # 忽略SSL警告
    requests.packages.urllib3.disable_warnings()
    # 执行爬取
    crawl_firefox_145()