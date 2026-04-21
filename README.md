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
故障排除指南 (Troubleshooting)
在搭建这套分布式 SOC 系统的过程中，我遇到并解决了以下核心技术问题。这些经验对于维护生产环境中的 Wazuh 具有参考价值：

1. Agent 状态显示为 Disconnected 或 Never connected
现象：在 Dashboard 中看不到 Agent 节点，或者执行 agent_control -l 列表为空。

排查步骤：
网络连接：检查服务端 1514 (UDP) 和 1515 (TCP) 端口是否开放。

密钥校验：确认 Agent 端 /var/ossec/etc/client.keys 里的密钥与服务端生成的密钥一致。

服务状态：执行 systemctl status wazuh-agent 查看是否有 Error 111 (Connection refused) 报错。

解决方法：重新执行密钥导入命令 bin/manage_agents -i <key> 并重启服务。

2. 日志已产生但 Dashboard 无数据
现象：Docker 日志在宿主机 /var/log/dvwa/access.log 已经更新，但 Dashboard 没有任何 Web 告警。

排查步骤：

权限检查：检查该日志文件是否具有读取权限。Wazuh Agent 运行用户（通常是 root 或 wazuh）必须能访问该路径。

格式验证：在 ossec.conf 中确认 <log_format> 是否被正确设为 apache。

分析引擎检查：查看服务端日志 /var/ossec/logs/ossec.log，确认是否有 Archives 处理延迟。

解决方法：执行 chmod 644 /var/log/dvwa/access.log 并确保 ossec.conf 中的路径完全正确。

3. Active Response 脚本未触发拦截
现象：发生了 SQL 注入且规则已报警（Level 10），但攻击者 IP 依然可以访问网页。

排查步骤：

指令确认：检查服务端日志 /var/ossec/logs/active-responses.log，看是否有 firewall-drop 执行记录。

脚本路径：确认 Agent 端 /var/ossec/active-response/bin/ 下是否存在对应的执行脚本。

防火墙依赖：确认宿主机是否安装了 iptables 或 nftables，因为内置脚本依赖这些底层工具。

解决方法：在 ossec.conf 中显式指定 <location>local</location> 以确保指令下发到正确的 Agent。
