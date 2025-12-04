import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SaveMonitor:
    def __init__(self, save_dir, callback):
        """初始化监控器"""
        self.save_dir = save_dir
        self.callback = callback
        self.is_running = False
        # 初始化解码器
        self.event_handler = SaveEventHandler(callback)
        self.observer = None
    
    def start(self):
        """开始监控"""
        # 检查存档目录是否存在
        if not os.path.exists(self.save_dir):
            print(f"警告：存档目录 {self.save_dir} 不存在")
            return False
        
        # 如果已经在运行，先停止
        if self.is_running:
            self.stop()
        
        # 创建新的Observer实例
        self.observer = Observer()
        
        # 安排监控任务
        self.observer.schedule(
            self.event_handler,
            self.save_dir,
            recursive=True
        )
        
        # 启动监控
        self.observer.start()
        self.is_running = True
        return True
    
    def stop(self):
        """停止监控"""
        if self.is_running and self.observer:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
    
    def pause(self):
        """暂停监控"""
        self.stop()
    
    def resume(self):
        """恢复监控"""
        if not self.is_running:
            self.start()
    
    def get_current_files(self):
        """获取当前存档目录的文件列表和修改时间"""
        files_info = {}
        for root, dirs, files in os.walk(self.save_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.save_dir)
                mtime = os.path.getmtime(file_path)
                files_info[rel_path] = mtime
        return files_info

class SaveEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        """初始化事件处理器"""
        self.callback = callback
        self.last_event_time = 0
        self.debounce_delay = 2  # 防抖延迟（秒）
    
    def on_modified(self, event):
        """文件修改事件"""
        self.handle_event(event)
    
    def on_created(self, event):
        """文件创建事件"""
        self.handle_event(event)
    
    def on_deleted(self, event):
        """文件删除事件"""
        self.handle_event(event)
    
    def handle_event(self, event):
        """处理文件系统事件"""
        current_time = time.time()
        
        # 防抖处理，避免短时间内多次触发
        if current_time - self.last_event_time < self.debounce_delay:
            return
        
        self.last_event_time = current_time
        
        # 调用回调函数
        if not event.is_directory:
            self.callback()