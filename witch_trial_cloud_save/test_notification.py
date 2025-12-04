import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notification import Notifier

# 测试通知功能
print("测试通知功能...")

# 测试备份成功通知
print("\n1. 测试备份成功通知:")
result = Notifier.backup_success()
print(f"备份成功通知结果: {result}")

# 测试恢复成功通知
print("\n2. 测试恢复成功通知:")
result = Notifier.restore_success()
print(f"恢复成功通知结果: {result}")

# 测试自定义错误通知
print("\n3. 测试错误通知:")
result = Notifier.error("测试错误消息")
print(f"错误通知结果: {result}")

print("\n所有通知测试完成！")