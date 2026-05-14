#!/usr/bin/env python3
"""
Purple Team Lab - 自动封禁插件
===============================
功能:  监听 Wazuh 告警，对高危攻击 IP 自动执行 iptables 封禁
架构:  Wazuh API 轮询 → 解析告警 → SSH 执行 iptables → 记录日志
MTTR:  < 2 秒（从告警产生到 iptables 封禁生效）

使用方式:
  python3 auto-block-ip.py                    # 前台运行
  python3 auto-block-ip.py --daemon           # 后台守护进程
  python3 auto-block-ip.py --test             # 测试模式（不实际封禁）

依赖:
  pip3 install wazuh paramiko urllib3

作者: Liu Hong | Purple Team Lab
"""

import json
import logging
import subprocess
import sys
import time
import os
import argparse
import re
import ipaddress
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════
# 配置区（根据实际环境修改）
# ═══════════════════════════════════════════════════════════════════

CONFIG = {
    "wazuh": {
        "host": "192.168.152.128",
        "port": 55000,
        "user": "wazuh-api",
        "password": "P@ssw0rdPurple!",
        "protocol": "https",
    },
    "alert": {
        "min_level": 10,              # 封禁阈值：Level >= 10
        "check_interval": 2,          # 轮询间隔（秒）
        "block_duration": 3600,       # 封禁时长（秒）= 1h
    },
    "targets": [                      # 需要执行封禁的主机
        {"host": "192.168.152.129", "user": "root", "port": 22,
         "via": "ssh"},
        {"host": "192.168.152.128", "user": "root", "port": 22,
         "via": "local"},  # Wazuh Server 自身用本地 iptables
    ],
    "whitelist": [                    # 永不封禁的网段
        "192.168.152.0/24",
        "10.0.0.0/8",
        "172.16.0.0/12",
    ],
    "log_file": "/var/log/purple-team/auto-block.log",
}

# ═══════════════════════════════════════════════════════════════════
# 日志初始化
# ═══════════════════════════════════════════════════════════════════

def setup_logging(log_file):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

# ═══════════════════════════════════════════════════════════════════
# 核心功能
# ═══════════════════════════════════════════════════════════════════

class BlockCache:
    """封禁记录缓存，防止重复封禁和管理过期记录"""

    def __init__(self, duration):
        self.cache = {}
        self.duration = duration

    def add(self, ip, alert_id, rule, count):
        self.cache[ip] = {
            "blocked_at": datetime.now(),
            "alert_id": alert_id,
            "rule": rule,
            "hosts_blocked": count,
        }

    def exists(self, ip):
        return ip in self.cache

    def clean_expired(self):
        now = datetime.now()
        expired = [
            ip for ip, info in self.cache.items()
            if now - info["blocked_at"] > timedelta(seconds=self.duration)
        ]
        for ip in expired:
            del self.cache[ip]
            logging.info(f"封禁记录已过期: {ip}")
        return expired


def is_whitelisted(ip, whitelist):
    """检查 IP 是否在白名单中"""
    try:
        addr = ipaddress.ip_address(ip)
        for net in whitelist:
            if addr in ipaddress.ip_network(net, strict=False):
                return True
    except ValueError:
        pass
    return False


def extract_attacker_ip(alert):
    """
    从告警中提取攻击者 IP 地址
    多字段尝试 + 正则回退 + 白名单过滤
    """
    # 优先从 data 字段提取
    data = alert.get("data", {})
    for field in ["srcip", "src_ip", "src_ip_address", "src_addr"]:
        ip = data.get(field)
        if ip and isinstance(ip, str):
            return ip

    # 从 source 字段提取
    source = alert.get("source", {})
    ip = source.get("ip") or source.get("address")
    if ip:
        return ip

    # 从 full_log 正则提取
    full_log = alert.get("full_log", "")
    match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", full_log)
    if match:
        return match.group(1)

    return None


def fetch_alerts(api_client, last_timestamp, min_level):
    """从 Wazuh API 获取最新告警"""
    try:
        response = api_client.get("/alerts", params={
            "sort": "timestamp:desc",
            "limit": 50,
            "filters": json.dumps({"rule.level": f">={min_level}"}),
        })
        items = response.json().get("data", {}).get(
            "affected_items", []
        )
        new_alerts = [
            a for a in items
            if a.get("timestamp", "") > last_timestamp
        ]
        return new_alerts
    except Exception as e:
        logging.error(f"获取告警失败: {e}")
        return []


