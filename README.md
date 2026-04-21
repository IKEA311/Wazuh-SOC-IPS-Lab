# Wazuh-SOC-IPS-Lab
# Wazuh SOC 态势感知与自动化防御实战

> **核心亮点**：本项目实现了从检测到拦截的秒级闭环。当 Kali Linux 发起 SQL 注入攻击时，系统可在不经过人工干预的情况下，自动识别威胁并实时封禁攻击源。

## 🛡️ 项目背景
本项目基于分布式安全架构，模拟企业级 SOC（安全运营中心）的运作流程：
1. **监测**：Agent 监控 Docker 靶场日志。
2. **分析**：Manager 匹配规则引擎，识别高危攻击。
3. **响应**：Active Response 秒级下发防火墙阻断指令。
4. **呈现**：Dashboard 实时展示地理溯源与拦截数据。

## 📂 仓库指南
* `/configs`: 包含核心配置片段（Decoder/Rules/Manager）。
* `/scripts`: 自动化运维与自定义告警脚本。
* `/screenshots`: 包含系统运行全图及拦截证明。

## 📊 实验效果展示
![SOC Dashboard](./screenshots/dashboard_main.png)
*上图展示了实时攻击地图及拦截计数器。*

## 🧠 技术原理 (Deep Dive)
* **日志链路**：Docker Log -> Host Mount -> Wazuh Agent -> Manager Analysis.
* **封禁逻辑**：检测到 Rule ID 31103 (SQLi) -> 触发 firewall-drop -> 修改宿主机 iptables。
