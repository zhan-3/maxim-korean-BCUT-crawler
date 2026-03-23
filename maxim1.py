from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import requests
import os
import time
import re

# ---------------------- 已适配你的GeckoDriver路径 ----------------------
TARGET_URL = "https://bcut.maximkorea.net/##"  # 替换为练习页面URL
SAVE_FOLDER = "firefox_145_practice_jpg"   # 图片保存文件夹
# 已修改为你的实际路径：C:\geckodriver\geckodriver.exe
GECKO_DRIVER_PATH = "C:\\geckodriver\\geckodriver.exe"
LOAD_MORE_BTN_SELECTOR = "button.view-more"# 加载更多按钮选择器
IMG_SELECTOR = "div.work-cell img.width-100p"  # jpg图片选择器
# Firefox 145.0.2专属User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0"
# ----------------------------------------------------------------------

def init_firefox_145():
    """初始化Firefox 145.0.2（版本精准适配）"""
    firefox_options = Options()
    # 1. 核心：Firefox 145反爬屏蔽
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("browser.execute_script", True)
    firefox_options.set_preference("browser.cache.disk.enable", True)
    # 2. 网络适配（解决国内连接问题）
    firefox_options.set_preference("network.proxy.type", 0)  # 直连（无需代理）
    firefox_options.set_preference("security.ssl.enable_ocsp_stapling", False)
    firefox_options.set_preference("security.ssl.override_security_restrictions", True)
    # 3. 性能优化
    firefox_options.add_argument(f"user-agent={USER_AGENT}")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-extensions")
    
    # 手动指定你的GeckoDriver路径
    service = Service(
        executable_path=GECKO_DRIVER_PATH,
        log_path=os.devnull  # 关闭驱动日志（避免冗余输出）
    )
    driver = webdriver.Firefox(service=service, options=firefox_options)
    driver.implicitly_wait(12)  # 延长等待时间（适配145版本加载特性）
    return driver

def get_jpg_urls(driver):
    img_urls = []
    try:
        # 步骤1：强制滚动页面，触发动态元素渲染（解决加载问题）
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # 等待JS渲染图片元素
        
        # 步骤2：精准匹配你的<img>元素（div.work-cell + img.width-100p）
        # 先定位所有父级div，再找内部的img，避免选择器失效
        work_divs = driver.find_elements(By.CSS_SELECTOR, "div.work-cell")
        for div in work_divs:
            # 在每个work-cell里找width-100p的img
            img_elem = div.find_element(By.CSS_SELECTOR, "img.width-100p")
            
            # 步骤3：提取主链接（src属性），过滤JPG
            img_url = img_elem.get_attribute("src")
            if img_url and img_url.endswith(".jpg"):
                # 去重：避免重复添加同一图片
                if img_url not in img_urls:
                    img_urls.append(img_url)
                    print(f"🔍 找到JPG链接：{img_url[:50]}...")  # 打印调试，确认拿到链接
                    
    except Exception as e:
        print(f"⚠️ 提取链接出错：{str(e)[:60]}")
    return img_urls

# 其他函数不变，仅修改get_jpg_urls即可
    """提取Firefox 145页面中的JPG链接"""
    img_urls = []
    try:
        # Firefox 145对动态元素支持优化：强制等待元素渲染
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        img_elems = driver.find_elements(By.CSS_SELECTOR, IMG_SELECTOR)
        
        for elem in img_elems:
            # Firefox 145需用get_property替代get_attribute（兼容src获取）
            img_url = elem.get_property("src") or elem.get_attribute("src")
            if img_url and (img_url.endswith(".jpg") or ".jpg?" in img_url):
                clean_url = re.sub(r'\?.*$', '', img_url)
                if clean_url not in img_urls:
                    img_urls.append(clean_url)
    except Exception as e:
        print(f"⚠️ 提取链接失败：{str(e)[:60]}")
    return img_urls

def download_jpg(img_url, save_path):
    """下载JPG（适配Firefox 145的防盗链）"""
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": TARGET_URL,
        "Accept": "image/jpeg,image/png,*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close"
    }
    try:
        response = requests.get(
            img_url,
            headers=headers,
            timeout=20,
            verify=False,
            stream=True
        )
        response.raise_for_status()
        # 分块写入（适配大图片）
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"✅ 成功：{os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"❌ 失败：{img_url[:60]} | {str(e)[:40]}")
        return False

def crawl_firefox_145():
    # 1. 前置检查：确认驱动路径存在
    if not os.path.exists(GECKO_DRIVER_PATH):
        print(f"❌ GeckoDriver路径不存在：{GECKO_DRIVER_PATH}")
        print("   请确认驱动文件已放到C:\\geckodriver文件夹中！")
        return
    
    # 2. 初始化Firefox浏览器
    try:
        driver = init_firefox_145()
    except Exception as e:
        print(f"❌ 启动Firefox 145失败：{str(e)[:60]}")
        print("   检查：1.GeckoDriver版本 2.Firefox是否安装 3.驱动权限")
        return
    
    # 3. 访问目标练习页面
    try:
        driver.get(TARGET_URL)
        time.sleep(4)  # Firefox 145首次加载需强制等待
        print(f"✅ 成功访问页面：{TARGET_URL}")
    except Exception as e:
        print(f"❌ 访问页面失败：{str(e)[:60]}")
        driver.quit()
        return
    
    # 4. 创建图片保存文件夹
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    # 5. 循环加载更多内容+提取JPG链接
    all_urls = []
    load_count = 0
    max_load = 4  # 练习用：最多加载4次
    
    while load_count < max_load:
        current_urls = get_jpg_urls(driver)
        new_urls = [u for u in current_urls if u not in all_urls]
        all_urls.extend(new_urls)
        
        print(f"\n🔄 第{load_count+1}次加载：")
        print(f"   新增JPG链接：{len(new_urls)}个 | 累计链接：{len(all_urls)}个")
        
        # 点击“MORE”按钮加载更多
        try:
            load_btn = driver.find_element(By.CSS_SELECTOR, LOAD_MORE_BTN_SELECTOR)
            driver.execute_script("arguments[0].scrollIntoView(true);", load_btn)
            time.sleep(1)
            load_btn.click()
            time.sleep(3)  # 适配Firefox 145的加载速度
            load_count += 1
        except:
            print("⚠️ 无更多内容/加载按钮未找到，终止加载")
            break
    
    # 6. 批量下载JPG图片
    print(f"\n📥 开始下载{len(all_urls)}张JPG图片...")
    success_count = 0
    for idx, url in enumerate(all_urls):
        img_name = f"firefox145_{idx+1}_{os.path.basename(url)}"
        save_path = os.path.join(SAVE_FOLDER, img_name)
        if download_jpg(url, save_path):
            success_count += 1
        time.sleep(1.5)  # 延长间隔，避免被网站限制
    
    # 7. 爬取完成，关闭浏览器
    driver.quit()
    print(f"\n🎉 练习完成（Firefox 145.0.2）：")
    print(f"   📊 统计：累计提取{len(all_urls)}个JPG链接 | 成功下载{success_count}张")
    print(f"   📂 图片保存路径：{os.path.abspath(SAVE_FOLDER)}")

if __name__ == "__main__":
    # 忽略SSL警告（适配国内网络）
    requests.packages.urllib3.disable_warnings()
    crawl_firefox_145()