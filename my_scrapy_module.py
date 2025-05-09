import os
import re
import time
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading


class ImageSpider:
    """图片爬虫类"""

    def __init__(self, save_root=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SLBrowser/9.0.6.2081 SLBChan/112 SLBVPV/64-bit'
        }
        self.base_url = "https://image.baidu.com/search/flip?tn=baiduimage&ie=utf-8&word={}&pn={}"
        self.save_root = save_root or os.path.join(os.getcwd(), 'downloads')

    def get_html(self, url):
        """发送HTTP请求获取网页内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败，状态码：{response.status_code}，URL：{url}")
        except Exception as e:
            print(f"请求出错：{e}，URL：{url}")
        return None

    def extract_image_urls(self, html):
        """从HTML内容中提取图片URL"""
        if not html:
            return []

        # 使用正则表达式提取百度图片URL
        img_urls = re.findall(r'"objURL":"(.*?)"', html, re.S)

        # 过滤无效URL
        return [url for url in img_urls if url.startswith('http')]

    def download_image(self, img_url, save_path, retry=3):
        """下载单张图片"""
        if not img_url.startswith('http'):
            print(f"无效的图片URL: {img_url}")
            return False

        try:
            response = requests.get(img_url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"下载失败，状态码：{response.status_code}，URL：{img_url}")
        except Exception as e:
            if retry > 0:
                print(f"下载出错，尝试重试 ({3 - retry + 1}/3): {e}")
                time.sleep(1)
                return self.download_image(img_url, save_path, retry - 1)
            else:
                print(f"下载出错，已达到最大重试次数: {e}")
        return False

    def create_save_dir(self, keyword, custom_path=None):
        """创建保存图片的目录

        Args:
            keyword: 搜索关键词
            custom_path: 自定义保存路径（可选）
        """
        if custom_path:
            # 使用用户指定的完整路径
            save_dir = custom_path.replace('"','')
        else:
            # 使用默认根目录 + 关键词文件夹
            valid_keyword = re.sub(r'[\\/:*?"<>|]', '_', keyword)
            save_dir = os.path.join(self.save_root, valid_keyword)

        # 创建目录（包括父目录）
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def crawl_images(self, keyword, max_count=100, sleep_time=1, custom_path=None, callback=None):
        """爬取关键词相关图片

        Args:
            keyword: 搜索关键词
            max_count: 最大下载数量
            sleep_time: 下载间隔时间（秒）
            custom_path: 自定义保存路径（可选）
            callback: 进度回调函数
        """
        save_dir = self.create_save_dir(keyword, custom_path)
        total_count = 0
        page_num = 0

        while total_count < max_count:
            url = self.base_url.format(keyword, page_num)
            html = self.get_html(url)

            if not html:
                break

            img_urls = self.extract_image_urls(html)

            if not img_urls:
                break

            for img_url in img_urls:
                if total_count >= max_count:
                    break

                save_path = os.path.join(save_dir, f"{keyword}_{total_count + 1}.jpg")
                if self.download_image(img_url, save_path):
                    total_count += 1
                    # 更新进度
                    if callback:
                        callback(total_count, max_count, save_dir)

                    time.sleep(sleep_time)  # 控制爬取速度

            page_num += 20
            # 防止无限循环
            if page_num > 1000:
                break

        return total_count, save_dir


class ImageSpiderGUI:
    """图片爬虫图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("百度图片爬虫")
        self.root.geometry("600x450")
        self.root.resizable(True, True)

        # 设置中文字体
        self.style = ttk.Style()
        self.style.configure(".", font=("SimHei", 10))

        self.spider = ImageSpider()
        self.is_running = False

        self.create_widgets()

    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 关键词输入
        ttk.Label(main_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.keyword_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.keyword_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)

        # 数量输入
        ttk.Label(main_frame, text="下载数量:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.count_var = tk.IntVar(value=100)
        ttk.Entry(main_frame, textvariable=self.count_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)

        # 自定义路径选项
        ttk.Label(main_frame, text="保存路径:").grid(row=2, column=0, sticky=tk.W, pady=5)

        self.use_custom_var = tk.BooleanVar()
        custom_check = ttk.Checkbutton(
            main_frame,
            text="使用自定义路径",
            variable=self.use_custom_var,
            command=self.toggle_custom_path
        )
        custom_check.grid(row=2, column=1, sticky=tk.W, pady=5)

        # 自定义路径输入框
        self.path_frame = ttk.Frame(main_frame)
        self.path_var = tk.StringVar()
        ttk.Entry(self.path_frame, textvariable=self.path_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.path_frame, text="浏览...", command=self.browse_path).pack(side=tk.LEFT)

        # 初始隐藏自定义路径输入
        self.path_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.path_frame.grid_remove()

        # 进度条
        ttk.Label(main_frame, text="下载进度:").grid(row=4, column=0, sticky=tk.W, pady=10)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            length=400,
            mode='determinate'
        )
        self.progress_bar.grid(row=4, column=1, sticky=tk.W, pady=10)

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 结果文本框
        ttk.Label(main_frame, text="下载日志:").grid(row=6, column=0, sticky=tk.NW, pady=5)
        self.log_text = tk.Text(main_frame, height=10, width=60)
        self.log_text.grid(row=6, column=1, sticky=tk.NSEW, pady=5)
        scrollbar = ttk.Scrollbar(main_frame, command=self.log_text.yview)
        scrollbar.grid(row=6, column=2, sticky=tk.NS)
        self.log_text.config(yscrollcommand=scrollbar.set)
        self.log_text.config(state=tk.DISABLED)

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=20)

        self.start_btn = ttk.Button(
            btn_frame,
            text="开始下载",
            command=self.start_crawl,
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = ttk.Button(
            btn_frame,
            text="停止",
            command=self.stop_crawl,
            width=15,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        # 配置列和行的权重，使界面可伸缩
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def toggle_custom_path(self):
        """切换自定义路径输入框的显示/隐藏"""
        if self.use_custom_var.get():
            self.path_frame.grid()
        else:
            self.path_frame.grid_remove()

    def browse_path(self):
        """打开文件浏览器选择保存路径"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)

    def update_status(self, message):
        """更新状态标签"""
        self.status_var.set(message)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_progress(self, current, total, save_dir):
        """更新进度条和状态"""
        progress = (current / total) * 100
        self.progress_var.set(progress)
        self.update_status(f"已下载 {current}/{total} 张图片，保存至: {save_dir}")

    def start_crawl(self):
        """开始爬取图片"""
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showerror("错误", "请输入搜索关键词")
            return

        try:
            max_count = max(1, self.count_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的下载数量")
            return

        custom_path = self.path_var.get().strip() if self.use_custom_var.get() else None

        if custom_path and not os.path.isdir(custom_path):
            try:
                os.makedirs(custom_path)
                self.update_status(f"创建目录: {custom_path}")
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {e}")
                return

        # 禁用开始按钮，启用停止按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_running = True

        # 清空日志和进度条
        self.progress_var.set(0)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        # 在新线程中执行爬取任务
        self.crawl_thread = threading.Thread(
            target=self._run_crawl,
            args=(keyword, max_count, custom_path)
        )
        self.crawl_thread.daemon = True
        self.crawl_thread.start()

    def _run_crawl(self, keyword, max_count, custom_path):
        """在线程中执行爬取任务"""
        try:
            self.update_status(f"开始下载 '{keyword}' 的图片...")
            total_downloaded, save_dir = self.spider.crawl_images(
                keyword,
                max_count,
                custom_path=custom_path,
                callback=self.update_progress
            )

            if self.is_running:
                self.update_status(f"下载完成！共下载 {total_downloaded} 张图片")
                messagebox.showinfo("完成", f"下载完成！共下载 {total_downloaded} 张图片\n保存路径: {save_dir}")
        except Exception as e:
            self.update_status(f"下载出错: {str(e)}")
            messagebox.showerror("错误", f"下载过程中出错: {str(e)}")
        finally:
            # 恢复按钮状态
            self.root.after(0, self._reset_ui)

    def stop_crawl(self):
        """停止爬取任务"""
        self.is_running = False
        self.update_status("正在停止...")
        self.stop_btn.config(state=tk.DISABLED)

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.is_running = False
