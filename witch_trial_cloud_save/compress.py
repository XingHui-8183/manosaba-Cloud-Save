import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

class CompressManager:
    @staticmethod
    def create_backup(save_dir, output_dir, debug=False):
        """创建存档的压缩包备份"""
        if debug:
            print(f"[调试] 创建备份 - 存档目录: {save_dir}, 输出目录: {output_dir}")
        
        # 创建日期时间格式的文件夹名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_folder = Path(output_dir) / timestamp
        backup_folder.mkdir(parents=True, exist_ok=True)
        
        if debug:
            print(f"[调试] 创建备份文件夹: {backup_folder}")
        
        # 创建压缩包路径
        zip_path = backup_folder / f"backup_{timestamp}.zip"
        
        if debug:
            print(f"[调试] 创建压缩包: {zip_path}")
        
        # 解决文件被占用问题：先复制到临时目录，再压缩
        import tempfile
        with tempfile.TemporaryDirectory() as temp_copy_dir:
            if debug:
                print(f"[调试] 创建临时复制目录: {temp_copy_dir}")
            
            # 复制存档目录到临时目录
            temp_save_dir = Path(temp_copy_dir) / "Saves_v1"
            temp_save_dir.mkdir(parents=True, exist_ok=True)
            
            if debug:
                print(f"[调试] 临时存档目录: {temp_save_dir}")
            
            # 遍历存档目录并复制文件到临时目录
            for root, dirs, files in os.walk(save_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    # 计算相对路径，保持目录结构
                    rel_path = os.path.relpath(src_path, save_dir)
                    dst_path = os.path.join(temp_save_dir, rel_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    try:
                        # 复制文件
                        import shutil
                        shutil.copy2(src_path, dst_path)
                        if debug:
                            print(f"[调试] 复制文件: {src_path} -> {dst_path}")
                    except PermissionError as e:
                        if debug:
                            print(f"[调试] 复制文件失败，权限被拒绝: {src_path}")
                            print(f"[调试] 错误信息: {e}")
                        # 尝试跳过被占用的文件，继续复制其他文件
                        continue
                    except Exception as e:
                        if debug:
                            print(f"[调试] 复制文件失败: {src_path}")
                            print(f"[调试] 错误信息: {e}")
                        # 尝试跳过失败的文件，继续复制其他文件
                        continue
            
            # 创建压缩包（使用临时复制的文件）
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历临时存档目录并添加到压缩包
                for root, dirs, files in os.walk(temp_save_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 计算相对路径，保持目录结构
                        rel_path = os.path.relpath(file_path, temp_save_dir)
                        zipf.write(file_path, rel_path)
                        
                        if debug:
                            print(f"[调试] 添加文件到压缩包: {rel_path}")
        
        if debug:
            print(f"[调试] 备份创建成功: {zip_path}")
        
        return zip_path
    
    @staticmethod
    def restore_backup(zip_path, save_dir, debug=False):
        """从压缩包恢复存档"""
        if debug:
            print(f"[调试] 恢复备份 - 压缩包路径: {zip_path}, 目标目录: {save_dir}")
        
        # 确保存档目录存在
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # 解压压缩包内容到存档目录
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(save_dir)
            
            if debug:
                print(f"[调试] 解压文件列表: {zipf.namelist()}")
        
        if debug:
            print(f"[调试] 备份恢复成功")
        
        return True
    
    @staticmethod
    def delete_old_save(save_dir, debug=False):
        """删除旧的存档目录"""
        if debug:
            print(f"[调试] 删除旧存档 - 目录: {save_dir}")
        
        if os.path.exists(save_dir):
            shutil.rmtree(save_dir)
            if debug:
                print(f"[调试] 旧存档删除成功")
        
        return True