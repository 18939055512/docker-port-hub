"""
Docker 容器检测模块
执行 docker ps 命令，获取容器端口映射信息
"""
import subprocess
import re
import json


class DockerDetect:
    """检测 Docker 容器信息"""

    def __init__(self):
        self._container_cache = {}

    def detect_all(self):
        """
        执行 docker ps 获取所有运行中的容器映射信息
        返回: { host_port: {container_name, image, status} }
        """
        self._container_cache = {}
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print(f"[Docker] docker ps 执行失败: {result.stderr}")
                return self._container_cache

            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    container = json.loads(line)
                    self._parse_container(container)
                except json.JSONDecodeError:
                    continue

            print(f"[Docker] 检测到 {len(self._container_cache)} 个端口映射")
        except FileNotFoundError:
            print("[Docker] docker 命令未找到，跳过 Docker 检测")
        except subprocess.TimeoutExpired:
            print("[Docker] docker ps 超时")
        except Exception as e:
            print(f"[Docker] 检测异常: {e}")

        return self._container_cache

    def _parse_container(self, container):
        """解析单个容器的端口映射"""
        try:
            name = container.get('Names', '').replace('/', '')
            image = container.get('Image', '')
            state = container.get('State', '')
            ports_str = container.get('Ports', '')

            if not ports_str:
                return

            # 解析端口映射: 0.0.0.0:38080->8080/tcp
            for mapping in ports_str.split(','):
                mapping = mapping.strip()
                match = re.search(r'(\d+)->', mapping)
                if match:
                    host_port = int(match.group(1))
                    self._container_cache[host_port] = {
                        'container_name': name,
                        'image': image,
                        'status': state
                    }
        except Exception as e:
            print(f"[Docker] 解析容器信息失败: {e}")

    def get_container_info(self, port):
        """获取指定端口对应的容器信息"""
        return self._container_cache.get(port, {})

    def get_all_mappings(self):
        """获取所有容器端口映射"""
        return dict(self._container_cache)