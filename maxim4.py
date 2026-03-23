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
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import shutil

# ---------------------- 核心配置（优化版） ----------------------
TARGET_URL = "https://bcut.maximkorea.net/##"
SAVE_FOLDER = "firefox_145_practice_jpg"
CRAWLED_URLS_FILE = "crawled_urls.txt"
GECKO_DRIVER_PATH = "C:\\geckodriver\\geckodriver.exe"
LOAD_MORE_BTN_SELECTOR = "button.view-more"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0"

# 关键优化：随机化延迟（避免固定频率被反爬）
TARGET_TOTAL = 100
NO_NEW_URLS_THRESHOLD = 5  # 放宽无新链接阈值
KEY_DELAY = lambda: random.uniform(2, 5)        # 随机2-5秒
LOAD_BTN_DELAY = lambda: random.uniform(3, 7)   # 随机3-7秒
DOWNLOAD_DELAY = lambda: random.uniform(0.5, 2) # 随机0.5-2秒
INIT_LOAD_DELAY = lambda: random.uniform(12, 20)# 随机12-20秒
PAGE_LOAD_TIMEOUT = 60  # 页面加载超时
IMPLICITLY_WAIT = 20    # 元素等待时间
RETRY_TIMES = 3         # 页面访问失败重试次数
THREAD_NUM = 3          # 降低线程数减少拦截（从5改为3）
DOWNLOAD_RETRY_TIMES = 2# 下载重试次数
BATCH_SIZE = 20         # 分批次下载大小

# 多线程计数
download_success_count = 0
count_lock = Lock()

