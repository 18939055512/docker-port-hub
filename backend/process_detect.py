"""
进程检测模块
通过 netstat + /proc 识别监听端口的进程信息

原理：
1. 执行 netstat -tlnp 获取监听端口对应的 PID 和程序名
2. 从 /proc/<pid>/cmdline 读取完整命令行
3. 从 /proc/<pid>/cwd 读取工作目录（符号链接）
4. 根据命令行/workdir 生成可读的服务名称

名称生成优先级：
a. cmdline 中的脚本名（如 main.py → main）
b. workdir 目录名（如 /data/proVideoDownLoadTools → proVideoDownLoadTools）
c. 程序名（如 python / node）
"""
import os
import re
import subprocess


# 常见脚本扩展名，用于从 cmdline 提取应用脚本名
SCRIPT_EXTS = ('.py', '.cjs', '.js', '.ts', '.mjs')


class ProcessDetect:
    """检测监听端口的进程信息"""

    def __init__(self):
        self._process_cache = {}

    def detect_all(self):
        """
        检测所有监听端口的进程信息
        返回: { port: {pid, program, cmdline, service_name, workdir} }
        """
        self._process_cache = {}
        try:
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print(f"[Process] netstat 执行失败: {result.stderr}")
                return self._process_cache

            # 解析每一行: tcp 0 0 0.0.0.0:38081 0.0.0.0:* LISTEN 65372/python
            # 格式: <proto> <recv-q> <send-q> <local-addr>:<port> <foreign> <state> <pid>/<program>
            for line in result.stdout.split('\n'):
                match = re.search(
                    r'\S+:(\d+)\s+\S+\s+\S+\s+(\d+)/(\S+)',
                    line
                )
                if not match:
                    continue
                port, pid, program = match.groups()
                self._process_cache[int(port)] = self._collect(pid, program)

            print(f"[Process] 检测到 {len(self._process_cache)} 个监听进程")
        except FileNotFoundError:
            print("[Process] netstat 命令未找到，跳过进程检测")
        except subprocess.TimeoutExpired:
            print("[Process] netstat 超时")
        except Exception as e:
            print(f"[Process] 检测异常: {e}")

        return self._process_cache

    def _collect(self, pid, program):
        """收集单个进程的详细信息"""
        info = {'pid': int(pid), 'program': program, 'cmdline': '', 'workdir': '', 'service_name': ''}

        # 读取命令行 /proc/<pid>/cmdline（以 \0 分隔）
        cmdline_file = f'/proc/{pid}/cmdline'
        try:
            with open(cmdline_file, 'rb') as f:
                raw = f.read()
            parts = [p.decode('utf-8', errors='replace') for p in raw.split(b'\0') if p]
            info['cmdline'] = ' '.join(parts)
        except Exception:
            pass

        # 读取工作目录 /proc/<pid>/cwd（符号链接）
        try:
            info['workdir'] = os.path.realpath(f'/proc/{pid}/cwd')
        except Exception:
            pass

        info['service_name'] = self._derive_name(info)
        return info

    def _derive_name(self, info):
        """
        根据命令行和工作目录生成服务名称
        优先级: package.json name > 脚本名 > workdir 目录名 > 程序名
        """
        # 0. 优先读取项目 package.json 的 name（最精确，如 tmux-web-server）
        name = self._name_from_package_json(info['workdir'])
        if name:
            return name

        # 1. 从 cmdline 提取脚本名
        name = self._name_from_cmdline(info['cmdline'])
        if name:
            return name

        # 2. 从 workdir 提取目录名
        name = self._name_from_workdir(info['workdir'])
        if name:
            return name

        # 3. 兜底使用程序名
        return info['program'] or f"pid-{info['pid']}"

    def _name_from_package_json(self, workdir):
        """优先读取项目 package.json 中的 name 字段"""
        if not workdir:
            return ''
        pkg_file = os.path.join(workdir, 'package.json')
        try:
            if os.path.isfile(pkg_file):
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                name = (data.get('name') or '').strip()
                return name
        except Exception:
            pass
        return ''

    def _name_from_cmdline(self, cmdline):
        """从命令行提取脚本名，如 'python /data/x/main.py' → 'x'"""
        if not cmdline:
            return ''
        parts = cmdline.split()
        # 跳过解释器本身
        interpreters = ('python', 'python3', 'node', '/usr/bin/node', 'java', 'sh', 'bash')
        # 跳过 node 加载器相关参数及其值路径
        skip_next = False
        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue
            if part in interpreters:
                continue
            # 跳过 node 加载器参数及其值（--require/--import/--loader/file://）
            if part in ('--require', '--import', '--loader'):
                skip_next = True
                continue
            if part.startswith('--') or part.startswith('file://'):
                continue
            # 提取脚本名（支持 .py .js .cjs .ts .mjs）
            if part.endswith(SCRIPT_EXTS):
                path = part
                base = os.path.basename(path)
                # 通用脚本名（app.py/main.py）回退到父目录名
                if base in ('app.py', 'main.py'):
                    parent = os.path.basename(os.path.dirname(path))
                    if parent:
                        return parent
                    continue
                # 忽略 node_modules 内部加载器（如 tsx/dist/preflight.cjs）
                if '/node_modules/' in path:
                    continue
                return os.path.splitext(base)[0]
            # 处理 node_modules/.bin/xxx 路径
            if '/node_modules/.bin/' in part:
                return os.path.basename(part)
            # 跳过短参数（-x, --xxx）
            if part.startswith('-') and len(part) > 1:
                continue
            if len(part) < 3:
                continue
            # 其他可执行路径
            if '/' in part:
                base = os.path.basename(part)
                if base not in interpreters:
                    return base
        return ''

    def _name_from_workdir(self, workdir):
        """从工作目录提取目录名"""
        if not workdir:
            return ''
        base = os.path.basename(workdir.rstrip('/'))
        # 忽略根目录/常见父级目录
        if base in ('/', 'home', 'root', 'data', 'opt', 'usr', 'var', 'srv'):
            return ''
        return base

    def get_process_info(self, port):
        """获取指定端口的进程信息"""
        return self._process_cache.get(port, {})

    def get_all_mappings(self):
        """获取所有端口进程映射"""
        return dict(self._process_cache)