# Wazuh-SOC-IPS-Lab：基于容器化环境的自动化防御实战

> **项目定位**：本项目不仅是一个 SOC 态势感知实验，更是一次针对 **Docker 容器环境** 下安全审计与自动化拦截（IPS）的深度调优实践。通过解决容器网络隔离、日志持久化挂载等复杂问题，实现了秒级的“检测-响应”闭环。

---

## 🏗️ 系统架构与拓扑 (Topology)

* **SOC Manager**: Wazuh Server (192.168.152.128) - 核心大脑，负责规则匹配与指令下发。
* **Target Agent**: Ubuntu Server 24.04 (192.168.152.129) - 部署 Wazuh Agent 与 Docker 靶场。
* **Attacker**: Kali Linux (192.168.152.130) - 模拟 SQL 注入与扫描攻击。
* **Business App**: DVWA (Docker Container) - 运行在宿主机 `8080` 端口。

---

## 📂 核心配置快照 (Key Configurations)

### 1. 自动化防御 (Active Response)
在 Manager 端 `ossec.conf` 中配置，针对 SQL 注入（Rule 31106, 31164）执行 10 秒自动封禁：

```xml
<command>
  <name>firewall-drop</name>
  <executable>firewall-drop</executable>
  <expect>srcip</expect>
  <timeout_allowed>yes</timeout_allowed>
</command>

<active-response>
  <command>firewall-drop</command>
  <location>local</location>
  <rules_id>31103,31106,31164</rules_id>
  <timeout>10</timeout>
</active-response>
```
Markdown
### 2. 日志链路重构
为了解决容器销毁导致日志丢失的问题，采用 **Volume 挂载 + 路径监控**：

**Docker 启动命令：**
```bash
docker run -d --name dvwa-lab -p 8080:80 -v /var/log/dvwa:/var/log/apache2 vulnerables/web-dvwa
Agent 监控配置：

XML
<localfile>
  <log_format>apache</log_format>
  <location>/var/log/dvwa/access.log</location>
</localfile>
```
🛠️ 深度排障实录 (Advanced Troubleshooting)
1. Docker 网络层级的“防御失效”
现象：Wazuh 触发了 firewall-drop，但 Kali 依然能访问 Web。

分析：Docker 流量走的是 FORWARD 链，绕过了 INPUT 链。

解决：应作用于 DOCKER-USER 链。

手动验证命令：

```Bash
sudo iptables -I DOCKER-USER -s 192.168.152.130 -j DROP

```
