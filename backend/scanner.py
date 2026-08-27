"""
端口扫描模块
通过 TCP 连接 + 探测数据双重检测端口是否开放

检测原理：
1. TCP 连接建立（connect_ex == 0）
2. 连接成功后发送 1 字节探测数据
3. 二次验证：
   - 收到 RST（连接被重置）→ 端口无应用监听，EMPTY
     （docker-proxy 转发到容器内无监听的端口时会出现此情况，
       此时 TCP 握手是成功的，但发数据会收到 RST，即"假阳性"）
   - 收到 EOF（recv 返回空字节，对端干净关闭，无数据）→ 端口无应用监听，EMPTY
     （docker-proxy 在并发下偶发以 FIN 而非 RST 关闭空端口连接）
   - 收到实际数据或无 RST/EOF 超时 → 有应用监听，RUNNING
"""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


class PortScanner:
    """端口扫描器，使用 TCP 连接 + 探测数据检测端口状态"""

    # 最大并发扫描线程数
    # 注意：docker-proxy 在高并发下无法及时返回 RST（连接被转发到容器内
    # 无监听端口时），导致探测超时被误判为 RUNNING。
    # 实测：并发 3 结果准确，并发 5 仍偶有波动，并发 10+ 出现大量假阳性。
    MAX_WORKERS = 3
    # 连接超时时间（秒）
    CONNECT_TIMEOUT = 2
    # 探测等待时间（秒）：连接成功后等待数据/RST/EOF
    # docker-proxy 在并发下偶发延迟 RST/EOF，1s 不够，设为 2s
    PROBE_TIMEOUT = 2

    def __init__(self, start_port, end_port, host='127.0.0.1'):
        self.start_port = start_port
        self.end_port = end_port
        self.host = host

    def scan_port(self, port):
        """
        扫描单个端口
        返回: (port, is_open)
        is_open 判定规则：
        - 连接失败 → False
        - 连接成功但发送/接收探测数据时收到 RST → False（无应用监听）
        - 连接成功但接收探测数据时收到 EOF（b''，对端关闭）→ False（无应用监听）
        - 连接成功且探测无 RST/EOF（收到数据或超时）→ True
        """
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.CONNECT_TIMEOUT)
            result = sock.connect_ex((self.host, port))
            if result != 0:
                # 连接被拒/超时 → 未开放
                return port, False

            # 连接成功，进入二次验证：发送探测数据
            # 若目标端口无应用监听（如 docker-proxy 转发空端口），
            # 对端内核会立即回 RST，sendall/recv 会抛 ConnectionReset/BrokenPipe
            sock.settimeout(self.PROBE_TIMEOUT)
            try:
                sock.sendall(b'\x00')
            except (ConnectionResetError, BrokenPipeError, OSError):
                # 收到 RST → 无应用监听（假阳性），判定为空闲
                return port, False

            try:
                data = sock.recv(1)
                if not data:
                    # 收到 EOF（对端干净关闭连接）→ 无应用监听
                    # docker-proxy 在并发下偶发以 FIN 而非 RST 关闭空端口
                    return port, False
                # 收到实际数据 → 有应用监听
                return port, True
            except socket.timeout:
                # 超时但没有 RST/EOF → 有应用监听（只是不响应探测数据）
                return port, True
            except (ConnectionResetError, BrokenPipeError, OSError):
                # 收到 RST → 无应用监听（假阳性），判定为空闲
                return port, False
        except socket.timeout:
            # 连接超时 → 未开放
            return port, False
        except Exception:
            return port, False
        finally:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass

    def scan_all(self):
        """
        扫描所有端口
        返回: { port: True/False }
        """
        ports = range(self.start_port, self.end_port + 1)
        total = len(ports)
        results = {}
        completed = 0

        print(f"[Scanner] 开始扫描端口 {self.start_port}-{self.end_port} (共 {total} 个)")

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {executor.submit(self.scan_port, port): port for port in ports}

            for future in as_completed(futures):
                port, is_open = future.result()
                results[port] = is_open
                completed += 1
                if completed % 50 == 0:
                    print(f"[Scanner] 扫描进度: {completed}/{total}")

        open_count = sum(1 for v in results.values() if v)
        print(f"[Scanner] 扫描完成: 开放 {open_count} 个, 关闭 {total - open_count} 个")
        return results