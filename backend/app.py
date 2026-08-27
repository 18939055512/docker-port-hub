"""
Docker Port Hub - 主应用
Docker 端口应用导航管理平台
"""
import os
import re
import threading
import time

import yaml
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config_manager import ConfigManager
from docker_detect import DockerDetect
from process_detect import ProcessDetect
from scanner import PortScanner

# 配置文件路径
CONFIG_DIR = os.environ.get('CONFIG_DIR', '/app/config')
APP_YML = os.path.join(CONFIG_DIR, 'application.yml')

app = Flask(__name__, static_folder=None)
CORS(app)

# ============ 配置加载 ============

def load_app_config():
    """加载 application.yml 配置"""
    default_config = {
        'server': {'port': 38082},
        'port': {'start': 38080, 'end': 38579, 'host': '127.0.0.1'},
        'access': {'prefix': 'http://127.0.0.1'},
        'scan': {'interval': 30}
    }
    if not os.path.exists(APP_YML):
        print(f"[App] 配置文件不存在: {APP_YML}，使用默认配置")
        return default_config
    try:
        with open(APP_YML, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
        # 合并默认配置
        for key in default_config:
            if key not in cfg:
                cfg[key] = default_config[key]
            else:
                for sub_key in default_config[key]:
                    if sub_key not in cfg[key]:
                        cfg[key][sub_key] = default_config[key][sub_key]
        print(f"[App] 配置加载成功: {APP_YML}")
        return cfg
    except Exception as e:
        print(f"[App] 配置加载失败: {e}，使用默认配置")
        return default_config


CONFIG = load_app_config()

SERVER_PORT = int(CONFIG['server']['port'])
PORT_START = int(CONFIG['port']['start'])
PORT_END = int(CONFIG['port']['end'])
SCAN_HOST = CONFIG['port'].get('host', '127.0.0.1')
ACCESS_PREFIX = CONFIG['access']['prefix']
SCAN_INTERVAL = int(CONFIG['scan'].get('interval', 30))


def resolve_scan_host():
    """
    解析扫描目标主机
    - 如果配置了 host，优先使用配置
    - 未配置或为 127.0.0.1 时，从 access.prefix 提取 IP 作为扫描主机
      （后端在容器中运行时，127.0.0.1 指向容器自身，无法扫描宿主机）
    """
    global SCAN_HOST
    if SCAN_HOST not in ('127.0.0.1', 'localhost'):
        return SCAN_HOST
    match = re.search(r'https?://([^:/]+)', ACCESS_PREFIX)
    if match:
        host = match.group(1)
        print(f"[App] 从访问前缀解析扫描主机: {host}")
        return host
    return SCAN_HOST


SCAN_HOST = resolve_scan_host()

# ============ 服务初始化 ============

config_manager = ConfigManager()
docker_detect = DockerDetect()
process_detect = ProcessDetect()
port_scanner = PortScanner(PORT_START, PORT_END, SCAN_HOST)

# 扫描结果缓存: { port: {status, name, remark, category, url, docker, image, container_status, process, process_cmd, process_dir} }
scan_cache = {}
cache_lock = threading.Lock()
first_scan_done = threading.Event()


def perform_scan():
    """执行一次完整扫描"""
    global scan_cache

    # 1. 扫描端口
    scan_result = port_scanner.scan_all()

    # 2. 检测 Docker 容器
    docker_mappings = docker_detect.detect_all()

    # 3. 检测进程（从 netstat + /proc 识别服务）
    process_mappings = process_detect.detect_all()

    # 4. 读取端口配置
    port_configs = config_manager.get_all_configs()

    # 5. 合并数据
    # 名称优先级: ports.json 配置 > 进程识别 > docker 容器名 > 未知应用
    new_cache = {}
    for port in range(PORT_START, PORT_END + 1):
        is_open = scan_result.get(port, False)
        docker_info = docker_mappings.get(port, {})
        app_config = port_configs.get(port, {})
        proc_info = process_mappings.get(port, {})

        # 生成名称
        name = app_config.get('name') or proc_info.get('service_name') or \
               docker_info.get('container_name') or '未知应用'

        # 进程识别信息（仅对 RUNNING 端口有效）
        proc_name = proc_info.get('service_name', '')
        proc_cmdline = proc_info.get('cmdline', '')
        proc_workdir = proc_info.get('workdir', '')

        item = {
            'port': port,
            'status': 'RUNNING' if is_open else 'EMPTY',
            'name': name,
            'remark': app_config.get('remark', '') or proc_cmdline,
            'category': app_config.get('category', ''),
            'url': f"{ACCESS_PREFIX}:{port}" if is_open else "",
            'docker': docker_info.get('container_name', ''),
            'image': docker_info.get('image', ''),
            'container_status': docker_info.get('status', ''),
            'process': proc_name,
            'process_cmd': proc_cmdline,
            'process_dir': proc_workdir
        }
        new_cache[port] = item

    with cache_lock:
        scan_cache = new_cache
    first_scan_done.set()

    running_count = sum(1 for v in new_cache.values() if v['status'] == 'RUNNING')
    print(f"[Scan] 完成: 运行中 {running_count} 个")


def scan_loop():
    """后台定时扫描循环"""
    while True:
        try:
            perform_scan()
        except Exception as e:
            print(f"[Scan] 扫描异常: {e}")
        time.sleep(SCAN_INTERVAL)


def start_background_scan():
    """启动后台扫描线程"""
    thread = threading.Thread(target=scan_loop, daemon=True)
    thread.start()
    print(f"[App] 后台扫描已启动, 周期 {SCAN_INTERVAL}s")
    # 非阻塞等待首次扫描完成
    first_scan_done.wait(timeout=15)


# ============ REST API ============

@app.route('/api/ports', methods=['GET'])
def get_ports():
    """获取所有端口状态"""
    with cache_lock:
        ports = list(scan_cache.values()) if scan_cache else []

    # 排序: 已占用在前, 未占用在后; 端口升序
    ports.sort(key=lambda x: (x['status'] == 'EMPTY', x['port']))
    return jsonify(ports)


@app.route('/api/ports/search', methods=['GET'])
def search_ports():
    """
    搜索端口
    支持: 端口号 / 应用名称 / Docker容器名
    """
    keyword = (request.args.get('keyword', '') or '').strip().lower()
    category = (request.args.get('category', '') or '').strip()
    status_filter = (request.args.get('status', '') or '').strip().upper()

    with cache_lock:
        ports = list(scan_cache.values()) if scan_cache else []

    result = []
    for item in ports:
        if keyword and keyword not in str(item['port']) and \
           keyword not in item['name'].lower() and \
           keyword not in item['docker'].lower() and \
           keyword not in item['process'].lower() and \
           keyword not in item['process_dir'].lower():
            continue
        if category and item['category'] != category:
            continue
        if status_filter and item['status'] != status_filter:
            continue
        result.append(item)

    # 按占用状态排序：已占用优先
    result.sort(key=lambda x: (x['status'] == 'EMPTY', x['port']))
    return jsonify(result)


@app.route('/api/ports/<int:port>', methods=['GET'])
def get_port(port):
    """获取单个端口状态"""
    with cache_lock:
        item = scan_cache.get(port)
    if not item:
        return jsonify({'error': '端口不存在'}), 404
    return jsonify(item)


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取系统配置信息"""
    return jsonify({
        'serverPort': SERVER_PORT,
        'portStart': PORT_START,
        'portEnd': PORT_END,
        'accessPrefix': ACCESS_PREFIX,
        'scanInterval': SCAN_INTERVAL,
        'categories': sorted(set(v.get('category', '') for v in
                                 config_manager.get_all_configs().values() if v.get('category')))
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    with cache_lock:
        ports = list(scan_cache.values()) if scan_cache else []
    total = len(ports)
    running = sum(1 for v in ports if v['status'] == 'RUNNING')
    empty = total - running
    return jsonify({
        'total': total,
        'running': running,
        'empty': empty
    })


# ============ 静态资源服务（前端构建产物） ============

FRONTEND_DIST = os.environ.get('FRONTEND_DIST', os.path.join(os.path.dirname(__file__), 'static'))


@app.route('/', methods=['GET'])
def index():
    """首页"""
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/<path:path>', methods=['GET'])
def static_files(path):
    """前端静态资源"""
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIST, path)
    # SPA 路由回退
    return send_from_directory(FRONTEND_DIST, 'index.html')


# ============ 启动 ============

if __name__ == '__main__':
    os.makedirs(CONFIG_DIR, exist_ok=True)
    start_background_scan()
    app.run(host='0.0.0.0', port=SERVER_PORT)