# ---------------------- 多线程下载模块（优化版） ----------------------
def thread_download_task(url, save_path):
    global download_success_count
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": TARGET_URL,
        "Accept": "image/jpeg,image/png,image/jpg,*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache"
    }
    
    # 下载重试逻辑
    for retry in range(DOWNLOAD_RETRY_TIMES):
        try:
            response = requests.get(
                url=url,
                headers=headers,
                timeout=30,
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
            if retry < DOWNLOAD_RETRY_TIMES - 1:
                sleep_time = random.uniform(3, 5)
                print(f"🔄 第{retry+1}次重试下载 {url[:60]}（等待{sleep_time:.1f}秒）")
                time.sleep(sleep_time)
                continue
            print(f"❌ 线程{threading.current_thread().name}：下载失败 {url[:60]} | {str(e)[:40]}")
            return False

def multi_thread_download(to_download, save_folder):
    global download_success_count
    download_success_count = 0
    print(f"\n🚀 启动多线程下载（线程数：{THREAD_NUM}，待下载：{len(to_download)}张）")
    
    # 分批次下载（避免一次性请求过多）
    batches = [to_download[i:i+BATCH_SIZE] for i in range(0, len(to_download), BATCH_SIZE)]
    
    with ThreadPoolExecutor(max_workers=THREAD_NUM, thread_name_prefix="Download") as executor:
        for batch_idx, batch in enumerate(batches):
            print(f"\n📦 处理第{batch_idx+1}批（共{len(batches)}批，本批{len(batch)}张）")
            future_to_url = {}
            for idx, url in enumerate(batch):
                safe_filename = re.sub(r'[^\w\.]', '_', os.path.basename(url))
                img_name = f"firefox145_{batch_idx*BATCH_SIZE + idx+1}_{safe_filename}"
                save_path = os.path.join(save_folder, img_name)
                future = executor.submit(thread_download_task, url, save_path)
                future_to_url[future] = url
                time.sleep(DOWNLOAD_DELAY())  # 随机延迟
            
            # 处理批次结果
            for future in as_completed(future_to_url):
                try:
                    future.result()
                except Exception as e:
                    print(f"⚠️ 线程任务异常：{str(e)[:50]}")
            
            # 批次间随机休息（关键：避免连续请求）
            if batch_idx < len(batches)-1:
                sleep_time = random.uniform(5, 10)
                print(f"\n⏳ 批次间休息{sleep_time:.1f}秒...")
                time.sleep(sleep_time)
    
    print(f"\n📊 多线程下载完成：成功{download_success_count}张 | 失败{len(to_download)-download_success_count}张")
    return download_success_count

# ---------------------- Firefox初始化（反反爬优化） ----------------------
def init_firefox_145():
    """初始化Firefox（随机化特征+海外站点适配）"""
    firefox_options = Options()
    
    # 核心反爬
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("browser.execute_script", True)
    firefox_options.set_preference("browser.cache.disk.enable", True)
    
    # 网络适配（延长超时）
    firefox_options.set_preference("network.proxy.type", 0)
    firefox_options.set_preference("security.ssl.enable_ocsp_stapling", False)
    firefox_options.set_preference("security.ssl.override_security_restrictions", True)
    firefox_options.set_preference("network.http.connection-timeout", 60)
    firefox_options.set_preference("network.http.request.timeout", 60)
    firefox_options.set_preference("network.http.response.timeout", 60)
    
    # 海外站点适配
    firefox_options.set_preference("intl.accept_languages", "ko-KR,ko,en-US,en")
    firefox_options.set_preference("browser.cache.memory.enable", False)
    
    # 随机化浏览器特征
    firefox_options.set_preference("browser.startup.homepage_override.mstone", "145.0")
    firefox_options.set_preference("browser.version", "145.0")
    firefox_options.set_preference("general.useragent.override", USER_AGENT)
    
    # 清除浏览器指纹
    firefox_options.set_preference("privacy.resistFingerprinting", True)
    firefox_options.set_preference("browser.canvas.msaa.enabled", False)
    
    # 启用图片自动加载（避免渲染失败）
    firefox_options.set_preference("permissions.default.image", 1)
    
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
    driver.implicitly_wait(IMPLICITLY_WAIT)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.set_script_timeout(PAGE_LOAD_TIMEOUT)
    
    # 随机窗口大小（模拟真人）
    driver.set_window_size(random.randint(1200, 1920), random.randint(800, 1080))
    
    return driver

# ---------------------- 页面访问重试函数 ----------------------
def access_page_with_retry(driver, url, retry_times=RETRY_TIMES):
    """页面访问失败自动重试"""
    for i in range(retry_times):
        try:
            driver.get(url)
            # 等待页面核心元素加载
            driver.find_element(By.TAG_NAME, "body")
            time.sleep(INIT_LOAD_DELAY())
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

# ---------------------- 滚动触发函数（随机化操作） ----------------------
def trigger_page_down(driver, extend_count):
    print(f"\n📌 第{extend_count+1}次触发PageDown加载")
    try:
        # 随机滚动位置（避免每次滚到底部）
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        random_scroll = random.randint(int(scroll_height*0.7), int(scroll_height*0.95))
        driver.execute_script(f"window.scrollTo(0, {random_scroll});")
        time.sleep(random.uniform(1, 3))
        
        body_elem = driver.find_element(By.TAG_NAME, "body")
        body_elem.click()
        
        # 随机PageDown次数（1-3次）
        press_times = random.randint(1, 3)
        for _ in range(press_times):
            body_elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(0.8, 1.5))
        
        # 强制渲染所有图片（覆盖更多字段）
        driver.execute_script("""
            document.querySelectorAll('img').forEach(img => {
                if(img.dataset.src) img.src = img.dataset.src;
                if(img.dataset.original) img.src = img.dataset.original;
                if(img.dataset.image) img.src = img.dataset.image;
                img.loading = 'eager';
            });
        """)
        
        # 随机回滚一点（模拟真人操作）
        driver.execute_script(f"window.scrollTo(0, {random.randint(int(scroll_height*0.5), int(scroll_height*0.8))});")
        time.sleep(KEY_DELAY())
        return True
    except Exception as e:
        print(f"⚠️ PageDown触发失败：{str(e)[:50]}")
        return False

