import os
import requests
import urllib.parse
from pathlib import Path

class GitAPI:
    def __init__(self, owner, repo, token, debug=False):
        """初始化GitHub API客户端"""
        self.owner = owner
        self.repo = repo
        self.token = token
        self.debug = debug
        
        # 对仓库名称进行URL编码，以支持中文仓库名称
        encoded_repo = urllib.parse.quote(repo)
        
        # GitHub API端点和请求头
        self.base_url = f"https://api.github.com/repos/{owner}/{encoded_repo}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def create_commit(self, file_path, content, message, max_retries=3, retry_delay=2):
        """创建或更新文件并提交，支持重试机制"""
        if self.debug:
            print(f"[调试] 创建提交 - 文件路径: {file_path}")
        
        # 从文件路径中提取备份信息
        file_name = Path(file_path).name
        backup_folder = Path(file_path).parent.name
        
        # 构造仓库中的路径，并对路径进行URL编码
        repo_path = f"{backup_folder}/{file_name}"
        repo_path = urllib.parse.quote(repo_path)
        
        if self.debug:
            print(f"[调试] 仓库路径: {repo_path}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 首先尝试直接创建文件（不包含sha）
                method = 'put'
                data = {
                    'message': message,
                    'content': content
                }
                
                # GitHub API需要添加branch参数
                data['branch'] = 'main'
                
                if self.debug:
                    print(f"[调试] 执行{method}请求（创建新文件） - URL: {self.base_url}/contents/{repo_path}")
                    print(f"[调试] 请求数据: {data}")
                
                response = requests.request(
                    method,
                    f"{self.base_url}/contents/{repo_path}",
                    headers=self.headers,
                    json=data,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 请求响应状态: {response.status_code}")
                    print(f"[调试] 请求响应内容: {response.text}")
                
                # 如果请求成功，直接返回
                if response.status_code == 201 or response.status_code == 200:
                    if self.debug:
                        print(f"[调试] 提交成功")
                    return True
                
                # 如果失败，可能需要获取sha进行更新
                if response.status_code == 400:
                    error_msg = response.text.lower()
                    if "sha is missing" in error_msg or "sha is empty" in error_msg:
                        if self.debug:
                            print(f"[调试] 需要更新现有文件，获取SHA...")
                        
                        # 获取文件信息以获取sha
                        get_url = f"{self.base_url}/contents/{repo_path}?ref=main"
                        
                        get_response = requests.get(
                            get_url,
                            headers=self.headers,
                            timeout=10
                        )
                        
                        if get_response.status_code == 200:
                            file_info = get_response.json()
                            sha = None
                            
                            # 处理Gitee API返回列表的情况
                            if isinstance(file_info, list):
                                # 查找匹配的文件
                                for item in file_info:
                                    if isinstance(item, dict) and item.get('name') == file_name:
                                        sha = item.get('sha')
                                        break
                            elif isinstance(file_info, dict):
                                sha = file_info.get('sha')
                            
                            if sha:
                                if self.debug:
                                    print(f"[调试] 获取到SHA: {sha}，更新文件...")
                                
                                # 使用sha更新文件
                                data['sha'] = sha
                                
                                if self.debug:
                                    print(f"[调试] 执行{method}请求（更新文件） - URL: {self.base_url}/contents/{repo_path}")
                                    print(f"[调试] 请求数据: {data}")
                                
                                update_response = requests.request(
                                    method,
                                    f"{self.base_url}/contents/{repo_path}",
                                    headers=self.headers,
                                    json=data,
                                    timeout=10
                                )
                                
                                if self.debug:
                                    print(f"[调试] 请求响应状态: {update_response.status_code}")
                                    print(f"[调试] 请求响应内容: {update_response.text}")
                                
                                if update_response.status_code == 200:
                                    if self.debug:
                                        print(f"[调试] 提交成功")
                                    return True
                                elif update_response.status_code == 404:
                                    # 文件可能已被删除，重新尝试创建
                                    if self.debug:
                                        print(f"[调试] 文件不存在，重新尝试创建...")
                                    del data['sha']
                                    continue
                            else:
                                if self.debug:
                                    print(f"[调试] 未找到文件 {file_name} 的SHA值，尝试创建新文件...")
                                # 未找到sha，可能是文件不存在，尝试创建新文件
                                if 'sha' in data:
                                    del data['sha']
                                continue
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"[调试] GitHub API错误: {e}")
                    print(f"[调试] 这可能是由于网络不稳定、API限流或GitHub服务器暂时不可用")
                
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return False
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] GitHub API错误: {e}")
                    import traceback
                    traceback.print_exc()
                return False
        
        if self.debug:
            print(f"[调试] 所有 {max_retries} 次尝试都失败了")
        return False
    
    def list_backups(self, max_retries=3, retry_delay=2):
        """获取仓库中的所有备份目录，支持重试机制"""
        if self.debug:
            print(f"[调试] 获取备份列表")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 获取仓库根目录内容
                url = f"{self.base_url}/contents/"
                # GitHub API需要添加ref参数
                url += "?ref=main"
                
                if self.debug:
                    print(f"[调试] 获取仓库根目录内容 (尝试 {retry_count + 1}/{max_retries}): {url}")
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=10  # 添加超时设置
                )
                
                if self.debug:
                    print(f"[调试] 响应状态: {response.status_code}")
                    print(f"[调试] 响应内容: {response.text}")
                
                if response.status_code == 200:
                    # 过滤出日期时间格式的文件夹
                    backups = []
                    items = response.json()
                    

                    
                    for item in items:
                        if item['type'] == 'dir':
                            backups.append(item['name'])
                    
                    # 按日期时间排序，最新的在前面
                    backups.sort(reverse=True)
                    
                    if self.debug:
                        print(f"[调试] 备份列表: {backups}")
                    
                    return backups
                elif response.status_code == 404:
                    if self.debug:
                        print(f"[调试] 获取备份列表失败：仓库或路径不存在")
                        print(f"[调试] 请检查：1. 仓库所有者 '{self.owner}' 是否正确")
                        print(f"[调试] 2. 仓库名称 '{self.repo}' 是否正确")
                        print(f"[调试] 3. 令牌是否有访问权限")
                        print(f"[调试] 4. 仓库是否为私有")
                    return []
                elif response.status_code == 401:
                    if self.debug:
                        print(f"[调试] 获取备份列表失败：未授权，请检查令牌是否有效")
                    return []
                elif response.status_code == 403:
                    if self.debug:
                        print(f"[调试] 获取备份列表失败：权限不足或API限流")
                    return []
                else:
                    if self.debug:
                        print(f"[调试] 获取备份列表失败，响应状态: {response.status_code}")
                    
                    # 增加重试计数
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return []
            
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"[调试] GitHub API连接错误: {e}")
                    print(f"[调试] 这可能是由于网络不稳定、API限流或GitHub服务器暂时不可用")
                
                # 增加重试计数
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return []
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] GitHub API错误: {e}")
                    import traceback
                    traceback.print_exc()
                return []
        
        # 所有重试都失败
        if self.debug:
            print(f"[调试] 所有 {max_retries} 次尝试都失败了")
        return []
    
    def download_backup(self, backup_folder, output_path, max_retries=3, retry_delay=2):
        """下载指定备份文件夹中的压缩包，支持重试机制"""
        if self.debug:
            print(f"[调试] 下载备份 - 备份文件夹: {backup_folder}, 输出路径: {output_path}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 获取备份文件夹内容
                if self.debug:
                    print(f"[调试] 获取备份文件夹内容: {backup_folder} (尝试 {retry_count + 1}/{max_retries})")
                
                # 构建请求URL
                folder_url = f"{self.base_url}/contents/{backup_folder}"
                # GitHub API需要添加ref参数
                folder_url += "?ref=main"
                
                response = requests.get(
                    folder_url,
                    headers=self.headers,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 响应状态: {response.status_code}")
                    print(f"[调试] 响应内容: {response.text}")
                
                if response.status_code == 200:
                    # 找到压缩包文件
                    zip_file = None
                    items = response.json()
                    

                    
                    for item in items:
                        if item['type'] == 'file' and item['name'].endswith('.zip'):
                            zip_file = item
                            break
                    
                    if not zip_file:
                        if self.debug:
                            print(f"[调试] 未找到压缩包文件")
                        return False
                    
                    if self.debug:
                        print(f"[调试] 找到压缩包文件: {zip_file['name']}")
                    
                    # 获取下载URL
                    download_url = zip_file.get('download_url')
                    
                    if self.debug:
                        print(f"[调试] 下载压缩包: {download_url}")
                    
                    # 下载文件不需要认证，因为download_url是临时的
                    download_response = requests.get(
                        download_url,
                        timeout=30  # 下载大文件需要更长超时
                    )
                    
                    if self.debug:
                        print(f"[调试] 下载响应状态: {download_response.status_code}")
                    
                    if download_response.status_code == 200:
                        # 保存到输出路径
                        if self.debug:
                            print(f"[调试] 保存到输出路径: {output_path}")
                        
                        with open(output_path, 'wb') as f:
                            f.write(download_response.content)
                        
                        if self.debug:
                            print(f"[调试] 下载成功")
                        
                        return True
                    else:
                        if self.debug:
                            print(f"[调试] 下载失败，响应状态: {download_response.status_code}")
                        return False
                elif response.status_code == 404:
                    if self.debug:
                        print(f"[调试] 备份文件夹不存在: {backup_folder}")
                    return False
                elif response.status_code == 401:
                    if self.debug:
                        print(f"[调试] 未授权，请检查令牌是否有效")
                    return False
                elif response.status_code == 403:
                    if self.debug:
                        print(f"[调试] 权限不足或API限流")
                    return False
                else:
                    if self.debug:
                        print(f"[调试] 获取备份文件夹失败，响应状态: {response.status_code}")
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return False
            
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"[调试] GitHub API连接错误: {e}")
                    print(f"[调试] 这可能是由于网络不稳定、API限流或GitHub服务器暂时不可用")
                
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return False
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] GitHub API错误: {e}")
                    import traceback
                    traceback.print_exc()
                return False
        
        if self.debug:
            print(f"[调试] 所有 {max_retries} 次尝试都失败了")
        return False
    
    def delete_file(self, file_path, max_retries=3, retry_delay=2):
        """删除仓库中的文件，支持重试机制"""
        if self.debug:
            print(f"[调试] 删除文件 - 文件路径: {file_path}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 获取文件信息的URL
                get_url = f"{self.base_url}/contents/{file_path}"
                # GitHub API需要添加ref参数
                get_url += "?ref=main"
                
                if self.debug:
                    print(f"[调试] 请求文件信息: {get_url} (尝试 {retry_count + 1}/{max_retries})")
                
                response = requests.get(
                    get_url,
                    headers=self.headers,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 获取文件信息响应状态: {response.status_code}")
                    print(f"[调试] 获取文件信息响应: {response.text}")
                
                if response.status_code == 200:
                    # 解析文件信息
                    file_info = response.json()
                    sha = file_info.get('sha')
                    
                    if self.debug:
                        print(f"[调试] 文件信息: {file_info}")
                        print(f"[调试] 获取文件SHA: {sha}")
                    
                    if not sha:
                        if self.debug:
                            print(f"[调试] 无法获取文件SHA: {file_path}")
                        return False
                    
                    # 执行删除操作
                    delete_data = {
                        'message': f"删除备份文件: {file_path}",
                        'sha': sha
                    }
                    
                    # GitHub API需要添加branch参数
                    delete_data['branch'] = 'main'
                    
                    if self.debug:
                        print(f"[调试] 准备删除请求数据: {delete_data}")
                    
                    response = requests.delete(
                        f"{self.base_url}/contents/{file_path}",
                        headers=self.headers,
                        json=delete_data,
                        timeout=10
                    )
                    
                    if self.debug:
                        print(f"[调试] 删除文件响应状态: {response.status_code}")
                        print(f"[调试] 删除文件响应: {response.text}")
                    
                    # 检查响应状态
                    success = response.status_code == 200
                    if success:
                        if self.debug:
                            print(f"[调试] 文件删除成功: {file_path}")
                    else:
                        if self.debug:
                            print(f"[调试] 文件删除失败: {file_path}")
                    
                    return success
                elif response.status_code == 404:
                    if self.debug:
                        print(f"[调试] 文件不存在: {file_path}")
                    return False
                elif response.status_code == 401:
                    if self.debug:
                        print(f"[调试] 未授权，请检查令牌是否有效")
                    return False
                elif response.status_code == 403:
                    if self.debug:
                        print(f"[调试] 权限不足或API限流")
                    return False
                else:
                    if self.debug:
                        print(f"[调试] 获取文件信息失败，响应状态: {response.status_code}")
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return False
            
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"[调试] GitHub API连接错误: {e}")
                    print(f"[调试] 这可能是由于网络不稳定、API限流或GitHub服务器暂时不可用")
                
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return False
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] 删除文件错误: {e}")
                    import traceback
                    traceback.print_exc()
                return False
        
        if self.debug:
            print(f"[调试] 所有 {max_retries} 次尝试都失败了")
        return False
    
    def delete_backup(self, backup_folder, max_retries=3, retry_delay=2):
        """删除仓库中的备份文件夹，支持重试机制"""
        if self.debug:
            print(f"[调试] 删除备份 - 文件夹: {backup_folder}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 构建请求URL
                folder_url = f"{self.base_url}/contents/{backup_folder}"
                # GitHub API需要添加ref参数
                folder_url += "?ref=main"
                
                if self.debug:
                    print(f"[调试] 请求文件夹内容: {folder_url} (尝试 {retry_count + 1}/{max_retries})")
                
                response = requests.get(
                    folder_url,
                    headers=self.headers,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 获取文件夹内容响应状态: {response.status_code}")
                    print(f"[调试] 获取文件夹内容响应: {response.text}")
                
                if response.status_code == 200:
                    # 解析文件夹内容
                    files = response.json()
                    

                    
                    if self.debug:
                        print(f"[调试] 文件夹内容: {files}")
                    
                    # 删除文件夹中的所有文件
                    success = True
                    for file in files:
                        if file['type'] == 'file':
                            file_path = f"{backup_folder}/{file['name']}"
                            if self.debug:
                                print(f"[调试] 准备删除文件: {file_path}")
                            
                            if not self.delete_file(file_path, max_retries=2, retry_delay=1):
                                if self.debug:
                                    print(f"[调试] 删除文件失败: {file_path}")
                                success = False
                    
                    if self.debug:
                        print(f"[调试] 备份删除{'成功' if success else '失败'}")
                    
                    return success
                elif response.status_code == 404:
                    if self.debug:
                        print(f"[调试] 备份文件夹不存在: {backup_folder}")
                    return False
                elif response.status_code == 401:
                    if self.debug:
                        print(f"[调试] 未授权，请检查令牌是否有效")
                    return False
                elif response.status_code == 403:
                    if self.debug:
                        print(f"[调试] 权限不足或API限流")
                    return False
                else:
                    if self.debug:
                        print(f"[调试] 获取文件夹内容失败，响应状态: {response.status_code}")
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return False
            
            except requests.exceptions.ConnectionError as e:
                if self.debug:
                    print(f"[调试] GitHub API连接错误: {e}")
                    print(f"[调试] 这可能是由于网络不稳定、API限流或GitHub服务器暂时不可用")
                
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return False
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] 删除备份错误: {e}")
                    import traceback
                    traceback.print_exc()
                return False
    
    def delete_all_backups(self):
        """删除仓库中的所有备份"""
        if self.debug:
            print(f"[调试] 删除所有备份")
        
        try:
            # 获取所有备份文件夹
            backups = self.list_backups()
            
            if self.debug:
                print(f"[调试] 找到 {len(backups)} 个备份文件夹")
            
            if not backups:
                if self.debug:
                    print(f"[调试] 没有找到备份文件夹")
                return True
            
            # 逐个删除备份
            for backup in backups:
                if self.debug:
                    print(f"[调试] 开始删除备份: {backup}")
                
                if not self.delete_backup(backup):
                    if self.debug:
                        print(f"[调试] 删除备份失败: {backup}")
                    return False
            
            if self.debug:
                print(f"[调试] 所有备份删除成功")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[调试] 删除所有备份错误: {e}")
                import traceback
                traceback.print_exc()
            return False
    
    def upload_file(self, file_path, message, max_retries=3, retry_delay=2):
        """上传文件到仓库，支持重试机制"""
        if self.debug:
            print(f"[调试] 上传文件 - 文件路径: {file_path}")
        
        try:
            # 读取文件内容并编码为base64
            with open(file_path, 'rb') as f:
                content = f.read()
            
            import base64
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            if self.debug:
                print(f"[调试] 文件大小: {len(content)}字节")
            
            # 调用create_commit方法上传，传入重试参数
            return self.create_commit(file_path, encoded_content, message, max_retries=max_retries, retry_delay=retry_delay)
        
        except FileNotFoundError:
            if self.debug:
                print(f"[调试] 上传文件失败：文件不存在 {file_path}")
            return False
        except Exception as e:
            if self.debug:
                print(f"[调试] 上传文件错误: {e}")
                import traceback
                traceback.print_exc()
            return False
    
    def create_release(self, tag_name, name, body, prerelease=False, target_commitish="main", max_retries=3, retry_delay=2):
        """创建发布版本，支持重试机制"""
        if self.debug:
            print(f"[调试] 创建发布 - 标签名: {tag_name}, 名称: {name}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 构建发布数据
                release_data = {
                    "tag_name": tag_name,
                    "name": name,
                    "body": body,
                    "prerelease": prerelease,
                    "target_commitish": target_commitish
                }
                

                
                if self.debug:
                    print(f"[调试] 发布数据: {release_data}")
                
                # 发送请求
                url = f"{self.base_url}/releases"
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=release_data,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 创建发布响应状态: {response.status_code}")
                    print(f"[调试] 创建发布响应内容: {response.text}")
                
                if response.status_code == 201:
                    # 发布创建成功
                    return response.json()
                elif response.status_code == 409 and "already exists" in response.text:
                    # 标签已存在，获取现有发布
                    if self.debug:
                        print(f"[调试] 标签已存在，获取现有发布")
                    return self.get_release_by_tag(tag_name)
                else:
                    # 其他错误，重试
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 创建发布失败，等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return None
                
            except Exception as e:
                if self.debug:
                    print(f"[调试] 创建发布错误: {e}")
                    import traceback
                    traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 创建发布失败，等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return None
        
        return None
    
    def get_release_by_tag(self, tag_name, max_retries=3, retry_delay=2):
        """根据标签名获取发布信息，支持重试机制"""
        if self.debug:
            print(f"[调试] 获取发布 - 标签名: {tag_name}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                url = f"{self.base_url}/releases/tags/{tag_name}"
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 获取发布响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 获取发布失败，等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return None
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] 获取发布错误: {e}")
                    import traceback
                    traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 获取发布失败，等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return None
        
        return None
    
    def list_releases(self, max_retries=3, retry_delay=2):
        """获取发布列表，支持重试机制"""
        if self.debug:
            print(f"[调试] 获取发布列表")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                url = f"{self.base_url}/releases"
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=10
                )
                
                if self.debug:
                    print(f"[调试] 获取发布列表响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 获取发布列表失败，等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return []
            
            except Exception as e:
                if self.debug:
                    print(f"[调试] 获取发布列表错误: {e}")
                    import traceback
                    traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 获取发布列表失败，等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return []
        
        return []
    
    def upload_release_asset(self, release_id, file_path, max_retries=3, retry_delay=2):
        """上传发布附件，支持重试机制"""
        if self.debug:
            print(f"[调试] 上传发布附件 - 发布ID: {release_id}, 文件路径: {file_path}")
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 读取文件内容
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # 获取文件名
                file_name = Path(file_path).name
                content_type = "application/octet-stream"  # 默认MIME类型
                
                if self.debug:
                    print(f"[调试] 文件名: {file_name}, 文件大小: {len(file_content)}字节")
                
                # GitHub API
                url = f"https://uploads.github.com/repos/{self.owner}/{self.repo}/releases/{release_id}/assets?name={file_name}"
                headers = {
                    "Authorization": f"token {self.token}",
                    "Content-Type": content_type
                }
                response = requests.post(
                    url,
                    headers=headers,
                    data=file_content,
                    timeout=30  # 上传大文件需要更长超时
                )
                
                if self.debug:
                    print(f"[调试] 上传发布附件响应状态: {response.status_code}")
                    print(f"[调试] 上传发布附件响应内容: {response.text}")
                
                if response.status_code == 201 or response.status_code == 200:
                    return response.json()
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        if self.debug:
                            print(f"[调试] 上传发布附件失败，等待 {retry_delay} 秒后重试...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        return None
                
            except Exception as e:
                if self.debug:
                    print(f"[调试] 上传发布附件错误: {e}")
                    import traceback
                    traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    if self.debug:
                        print(f"[调试] 上传发布附件失败，等待 {retry_delay} 秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    return None
        
        return None