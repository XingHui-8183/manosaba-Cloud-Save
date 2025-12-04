import tkinter as tk
from tkinter import ttk, messagebox
import os
import tempfile
import webbrowser
from config import Config
from compress import CompressManager
from github_api import GitAPI
from monitor import SaveMonitor
from notification import Notifier

class App:
    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.monitor = None
        
        # 初始化GUI
        self.setup_gui()
        
        # 初始化监控
        self.init_monitor()
        
        # 根据设置执行自动操作
        self.auto_action()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root.title("魔女审判云存档")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=10)
        
        title = ttk.Label(
            title_frame,
            text="魔女审判云存档",
            font=("Arial", 16, "bold")
        )
        title.pack(side=tk.LEFT, padx=5)
        
        # 打开存档目录按钮
        open_dir_btn = ttk.Button(
            title_frame,
            text="打开存档目录",
            command=self.open_save_dir
        )
        open_dir_btn.pack(side=tk.RIGHT, padx=5)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 手动上传按钮
        self.upload_btn = ttk.Button(
            button_frame,
            text="手动上传存档",
            command=self.manual_upload
        )
        self.upload_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 同步存档按钮
        self.sync_btn = ttk.Button(
            button_frame,
            text="同步最新存档",
            command=self.sync_latest
        )
        self.sync_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 拉取存档目录按钮
        self.refresh_btn = ttk.Button(
            button_frame,
            text="拉取存档目录",
            command=self.refresh_backup_list
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 设置按钮
        self.settings_btn = ttk.Button(
            button_frame,
            text="设置",
            command=self.open_settings
        )
        self.settings_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 创建备份列表框架
        list_frame = ttk.LabelFrame(main_frame, text="云端备份列表")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建列表框
        self.backup_list = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10)
        )
        self.backup_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.backup_list.yview)
        
        # 创建操作按钮框架
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        # 恢复选中的备份按钮
        self.restore_btn = ttk.Button(
            action_frame,
            text="恢复选中的备份",
            command=self.restore_selected
        )
        self.restore_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 删除选中的备份按钮
        self.delete_btn = ttk.Button(
            action_frame,
            text="删除选中的备份",
            command=self.delete_selected
        )
        self.delete_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 删除所有备份按钮
        self.delete_all_btn = ttk.Button(
            action_frame,
            text="删除所有备份",
            command=self.delete_all_backups
        )
        self.delete_all_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 刷新备份列表
        self.refresh_backup_list()
    
    def open_save_dir(self):
        """打开存档目录"""
        import os
        import subprocess
        
        save_dir = self.config.get("save_dir")
        
        # 确保存档目录存在
        if not os.path.exists(save_dir):
            messagebox.showerror("错误", f"存档目录不存在: {save_dir}")
            return
        
        try:
            # 在Windows上打开文件夹
            subprocess.Popen(f'explorer "{save_dir}"')
        except Exception as e:
            messagebox.showerror("错误", f"无法打开存档目录: {e}")
    
    def init_monitor(self):
        """初始化监控器"""
        save_dir = self.config.get("save_dir")
        self.monitor = SaveMonitor(save_dir, self.auto_backup)
        self.monitor.start()
        # 初始化最后上传时间
        self.last_upload_time = 0
    
    def auto_action(self):
        """根据设置执行自动操作"""
        auto_action = self.config.get("auto_action")
        if auto_action == "pull":
            self.sync_latest()
        elif auto_action == "push":
            self.manual_upload()
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        # 清空列表
        self.backup_list.delete(0, tk.END)
        
        # 获取GitHub配置
        owner = self.config.get("github_owner")
        repo = self.config.get("github_repo")
        token = self.config.get("github_token")
        
        debug_mode = self.config.get("debug_mode")
        
        if not all([owner, repo, token]):
            self.backup_list.insert(tk.END, "请先在设置中配置GitHub信息")
            return
        
        # 获取备份列表
        git_api = GitAPI(owner, repo, token, debug=debug_mode)
        backups = git_api.list_backups()
        
        if not backups:
            self.backup_list.insert(tk.END, "暂无备份")
        else:
            for backup in backups:
                self.backup_list.insert(tk.END, backup)
    
    def manual_upload(self, is_auto=False):
        """手动上传存档"""
        import time
        
        # 检查10秒内是否已经上传过
        current_time = time.time()
        if current_time - self.last_upload_time < 10:
            # 10秒内已经上传过，不执行操作
            remaining_time = int(10 - (current_time - self.last_upload_time))
            if not is_auto:
                messagebox.showinfo("提示", f"请稍后再试，{remaining_time}秒后可再次上传")
            elif self.config.get("debug_mode"):
                print(f"[调试] 10秒内已上传，跳过自动备份")
            return
        
        try:
            # 获取GitHub配置
            owner = self.config.get("github_owner")
            repo = self.config.get("github_repo")
            token = self.config.get("github_token")
            
            save_dir = self.config.get("save_dir")
            debug_mode = self.config.get("debug_mode")
            
            if not all([owner, repo, token]):
                if not is_auto:
                    messagebox.showerror("错误", "请先在设置中配置GitHub信息")
                return
            
            # 创建备份
            temp_dir = tempfile.gettempdir()
            zip_path = CompressManager.create_backup(save_dir, temp_dir, debug=debug_mode)
            
            # 上传到GitHub
            git_api = GitAPI(owner, repo, token, debug=debug_mode)
            success = git_api.upload_file(
                zip_path,
                f"自动备份: {zip_path.parent.name}"
            )
            
            if success:
                # 更新最后上传时间
                self.last_upload_time = time.time()
                Notifier.backup_success()
                self.refresh_backup_list()
                if not is_auto:
                    messagebox.showinfo("成功", "存档已成功上传到云端")
            else:
                Notifier.error("上传失败")
                if not is_auto:
                    messagebox.showerror("错误", "存档上传失败")
                    
        except Exception as e:
            Notifier.error(f"上传失败: {str(e)}")
            if not is_auto:
                messagebox.showerror("错误", f"上传失败: {str(e)}")
    
    def sync_latest(self):
        """同步最新存档"""
        try:
            # 获取GitHub配置
            owner = self.config.get("github_owner")
            repo = self.config.get("github_repo")
            token = self.config.get("github_token")
            
            save_dir = self.config.get("save_dir")
            debug_mode = self.config.get("debug_mode")
            
            if not all([owner, repo, token]):
                messagebox.showerror("错误", "请先在设置中配置GitHub信息")
                return
        
            # 获取最新备份
            git_api = GitAPI(owner, repo, token, debug=debug_mode)
            backups = git_api.list_backups()
            
            if not backups:
                messagebox.showinfo("提示", "云端暂无备份")
                return
            
            # 下载最新备份
            latest_backup = backups[0]
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, f"latest_backup.zip")
            
            success = git_api.download_backup(latest_backup, zip_path)
            if not success:
                Notifier.error("下载失败")
                messagebox.showerror("错误", "备份下载失败")
                return
            
            # 暂停监控，防止恢复后立即上传
            if self.monitor:
                self.monitor.pause()
            
            # 恢复备份
            CompressManager.delete_old_save(save_dir, debug=debug_mode)
            CompressManager.restore_backup(zip_path, save_dir, debug=debug_mode)
            
            Notifier.restore_success()
            messagebox.showinfo("成功", "存档已成功同步")

        except Exception as e:
            Notifier.error(f"同步失败: {str(e)}")
            messagebox.showerror("错误", f"同步失败: {str(e)}")
        finally:
            # 无论成功失败，都恢复监控
            if self.monitor:
                self.monitor.resume()
                if self.config.get("debug_mode"):
                    print(f"[调试] 监控已恢复")
    
    def restore_selected(self):
        """恢复选中的备份"""
        try:
            # 获取选中的备份
            selection = self.backup_list.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个备份")
                return
            
            selected_backup = self.backup_list.get(selection[0])
            
            # 确认恢复
            if not messagebox.askyesno(
                "确认恢复",
                f"确定要恢复备份 {selected_backup} 吗？这将覆盖当前存档。"
            ):
                return
            
            # 获取GitHub配置
            owner = self.config.get("github_owner")
            repo = self.config.get("github_repo")
            token = self.config.get("github_token")
            
            save_dir = self.config.get("save_dir")
            debug_mode = self.config.get("debug_mode")
            
            if not all([owner, repo, token]):
                messagebox.showerror("错误", "请先在设置中配置GitHub信息")
                return
            
            # 下载备份
            git_api = GitAPI(owner, repo, token, debug=debug_mode)
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, f"restore_backup.zip")
            
            success = git_api.download_backup(selected_backup, zip_path)
            if not success:
                Notifier.error("下载失败")
                messagebox.showerror("错误", "备份下载失败")
                return
            
            # 暂停监控，防止恢复后立即上传
            if self.monitor:
                self.monitor.pause()
            
            # 恢复备份
            CompressManager.delete_old_save(save_dir, debug=debug_mode)
            CompressManager.restore_backup(zip_path, save_dir, debug=debug_mode)
            
            Notifier.restore_success()
            messagebox.showinfo("成功", f"备份 {selected_backup} 已成功恢复")

        except Exception as e:
            Notifier.error(f"恢复失败: {str(e)}")
            messagebox.showerror("错误", f"恢复失败: {str(e)}")
        finally:
            # 无论成功失败，都恢复监控
            if self.monitor:
                self.monitor.resume()
                if self.config.get("debug_mode"):
                    print(f"[调试] 监控已恢复")
    
    def delete_selected(self):
        """删除选中的备份"""
        try:
            # 获取选中的备份
            selection = self.backup_list.curselection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个备份")
                return
            
            selected_backup = self.backup_list.get(selection[0])
            
            # 确认删除
            if not messagebox.askyesno(
                "确认删除",
                f"确定要删除备份 {selected_backup} 吗？此操作不可恢复。"
            ):
                return
            
            # 获取GitHub配置
            owner = self.config.get("github_owner")
            repo = self.config.get("github_repo")
            token = self.config.get("github_token")
            
            debug_mode = self.config.get("debug_mode")
            
            if not all([owner, repo, token]):
                messagebox.showerror("错误", "请先在设置中配置GitHub信息")
                return
            
            # 删除备份
            git_api = GitAPI(owner, repo, token, debug=debug_mode)
            success = git_api.delete_backup(selected_backup)
            
            if success:
                Notifier.show_notification("成功", f"备份 {selected_backup} 已删除")
                self.refresh_backup_list()
                messagebox.showinfo("成功", f"备份 {selected_backup} 已成功删除")
            else:
                Notifier.error("删除失败")
                messagebox.showerror("错误", f"删除备份 {selected_backup} 失败")
                
        except Exception as e:
            Notifier.error(f"删除失败: {str(e)}")
            messagebox.showerror("错误", f"删除备份失败: {e}")
    
    def delete_all_backups(self):
        """删除所有备份"""
        try:
            # 获取GitHub配置
            owner = self.config.get("github_owner")
            repo = self.config.get("github_repo")
            token = self.config.get("github_token")
            
            if not all([owner, repo, token]):
                messagebox.showerror("错误", "请先在设置中配置GitHub信息")
                return
            
            # 获取当前备份列表
            git_api = GitAPI(owner, repo, token)
            backups = git_api.list_backups()
            
            if not backups:
                messagebox.showinfo("提示", "当前没有备份")
                return
            
            # 二次确认删除所有备份
            if not messagebox.askyesno(
                "确认删除所有备份",
                f"确定要删除所有 {len(backups)} 个备份吗？此操作不可恢复！"
            ):
                return
            
            # 再次确认，防止误操作
            if not messagebox.askyesno(
                "再次确认",
                "您确定要删除所有备份吗？此操作将永久删除所有备份数据，无法恢复！"
            ):
                return
            
            # 删除所有备份
            debug_mode = self.config.get("debug_mode")
            git_api = GitAPI(owner, repo, token, debug=debug_mode)
            success = git_api.delete_all_backups()
            
            if success:
                Notifier.show_notification("成功", "所有备份已删除")
                self.refresh_backup_list()
                messagebox.showinfo("成功", "所有备份已成功删除")
            else:
                Notifier.error("删除失败")
                messagebox.showerror("错误", "删除所有备份失败")
                
        except Exception as e:
            Notifier.error(f"删除失败: {str(e)}")
            messagebox.showerror("错误", f"删除所有备份失败: {e}")
    
    def auto_backup(self):
        """自动备份（监控到变化时调用）"""
        import time
        
        # 添加延迟，确保文件操作完成
        time.sleep(1)
        
        # 执行上传，标记为自动上传
        self.manual_upload(is_auto=True)
    
    def open_settings(self):
        """打开设置页面"""
        SettingsWindow(self.root, self.config, self.refresh_backup_list)
    
    def on_close(self):
        """关闭窗口时的清理操作"""
        if self.monitor:
            self.monitor.stop()
        self.root.destroy()

