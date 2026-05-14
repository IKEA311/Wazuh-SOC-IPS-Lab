# 🛡️ Purple Team Lab — 企业级全栈攻防模拟实验室

<p align="center">
  <img src="docs/screenshots/环境拓扑图.png" alt="网络拓扑图" width="800">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-blue">
  <img src="https://img.shields.io/badge/SIEM-Wazuh-5391FE">
  <img src="https://img.shields.io/badge/EDR-Sysmon-FF6F00">
  <img src="https://img.shields.io/badge/Attack-Kali%20Linux-red">
  <img src="https://img.shields.io/badge/Automation-Python-3776AB">
  <img src="https://img.shields.io/badge/Container-Docker-2496ED">
</p>

---

## 📋 项目概述

基于 **Wazuh SIEM** 搭建的企业级安全监控架构，在虚拟化环境中模拟真实内网攻防场景。从 **攻击者（Kali）** 视角实施渗透测试，再切换至 **蓝队视角** 通过 Sysmon 日志溯源攻击链路、编写自定义检测规则、开发自动化响应脚本，形成完整的 **紫队（Purple Team）** 攻防闭环。

## 🎯 核心目标

| 目标 | 说明 |
|------|------|
| 攻防闭环 | 攻击→日志采集→规则检测→告警→自动阻断，全流程可复现 |
| 规则调优 | 基于 ATT&CK 框架编写自定义 Wazuh 规则，降低误报/漏报 |
| 自动化响应 | 将 MTTR（平均响应时间）压缩至 2 秒以内 |

## 🏗️ 环境架构

| 角色 | 主机名 | IP 地址 | 操作系统 | 用途 |
|------|--------|---------|----------|------|
| ⚫ SIEM 服务器 | Wazuh-Server | `192.168.152.128` | Ubuntu Server | Wazuh Manager + 规则匹配 + 指令下发 |
| 🟡 靶机 | Ubuntu-Target | `192.168.152.129` | Ubuntu 24.04 | Wazuh Agent + Docker 靶场 |
| 🟢 攻击机 | Kali-Linux | `192.168.152.130` | Kali Linux | SQL 注入、端口扫描等攻击 |
| 🔵 工作站 | Win7-Target | DHCP / 静态 | Windows 7 | 内网客户端 + Sysmon + Wazuh Agent |
| 📦 业务应用 | DVWA | Docker on :8080 | Docker Container | 在 Ubuntu 靶机 8080 端口运行 |

## 🔥 攻防演练链路

```
Kali-Linux (192.168.152.130)
  │
  ├── SQLi ──────► Ubuntu-Target:8080/DVWA
  │                   │
  │                   └──► Wazuh Agent ──► Wazuh Server (规则匹配) ──► 告警
  │
  ├── WebShell ──► Ubuntu-Target:8080/DVWA
  │                   │
  │                   └──► Wazuh Agent ──► Wazuh Server ──► 规则匹配
  │
  └── MS17-010 ──► Win7-Target
                      │
                      └──► Sysmon ──► Wazuh Agent ──► Wazuh Server ──► 自动封禁
```

## ✨ 核心成果

| 成果 | 详情 |
|------|------|
| ✅ 自定义检测规则 | 15+ 条 Wazuh 规则（SQLi、暴力破解、WebShell、MS17-010、异常进程） |
| ✅ 自动化响应 | Python API 自动封禁插件，`iptables` 阻断 < 2s |
| ✅ 日志采集 | Sysmon 内核级日志 + Wazuh FIM（文件完整性监控） |
| ✅ 渗透报告 | 覆盖"攻击留痕→日志分析→加固建议"完整闭环 |
| ✅ 代码开源 | 规则、脚本、配置全量开源 |


## 📚 文档导航

| 文档 | 内容 |
|------|------|
| [01-环境架构与拓扑](docs/01-环境架构与拓扑.md) | 网络拓扑设计、各组件角色与交互 |
| [02-环境搭建步骤](docs/02-环境搭建步骤.md) | 从零搭建 Wazuh + Sysmon + 靶机环境 |
| [03-渗透攻击测试](docs/03-渗透攻击测试.md) | SQLi、WebShell、MS17-010 实战操作 |
| [04-检测规则编写](docs/04-检测规则编写.md) | 自定义 Wazuh 规则的设计、编写与调试 |
| [05-自动化响应开发](docs/05-自动化响应开发.md) | Python API 自动封禁插件的完整开发过程 |
| [06-问题排查与调试](docs/06-问题排查与调试.md) | 踩坑记录与解决方案 |

## 📂 项目结构

```
Purple-Team-Lab/
├── README.md                       # 项目总览
├── docs/
│   ├── 01-环境架构与拓扑.md
│   ├── 02-环境搭建步骤.md
│   ├── 03-渗透攻击测试.md
│   ├── 04-检测规则编写.md
│   ├── 05-自动化响应开发.md
│   ├── 06-问题排查与调试.md
│   └── screenshots/                # 截图目录
│       ├── 环境拓扑图.png
│       ├── wazuh-dashboard.png
│       ├── sql注入测试.png
│       ├── webshell上传.png
│       ├── ms17-010攻击.png
│       ├── 规则告警展示.png
│       └── 自动封禁效果.png
├── rules/
│   ├── custom-bruteforce.xml       # 暴力破解检测规则
│   ├── custom-sqli.xml             # SQL 注入检测规则
│   ├── custom-webshell.xml         # WebShell 检测规则
│   ├── custom-ms17-010.xml         # MS17-010 永恒之蓝检测规则
│   └── custom-malicious-process.xml# 异常进程检测规则
├── scripts/
│   ├── auto-block-ip.py            # 自动封禁脚本
│   └── sysmon-config.xml           # Sysmon 配置文件
├── reports/
│   └── 渗透测试报告.md              # 完整渗透测试报告模板
└── assets/
    └── topology.drawio             # 拓扑图 drawio 源文件
```

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/<你的用户名>/Purple-Team-Lab.git
cd Purple-Team-Lab

# 2. 部署 Wazuh Manager（Docker 方式）
docker-compose -f docker/compose.yml up -d

# 3. 在各靶机安装 Wazuh Agent
# 详见 docs/02-环境搭建步骤.md

# 4. 部署自定义规则
cp rules/*.xml /var/ossec/etc/rules/
systemctl restart wazuh-manager

# 5. 部署自动封禁脚本
pip3 install wazuh
python3 scripts/auto-block-ip.py --daemon
```

## 🛠️ 技术栈

- **SIEM**: Wazuh 4.x (Manager + Indexer + Dashboard)
- **EDR**: Sysmon (Windows 内核级日志采集)
- **攻击**: Kali Linux (SQLMap, Metasploit, weevely)
- **开发**: Python 3 (Wazuh API SDK)
- **虚拟化**: VMware Workstation / VirtualBox
- **容器**: Docker + Docker Compose

## 📄 许可证

本项目仅供安全研究与教育用途。使用者需遵守当地法律法规，禁止将技术用于非法目的。

---

<p align="center">
  <b>紫队思维 · 以攻促防</b><br>
  如果你觉得这个项目对你有帮助，欢迎 ⭐ Star！
</p>