def block_ip_local(attacker_ip):
    """本地 iptables 封禁"""
    try:
        result = subprocess.run(
            ["iptables", "-C", "INPUT", "-s", attacker_ip, "-j", "DROP"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logging.info(f"[localhost] {attacker_ip} 已在封禁列表中，跳过")
            return True

        subprocess.run(
            ["iptables", "-A", "INPUT", "-s", attacker_ip, "-j", "DROP"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["logger", "-t", "AUTO-BLOCK",
             f"PurpleTeam auto-blocked malicious IP: {attacker_ip}"],
            capture_output=True
        )
        logging.info(f"[localhost] ✅ 成功封禁 {attacker_ip}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"[localhost] iptables 封禁失败: {e.stderr.decode()}")
        return False
    except Exception as e:
        logging.error(f"[localhost] 封禁异常: {e}")
        return False


def block_ip_ssh(host_info, attacker_ip, test_mode=False):
    """通过 SSH 在远程主机上执行 iptables 封禁"""
    if test_mode:
        logging.info(
            f"[TEST] 模拟封禁 {attacker_ip} @ "
            f"{host_info['host']}（不实际操作）"
        )
        return True

    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host_info["host"],
            username=host_info["user"],
            port=host_info.get("port", 22),
            password=host_info.get("password"),
            key_filename=host_info.get("key_file",
                                       "/root/.ssh/auto_block"),
            timeout=10,
        )

        # 检查是否已封禁
        check = f"iptables -C INPUT -s {attacker_ip} -j DROP 2>/dev/null && echo 'EXISTS' || echo 'NOT_EXISTS'"
        _, stdout, _ = ssh.exec_command(check)
        if stdout.read().decode().strip() == "EXISTS":
            logging.info(
                f"[{host_info['host']}] {attacker_ip} 已在封禁列表中，跳过"
            )
            ssh.close()
            return True

        # 执行封禁
        _, stdout, stderr = ssh.exec_command(
            f"iptables -A INPUT -s {attacker_ip} -j DROP"
        )
        error = stderr.read().decode().strip()
        if error:
            logging.error(f"[{host_info['host']}] 封禁失败: {error}")
            ssh.close()
            return False

        # 记录日志
        ssh.exec_command(
            f"logger -t 'AUTO-BLOCK' "
            f"'PurpleTeam auto-blocked malicious IP: {attacker_ip}'"
        )
        ssh.close()
        logging.info(f"[{host_info['host']}] ✅ 成功封禁 {attacker_ip}")
        return True

    except ImportError:
        logging.error("paramiko 未安装，请执行: pip3 install paramiko")
        return False
    except Exception as e:
        logging.error(f"[{host_info['host']}] SSH 封禁失败: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════════════════════════

def main_loop(test_mode=False):
    """主轮询循环"""
    cfg = CONFIG
    cache = BlockCache(cfg["alert"]["block_duration"])

    logging.info("=" * 50)
    logging.info("🚀 Purple Team Auto-Block 启动")
    logging.info(f"告警阈值: Level >= {cfg['alert']['min_level']}")
    logging.info(f"检查间隔: {cfg['alert']['check_interval']}s")
    logging.info(f"封禁时长: {cfg['alert']['block_duration']}s")
    if test_mode:
        logging.info("🔬 测试模式: 不会执行实际封禁")
    logging.info("=" * 50)

    # ── 🐞 Bugfix: 自签名证书跳过验证 ──
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ── Wazuh API 连接 ──
    from wazuh import Wazuh

    wc = cfg["wazuh"]
    while True:
        try:
            api = Wazuh(
                host=wc["host"], protocol=wc["protocol"],
                port=wc["port"], user=wc["user"],
                password=wc["password"],
            )
            # 测试连接
            api.get("/agents", params={"limit": 1})
            logging.info("✅ Wazuh API 连接成功")
            break
        except Exception as e:
            logging.warning(f"等待 Wazuh API 连接... ({e})")
            time.sleep(5)

    last_timestamp = datetime.utcnow().strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    while True:
        try:
            # 1. 清理过期封禁
            cache.clean_expired()

            # 2. 获取告警
            alerts = fetch_alerts(
                api, last_timestamp, cfg["alert"]["min_level"]
            )

            for alert in alerts:
                ts = alert.get("timestamp", "")
                if ts > last_timestamp:
                    last_timestamp = ts

                # 3. 提取攻击者 IP
                attacker_ip = extract_attacker_ip(alert)
                if not attacker_ip:
                    continue

                # 4. 白名单过滤
                if is_whitelisted(attacker_ip, cfg["whitelist"]):
                    logging.debug(
                        f"跳过白名单 IP: {attacker_ip}"
                    )
                    continue

                # 5. 重复检查
                if cache.exists(attacker_ip):
                    continue

                # 6. 执行封禁
                rule_desc = alert.get("rule", {}).get(
                    "description", "unknown"
                )
                alert_id = alert.get("id", "unknown")
                logging.info(
                    f"⚠️  检测到攻击 - IP: {attacker_ip}, "
                    f"规则: {rule_desc} (ID: {alert_id})"
                )

                success = 0
                for target in cfg["targets"]:
                    if target["via"] == "ssh":
                        if block_ip_ssh(target, attacker_ip, test_mode):
                            success += 1
                    elif target["via"] == "local":
                        if block_ip_local(attacker_ip):
                            success += 1

                cache.add(
                    attacker_ip, alert_id, rule_desc, success
                )
                logging.info(
                    f"🔒 封禁完成 - {attacker_ip}, "
                    f"成功封禁 {success}/{len(cfg['targets'])} 台主机"
                )

            time.sleep(cfg["alert"]["check_interval"])

        except KeyboardInterrupt:
            logging.info("收到 Ctrl+C，退出")
            sys.exit(0)
        except Exception as e:
            logging.error(f"主循环异常: {e}", exc_info=True)
            time.sleep(cfg["alert"]["check_interval"] * 2)


def main():
    parser = argparse.ArgumentParser(
        description="Purple Team Lab - Wazuh 自动封禁插件"
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="作为守护进程运行（需 systemd 支持）"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="测试模式 - 轮询告警但不执行实际封禁"
    )
    args = parser.parse_args()

    setup_logging(CONFIG["log_file"])
    main_loop(test_mode=args.test)


if __name__ == "__main__":
    main()