class SettingsWindow:
    def __init__(self, parent, config, refresh_callback):
        self.parent = parent
        self.config = config
        self.refresh_callback = refresh_callback
        
        # 创建设置窗口
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("700x400")
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.grab_set()
        
        # 创建设置框架
        settings_frame = ttk.Frame(self.window, padding="20")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建两列布局
        left_frame = ttk.Frame(settings_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(settings_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 左侧框架：基础设置
        
        # 存档路径
        ttk.Label(left_frame, text="存档路径:").pack(anchor=tk.W, pady=5)
        path_frame = ttk.Frame(left_frame)
        path_frame.pack(anchor=tk.W, pady=5, fill=tk.X)
        
        self.save_dir_var = tk.StringVar(value=self.config.get("save_dir"))
        ttk.Entry(
            path_frame,
            textvariable=self.save_dir_var,
            width=30
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 浏览按钮
        browse_btn = ttk.Button(
            path_frame,
            text="浏览",
            command=self.browse_save_dir
        )
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        # GitHub平台配置提示
        platform_frame = ttk.Frame(left_frame)
        platform_frame.pack(anchor=tk.W, pady=5)
        
        ttk.Label(platform_frame, text="使用GitHub平台:").pack(anchor=tk.W, pady=5)
        
        # 自动操作
        ttk.Label(left_frame, text="启动时自动操作:").pack(anchor=tk.W, pady=5)
        self.auto_action_var = tk.StringVar(value=self.config.get("auto_action"))
        auto_action_frame = ttk.Frame(left_frame)
        auto_action_frame.pack(anchor=tk.W, pady=5)
        
        ttk.Radiobutton(
            auto_action_frame,
            text="什么都不做",
            variable=self.auto_action_var,
            value="none"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            auto_action_frame,
            text="从云拉取最新存档",
            variable=self.auto_action_var,
            value="pull"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            auto_action_frame,
            text="上传当前存档",
            variable=self.auto_action_var,
            value="push"
        ).pack(anchor=tk.W)
        
        # 调试模式
        ttk.Label(left_frame, text="调试模式:").pack(anchor=tk.W, pady=5)
        self.debug_mode_var = tk.BooleanVar(value=self.config.get("debug_mode"))
        debug_mode_check = ttk.Checkbutton(
            left_frame,
            text="开启调试模式（实时打印日志）",
            variable=self.debug_mode_var
        )
        debug_mode_check.pack(anchor=tk.W, pady=5)
        
        # GitHub链接
        github_frame = ttk.Frame(left_frame)
        github_frame.pack(anchor=tk.W, pady=10)
        
        github_link = ttk.Label(
            github_frame,
            text="觉得好用就请点个star",
            foreground="blue",
            cursor="hand2"
        )
        github_link.pack(anchor=tk.W)
        
        # 添加点击事件
        def open_github():
            webbrowser.open("https://github.com/XingHui-8183/manosaba-Cloud-Save")
        
        github_link.bind("<Button-1>", lambda e: open_github())
        
        # 浅灰色小字显示链接
        url_label = ttk.Label(
            github_frame,
            text="https://github.com/XingHui-8183/manosaba-Cloud-Save",
            foreground="#888888",
            font=("Arial", 8)
        )
        url_label.pack(anchor=tk.W, pady=2)
        
        # 右侧框架：平台配置
        
        # GitHub 配置
        self.github_frame = ttk.LabelFrame(right_frame, text="GitHub 配置", padding="10")
        self.github_frame.pack(fill=tk.X, pady=5)
        
        # GitHub Owner
        ttk.Label(self.github_frame, text="用户名/组织名:").pack(anchor=tk.W, pady=5)
        self.github_owner_var = tk.StringVar(value=self.config.get("github_owner"))
        ttk.Entry(
            self.github_frame,
            textvariable=self.github_owner_var,
            width=30
        ).pack(anchor=tk.W, pady=5, fill=tk.X)
        
        # GitHub Repo
        ttk.Label(self.github_frame, text="仓库名:").pack(anchor=tk.W, pady=5)
        self.github_repo_var = tk.StringVar(value=self.config.get("github_repo"))
        ttk.Entry(
            self.github_frame,
            textvariable=self.github_repo_var,
            width=30
        ).pack(anchor=tk.W, pady=5, fill=tk.X)
        
        # GitHub Token
        ttk.Label(self.github_frame, text="Token:").pack(anchor=tk.W, pady=5)
        self.github_token_var = tk.StringVar(value=self.config.get("github_token"))
        ttk.Entry(
            self.github_frame,
            textvariable=self.github_token_var,
            width=30,
            show="*"
        ).pack(anchor=tk.W, pady=5, fill=tk.X)
        

        

        
        # 保存按钮
        save_btn = ttk.Button(
            settings_frame,
            text="保存设置",
            command=self.save_settings
        )
        save_btn.pack(fill=tk.X, pady=20)
    
    def browse_save_dir(self):
        """浏览选择存档目录"""
        from tkinter import filedialog
        
        # 打开文件夹选择对话框
        selected_dir = filedialog.askdirectory(
            title="选择存档目录",
            initialdir=self.save_dir_var.get()
        )
        
        if selected_dir:
            self.save_dir_var.set(selected_dir)
    

    
    def save_settings(self):
        """保存设置"""
        # 保存配置
        self.config.set("save_dir", self.save_dir_var.get())
        self.config.set("github_owner", self.github_owner_var.get())
        self.config.set("github_repo", self.github_repo_var.get())
        self.config.set("github_token", self.github_token_var.get())
        self.config.set("auto_action", self.auto_action_var.get())
        self.config.set("debug_mode", self.debug_mode_var.get())
        
        # 刷新备份列表
        self.refresh_callback()
        
        # 关闭窗口
        self.window.destroy()
        messagebox.showinfo("成功", "设置已保存")

def main():
    """主函数"""
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()