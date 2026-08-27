"""
端口配置文件管理器
读取 config/ports.json 中的应用信息配置
"""
import json
import os

# 配置文件路径（相对于项目根目录或绝对路径）
CONFIG_DIR = os.environ.get('CONFIG_DIR', '/app/config')
PORTS_FILE = os.path.join(CONFIG_DIR, 'ports.json')


class ConfigManager:
    """管理 ports.json 中的应用信息"""

    def __init__(self):
        self._ports_config = {}
        self._load_config()

    def _load_config(self):
        """加载 ports.json 到内存"""
        self._ports_config = {}
        if not os.path.exists(PORTS_FILE):
            print(f"[Config] 配置文件不存在: {PORTS_FILE}，使用空配置")
            return

        try:
            with open(PORTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    port = item.get('port')
                    if port:
                        self._ports_config[port] = {
                            'name': item.get('name', ''),
                            'remark': item.get('remark', ''),
                            'category': item.get('category', '')
                        }
            print(f"[Config] 已加载 {len(self._ports_config)} 条应用配置")
        except Exception as e:
            print(f"[Config] 加载配置文件失败: {e}")

    def get_port_info(self, port):
        """获取指定端口的配置信息"""
        return self._ports_config.get(port, {})

    def get_all_configs(self):
        """获取所有配置的端口信息"""
        return dict(self._ports_config)

    def reload(self):
        """重新加载配置（用于热更新）"""
        self._load_config()