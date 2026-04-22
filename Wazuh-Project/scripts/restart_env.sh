#!/bin/bash

# =================================================================
# Project: Wazuh-SOC-IPS-Lab
# File: scripts/restart_env.sh
# Description: 一键重置 Docker 靶场环境与网络安全配置
# Author: Hong (IKEA311)
# =================================================================

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}[*] 开始初始化实验环境...${NC}"

# 1. 清理旧容器
echo -e "${GREEN}[1/5] 正在清理旧的 DVWA 容器...${NC}"
sudo docker stop dvwa-lab 2>/dev/null
sudo docker rm dvwa-lab 2>/dev/null

# 2. 修复防火墙与 Docker 网络
# 注意：此操作会恢复被 iptables -F/-X 破坏的 Docker 链
echo -e "${GREEN}[2/5] 正在重置 iptables 与 Docker 网络服务...${NC}"
sudo iptables -F DOCKER-USER 2>/dev/null
sudo systemctl restart docker

# 3. 准备日志持久化目录
echo -e "${GREEN}[3/5] 正在配置日志挂载路径与权限...${NC}"
LOG_DIR="/var/log/dvwa"
sudo mkdir -p $LOG_DIR
sudo chmod 777 $LOG_DIR
# 清空旧日志，确保实验数据新鲜
sudo truncate -s 0 $LOG_DIR/access.log 2>/dev/null

# 4. 启动容器
echo -e "${GREEN}[4/5] 正在部署 DVWA 容器 (Port: 8080)...${NC}"
sudo docker run -d \
  --name dvwa-lab \
  -p 8080:80 \
  -v $LOG_DIR:/var/log/apache2 \
  vulnerables/web-dvwa

# 5. 状态检查
echo -e "${GREEN}[5/5] 正在验证服务状态...${NC}"
sleep 3
if [ "$(sudo docker inspect -f '{{.State.Running}}' dvwa-lab)" == "true" ]; then
    echo -e "${GREEN}----------------------------------------------------------${NC}"
    echo -e "${GREEN}✅ 环境重置成功！${NC}"
    echo -e "🌐 访问地址: http://$(hostname -I | awk '{print $1}'):8080"
    echo -e "📜 日志路径: $LOG_DIR/access.log"
    echo -e "🛡️  提示: 请确保 Wazuh Agent 的 ossec.conf 已监控此路径。"
    echo -e "${GREEN}----------------------------------------------------------${NC}"
else
    echo -e "${RED}❌ 容器启动失败，请检查 Docker 日志。${NC}"
fi