# ---------------------- 链接提取函数（优化版） ----------------------
def get_jpg_urls(driver):
    img_urls = []
    try:
        # 多次滚动+等待，确保所有图片元素加载
        for _ in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
        
        # 扩展图片后缀匹配（支持jpg/jpeg/JPG/JPEG）
        img_elems = driver.find_elements(By.XPATH, 
            "//img[contains(@src, '.jpg') or contains(@src, '.jpeg') or "
            "contains(@data-src, '.jpg') or contains(@data-src, '.jpeg')]")
        
        for elem in img_elems:
            # 优先提取真实链接（覆盖更多字段）
            img_url = (
                elem.get_attribute("data-src") or
                elem.get_attribute("data-original") or
                elem.get_attribute("src") or
                elem.get_attribute("data-image")
            )
            if not img_url:
                continue
            
            # 统一转为小写，避免大小写问题
            img_url_lower = img_url.lower()
            if ".jpg" not in img_url_lower and ".jpeg" not in img_url_lower:
                continue
            
            # 清理参数但保留核心链接
            clean_url = re.sub(r'\?.*$', '', img_url).strip()
            if clean_url.startswith(("http://", "https://")) and clean_url not in img_urls:
                img_urls.append(clean_url)
                if len(img_urls) % 10 == 0:
                    print(f"🔍 已提取{len(img_urls)}个图片链接（最新：{clean_url[:50]}...）")
    except Exception as e:
        print(f"⚠️ 提取链接出错：{str(e)[:60]}")
    return img_urls

# ---------------------- 断点续爬函数 ----------------------
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

# ---------------------- 主逻辑（优化版） ----------------------
def crawl_firefox_145():
    # 1. 前置检查
    if not os.path.exists(GECKO_DRIVER_PATH):
        print(f"❌ GeckoDriver路径不存在：{GECKO_DRIVER_PATH}")
        return
    
    # 2. 加载历史链接
    all_urls = load_crawled_urls()
    historical_success = len([f for f in os.listdir(SAVE_FOLDER) if f.lower().endswith((".jpg", ".jpeg"))]) if os.path.exists(SAVE_FOLDER) else 0
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
            
            # 尝试点击加载更多按钮
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY())
            except:
                pass
            
            # 重启浏览器（清理缓存）
            if no_new_count >= 2 and restart_count < 3:
                print("\n🔄 重启浏览器（清理缓存）...")
                driver.quit()
                # 清理Firefox缓存
                try:
                    shutil.rmtree(driver.profile.path, ignore_errors=True)
                except:
                    pass
                driver = init_firefox_145()
                access_page_with_retry(driver, TARGET_URL)
                restart_count += 1
                no_new_count = 0
        else:
            no_new_count = 0
            all_urls.extend(new_urls)
            all_urls = list(dict.fromkeys(all_urls))  # 去重
            save_crawled_urls(all_urls)
            print(f"\n🔄 本次新增{len(new_urls)}个链接 | 累计{len(all_urls)}个")
            
            # 尝试点击加载更多按钮
            try:
                load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
                driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
                time.sleep(2)
                load_btn.click()
                time.sleep(LOAD_BTN_DELAY())
            except:
                print("ℹ️ 未找到MORE按钮")
        
        if len(all_urls) >= TARGET_TOTAL:
            print(f"\n🎉 已达目标数量：{TARGET_TOTAL}个链接")
            break
    
    # 6. 多线程下载
    print("\n" + "-"*80)
    print(f"📥 准备多线程下载（共{len(all_urls)}个链接）")
    print("-"*80)
    
    # 过滤已下载的图片
    downloaded_files = [f for f in os.listdir(SAVE_FOLDER) if f.lower().endswith((".jpg", ".jpeg"))] if os.path.exists(SAVE_FOLDER) else []
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
    # 禁用requests警告
    requests.packages.urllib3.disable_warnings()
    # 启动主程序
    crawl_firefox_145()