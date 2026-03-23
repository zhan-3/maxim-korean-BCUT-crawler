from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import requests
import os
import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ---------------------- 核心配置（超时优化） ----------------------
TARGET_URL = "https://bcut.maximkorea.net/##"
SAVE_FOLDER = "firefox_145_practice_jpg"
CRAWLED_URLS_FILE = "crawled_urls.txt"
GECKO_DRIVER_PATH = "C:\\geckodriver\\geckodriver.exe"
LOAD_MORE_BTN_SELECTOR = "button.view-more"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"

# 关键优化：延长超时阈值
TARGET_TOTAL = 50
NO_NEW_URLS_THRESHOLD = 3
KEY_DELAY = 4
LOAD_BTN_DELAY = 5
DOWNLOAD_DELAY = 1
INIT_LOAD_DELAY = 15  # 从6秒延长到15秒，给海外站点足够加载时间
PAGE_LOAD_TIMEOUT = 60  # 页面加载超时从30秒延长到60秒
IMPLICITLY_WAIT = 20    # 元素等待从15秒延长到20秒
RETRY_TIMES = 3         # 页面访问失败自动重试次数

# 多线程配置
THREAD_NUM = 5
download_success_count = 0
count_lock = Lock()

# ---------------------- 多线程下载模块 ----------------------
def thread_download_task(url, save_path):
    global download_success_count
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": TARGET_URL,
        "Accept": "image/jpeg,image/png,*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        # 新增：适配海外站点的请求头
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache"
    }
    try:
        # 下载超时也延长
        response = requests.get(
            url=url,
            headers=headers,
            timeout=30,  # 下载超时从25秒延长到30秒
            verify=False,
            stream=True,
            allow_redirects=True
        )
        response.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=2048):
                if chunk:
                    f.write(chunk)
        with count_lock:
            download_success_count += 1
        print(f"✅ 线程{threading.current_thread().name}：下载成功 {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"❌ 线程{threading.current_thread().name}：下载失败 {url[:60]} | {str(e)[:40]}")
        return False

def multi_thread_download(to_download, save_folder):
    global download_success_count
    download_success_count = 0
    print(f"\n🚀 启动多线程下载（线程数：{THREAD_NUM}，待下载：{len(to_download)}张）")
    
    with ThreadPoolExecutor(max_workers=THREAD_NUM, thread_name_prefix="Download") as executor:
        future_to_url = {}
        for idx, url in enumerate(to_download):
            safe_filename = re.sub(r'[^\w\.]', '_', os.path.basename(url))
            img_name = f"firefox145_{idx+1}_{safe_filename}"
            save_path = os.path.join(save_folder, img_name)
            future = executor.submit(thread_download_task, url, save_path)
            future_to_url[future] = url
            time.sleep(DOWNLOAD_DELAY)
        
        for future in as_completed(future_to_url):
            try:
                future.result()
            except Exception as e:
                print(f"⚠️ 线程任务异常：{str(e)[:50]}")
    
    print(f"\n📊 多线程下载完成：成功{download_success_count}张 | 失败{len(to_download)-download_success_count}张")
    return download_success_count

# ---------------------- Firefox初始化（网络优化） ----------------------
def init_firefox_145():
    """初始化Firefox（延长超时+海外站点适配）"""
    firefox_options = Options()
    # 核心反爬
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("browser.execute_script", True)
    firefox_options.set_preference("browser.cache.disk.enable", True)
    # 网络适配（关键优化）
    firefox_options.set_preference("network.proxy.type", 0)
    firefox_options.set_preference("security.ssl.enable_ocsp_stapling", False)
    firefox_options.set_preference("security.ssl.override_security_restrictions", True)
    # 延长网络超时
    firefox_options.set_preference("network.http.connection-timeout", 60)
    firefox_options.set_preference("network.http.request.timeout", 60)
    firefox_options.set_preference("network.http.response.timeout", 60)
    # 海外站点适配
    firefox_options.set_preference("intl.accept_languages", "ko-KR,ko,en-US,en")
    firefox_options.set_preference("browser.cache.memory.enable", False)
    # 性能优化
    firefox_options.add_argument(f"user-agent={USER_AGENT}")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-extensions")
    firefox_options.add_argument("--disable-blink-features=AutomationControlled")
    # 禁用图片自动加载（先加载页面结构，再触发渲染）
    firefox_options.set_preference("permissions.default.image", 2)
    
    service = Service(
        executable_path=GECKO_DRIVER_PATH,
        log_path=os.devnull
    )
    driver = webdriver.Firefox(service=service, options=firefox_options)
    driver.implicitly_wait(IMPLICITLY_WAIT)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    # 新增：禁用页面加载完成后的超时
    driver.set_script_timeout(PAGE_LOAD_TIMEOUT)
    return driver

# ---------------------- 页面访问重试函数 ----------------------
def access_page_with_retry(driver, url, retry_times=RETRY_TIMES):
    """页面访问失败自动重试"""
    for i in range(retry_times):
        try:
            driver.get(url)
            # 等待页面核心元素加载（而非仅等待页面加载完成）
            driver.find_element(By.TAG_NAME, "body")
            time.sleep(INIT_LOAD_DELAY)
            print(f"✅ 页面访问成功（第{i+1}次尝试）")
            return True
        except Exception as e:
            print(f"❌ 第{i+1}次访问页面失败：{str(e)[:60]}")
            if i < retry_times - 1:
                print(f"🔄 等待5秒后重试...")
                time.sleep(5)
                # 重启浏览器重试
                driver.quit()
                driver = init_firefox_145()
    return False

def trigger_page_down(driver, extend_count):
    print(f"\n📌 第{extend_count+1}次触发PageDown加载")
    try:
        time.sleep(1 + extend_count % 2)
        body_elem = driver.find_element(By.TAG_NAME, "body")
        body_elem.click()
        press_times = 2 if extend_count % 3 == 0 else 1
        for _ in range(press_times):
            body_elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
        # 重新启用图片加载（触发渲染）
        driver.execute_script("""
            document.querySelectorAll('img').forEach(img => {
                img.src = img.src;
            });
        """)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(KEY_DELAY)
        return True
    except Exception as e:
        print(f"⚠️ PageDown触发失败：{str(e)[:50]}")
        return False

def get_jpg_urls(driver):
    img_urls = []
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        img_elems = driver.find_elements(By.XPATH, 
            "//img[contains(@src, '.jpg') or contains(@data-src, '.jpg')]")
        
        for elem in img_elems:
            img_url = elem.get_attribute("data-src") or elem.get_attribute("src")
            if not img_url or ".jpg" not in img_url:
                continue
            clean_url = re.sub(r'\?.*$', '', img_url)
            if clean_url.startswith("http") and clean_url not in img_urls:
                img_urls.append(clean_url)
                if len(img_urls) % 10 == 0:
                    print(f"🔍 已提取{len(img_urls)}个JPG链接（最新：{clean_url[:50]}...）")
    except Exception as e:
        print(f"⚠️ 提取链接出错：{str(e)[:60]}")
    return img_urls

# 断点续爬函数
def save_crawled_urls(urls):
    with open(CRAWLED_URLS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    print(f"\n💾 已保存{len(urls)}个已爬链接到：{CRAWLED_URLS_FILE}")

def load_crawled_urls():
    if os.path.exists(CRAWLED_URLS_FILE):
        with open(CRAWLED_URLS_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and line.startswith("http")]
        print(f"📜 加载历史爬取链接：{len(urls)}个")
        return urls
    return []

# ---------------------- 主逻辑（新增重试） ----------------------
def crawl_firefox_145():
    # 1. 前置检查
    if not os.path.exists(GECKO_DRIVER_PATH):
        print(f"❌ GeckoDriver路径不存在：{GECKO_DRIVER_PATH}")
        return
    
    # 2. 加载历史链接
    all_urls = load_crawled_urls()
    historical_success = len([f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")]) if os.path.exists(SAVE_FOLDER) else 0
    print(f"📊 初始状态：已爬{len(all_urls)}个链接 | 历史下载{historical_success}张图片")
    
    # 3. 初始化浏览器+重试访问
    driver = init_firefox_145()
    access_success = access_page_with_retry(driver, TARGET_URL)
    if not access_success:
        print(f"❌ 经过{RETRY_TIMES}次重试仍无法访问页面，任务终止")
        driver.quit()
        return
    
    # 4. 创建文件夹
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    # 5. 核心爬取逻辑
    extend_count = 0
    no_new_count = 0
    restart_count = 0
    
    print(f"\n🚀 开始爬取（目标{TARGET_TOTAL}张，线程数：{THREAD_NUM}）")
    print("-" * 80)
    
    while len(all_urls) < TARGET_TOTAL and no_new_count < NO_NEW_URLS_THRESHOLD:
        trigger_page_down(driver, extend_count)
        extend_count += 1
        
        current_urls = get_jpg_urls(driver)
        new_urls = [u for u in current_urls if u not in all_urls]
        
        if len(new_urls) == 0:
            no_new_count += 1
            print(f"\n⚠️ 第{no_new_count}次无新链接（累计已爬{len(all_urls)}个）")
            
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY)
            except:
                pass
            
            if no_new_count >= 2 and restart_count < 2:
                print("\n🔄 重启浏览器...")
                driver.quit()
                driver = init_firefox_145()
                access_page_with_retry(driver, TARGET_URL)
                restart_count += 1
                no_new_count = 0
        else:
            no_new_count = 0
            all_urls.extend(new_urls)
            all_urls = list(dict.fromkeys(all_urls))
            save_crawled_urls(all_urls)
            print(f"\n🔄 本次新增{len(new_urls)}个链接 | 累计{len(all_urls)}个")
            
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY)
            except:
                print("ℹ️ 未找到MORE按钮")
        
        if len(all_urls) >= TARGET_TOTAL:
            print(f"\n🎉 已达目标数量：{TARGET_TOTAL}个链接")
            break
    
    # 6. 多线程下载
    print("\n" + "-"*80)
    print(f"📥 准备多线程下载（共{len(all_urls)}个链接）")
    print("-"*80)
    
    downloaded_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")] if os.path.exists(SAVE_FOLDER) else []
    to_download = []
    for url in all_urls:
        url_filename = os.path.basename(url)
        if not any(url_filename in f for f in downloaded_files):
            to_download.append(url)
    
    print(f"📊 需下载：{len(to_download)}张 | 已下载：{len(all_urls)-len(to_download)}张")
    
    if to_download:
        current_success = multi_thread_download(to_download, SAVE_FOLDER)
        total_success = historical_success + current_success
    else:
        total_success = historical_success
        print("ℹ️ 无新增图片需要下载")
    
    # 7. 收尾
    driver.quit()
    save_crawled_urls(all_urls)
    
    print("\n" + "="*80)
    print("🎉 爬取任务完成！")
    print(f"📊 最终统计：")
    print(f"   • 累计提取链接：{len(all_urls)}个")
    print(f"   • 累计成功下载：{total_success}张")
    print(f"   • 多线程数：{THREAD_NUM}")
    print(f"   • 图片保存路径：{os.path.abspath(SAVE_FOLDER)}")
    print("="*80)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    crawl_firefox_145()