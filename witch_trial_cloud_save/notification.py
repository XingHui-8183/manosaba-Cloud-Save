import time
import sys
import os
import subprocess
import tempfile

class Notifier:
    @staticmethod
    def show_notification(title, message):
        """显示系统通知"""
        try:
            # 控制台输出，确保通知信息能被看到
            print(f"[{title}] {message}")
            
            if sys.platform == "win32":
                # Windows系统，尝试多种简单可靠的通知方法
                
                # 对标题和消息进行转义，防止PowerShell脚本出错
                title_escaped = title.replace("'", "''")
                message_escaped = message.replace("'", "''")
                
                # 1. 优先使用更可靠的PowerShell NotifyIcon方法
                try:
                    # 使用更可靠的NotifyIcon实现
                    ps_script = f""" 
                    Add-Type -AssemblyName System.Windows.Forms
                    Add-Type -AssemblyName System.Drawing
                    
                    # 创建通知图标对象
                    $notifyIcon = New-Object System.Windows.Forms.NotifyIcon
                    
                    # 设置图标和基本属性
                    $notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
                    $notifyIcon.Visible = $true
                    
                    # 设置通知内容
                    $notifyIcon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
                    $notifyIcon.BalloonTipTitle = '{title_escaped}'
                    $notifyIcon.BalloonTipText = '{message_escaped}'
                    
                    # 显示通知
                    $notifyIcon.ShowBalloonTip(3000)
                    
                    # 短暂延迟后清理资源
                    Start-Sleep -Milliseconds 3500
                    $notifyIcon.Dispose()
                    """
                    
                    result = subprocess.run(
                        ["powershell", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return True
                    else:
                        print(f"PowerShell NotifyIcon通知失败，错误码: {result.returncode}")
                        print(f"错误输出: {result.stderr}")
                except Exception as e:
                    print(f"PowerShell NotifyIcon通知失败: {e}")
                
                # 2. 尝试使用PowerShell Toast通知脚本作为备选
                try:
                    # 使用更简洁的PowerShell命令，避免复杂的对象创建
                    ps_script = f""" 
                    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                    $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                    
                    # 设置标题和内容
                    $Title = $Template.GetElementsByTagName("text")[0]
                    $Title.InnerText = '{title_escaped}'
                    $Message = $Template.GetElementsByTagName("text")[1]
                    $Message.InnerText = '{message_escaped}'
                    
                    # 创建通知
                    $Toast = [Windows.UI.Notifications.ToastNotification]::new($Template)
                    $Toast.Tag = 'CloudSaveTool'
                    $Toast.Group = 'CloudSaveTool'
                    
                    # 显示通知
                    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('CloudSaveTool').Show($Toast)
                    """
                    
                    # 执行PowerShell脚本
                    result = subprocess.run(
                        ["powershell", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return True
                    else:
                        print(f"PowerShell Toast通知失败，错误码: {result.returncode}")
                        print(f"错误输出: {result.stderr}")
                except Exception as e:
                    print(f"PowerShell Toast通知失败: {e}")
                
                # 3. 尝试使用msg命令（仅管理员可用，但简单可靠）
                try:
                    # 对消息进行转义，防止命令行解析错误
                    msg_content = f"{title}: {message}"
                    result = subprocess.run(
                        ["msg", "*", msg_content],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return True
                except Exception as e:
                    print(f"MSG命令通知失败: {e}")
                
                # 4. 尝试使用rundll32命令调用Windows API（最底层的方法）
                try:
                    # 使用user32.dll的MessageBox函数显示简单消息框
                    subprocess.run(
                        ["rundll32", "user32.dll,MessageBoxA", "0", f"{message}", f"{title}", "64"],
                        capture_output=True,
                        timeout=10
                    )
                    return True
                except Exception as e:
                    print(f"Rundll32通知失败: {e}")
            
            # 所有方法都失败，只返回控制台输出
            return True
        except Exception as e:
            print(f"通知发送失败: {e}")
            # 确保控制台输出
            print(f"[{title}] {message}")
            return False
    
    @staticmethod
    def backup_success():
        """备份成功通知"""
        return Notifier.show_notification(
            "备份成功",
            "存档已成功备份到云端"
        )
    
    @staticmethod
    def restore_success():
        """恢复成功通知"""
        return Notifier.show_notification(
            "恢复成功",
            "存档已从云端成功恢复"
        )
    
    @staticmethod
    def error(message):
        """错误通知"""
        return Notifier.show_notification(
            "操作失败",
            message
        )