Wazuh-SOC-IPS-Lab：基于容器化环境的自动化防御实战
项目定位：本项目不仅是一个 SOC 态势感知实验，更是一次针对 Docker 容器环境 下安全审计与自动化拦截（IPS）的深度调优实践。通过解决容器网络隔离、日志持久化挂载等复杂问题，实现了秒级的“检测-响应”闭环。

🏗️ 系统架构与拓扑 (Topology)
SOC Manager: Wazuh Server (192.168.152.128) - 核心大脑，负责规则匹配与指令下发。

Target Agent: Ubuntu Server 24.04 (192.168.152.129) - 部署 Wazuh Agent 与 Docker 靶场。

Attacker: Kali Linux (192.168.152.130) - 模拟 SQL 注入与扫描攻击。

Business App: DVWA (Docker Container) - 运行在宿主机 8080 端口。

📂 核心配置快照 (Key Configurations)
1. 自动化防御 (Active Response)
在 Manager 端 ossec.conf 中配置，针对 SQL 注入（Rule 31106, 31164）执行 10 秒自动封禁：

XML
<command>
  <name>firewall-drop</name>
  <executable>firewall-drop</executable>
  <expect>srcip</expect> <timeout_allowed>yes</timeout_allowed>
</command>

<active-response>
  <command>firewall-drop</command>
  <location>local</location>
  <rules_id>31103,31106,31164</rules_id>
  <timeout>10</timeout>
</active-response>
2. 日志链路重构
为了解决容器销毁导致日志丢失的问题，采用 Volume 挂载 + 路径监控：

Docker 启动命令：
docker run -d --name dvwa-lab -p 8080:80 -v /var/log/dvwa:/var/log/apache2 vulnerables/web-dvwa

Agent 监控配置：

XML
<localfile>
  <log_format>apache</log_format>
  <location>/var/log/dvwa/access.log</location> </localfile>
🛠️ 深度排障实录 (Advanced Troubleshooting)
这是本项目最具技术价值的部分，记录了在容器化环境中遇到的“坑”及解决方案：

1. Docker 网络层级的“防御失效”问题
现象：Wazuh 日志显示已触发 firewall-drop，但攻击者（Kali）依然能访问 Web。

深度分析：Wazuh 默认脚本修改的是 INPUT 链，而 Docker 流量通过 PREROUTING 直接进入了 FORWARD 链，绕过了标准防火墙策略。

解决建议：在生产环境中需修改脚本作用于 DOCKER-USER 链。手动验证命令：
sudo iptables -I DOCKER-USER -s 192.168.152.130 -j DROP

2. SSL_ERROR_RX_RECORD_TOO_LONG 协议报错
现象：重启 Docker 服务后，浏览器显示“建立安全连接失败”。

根本原因：由于浏览器 HSTS 缓存，自动将访问重定向至 https://...:8080。由于 DVWA 容器仅支持 HTTP 80 端口，导致协议头不匹配。

修复方法：清理缓存或强制手动指定 http:// 访问。

3. Dashboard 数据聚合延迟与过滤器偏置
现象：Threat Hunting 页面有 31164 告警，但 SOC-Center 仪表盘显示为 0。

排查过程：分析 DQL 查询语句，发现 Dashboard 预设 Metric 仅统计 Level > 12 的事件。

解决思路：自定义可视化图表（Visualizations），将 rule.id: 31164 纳入统计范畴。

📊 实验成果验证
攻击识别：Kali 发起 UNION SELECT 注入，Wazuh Dashboard 实时弹出红色告警（Rule 31164）。

自动阻断：执行 sudo tail -f /var/ossec/logs/active-responses.log 观测到 firewall-drop 指令下发。

状态恢复：设定的 10 秒 timeout 到期后，系统自动删除 iptables 规则，业务访问恢复。

💡 结语与思考
在容器化时代，传统的 SOC 部署不能仅仅依赖默认配置。通过本项目，我深刻体会到 容器网络驱动（Bridge Mode）与宿主机内核防火墙（Netfilter） 的交互逻辑是决定安全策略是否生效的关键。未来的优化方向将聚焦于直接在容器内构建 Sidecar 审计模式，以实现更细粒度的流量控制。
