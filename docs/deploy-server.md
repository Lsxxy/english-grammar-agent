# 服务器部署步骤

你的服务器 `2 vCPU / 2 GiB / 40 GiB` 足够运行第一版 agent。下面以 Ubuntu 为例。

## 1. 连接服务器

在云厂商控制台点“远程连接”，或者本地终端 SSH：

```bash
ssh root@47.94.15.202
```

如果是第一次连接，先更新系统：

```bash
apt update
apt install -y git python3 python3-venv python3-pip nginx
```

## 2. 上传项目

推荐先用 Git。把本地项目推到 GitHub/Gitee 后，在服务器执行：

```bash
cd /opt
git clone 你的仓库地址 grammar-agent
cd /opt/grammar-agent
```

如果暂时不用 Git，也可以用 `scp` 上传整个项目目录：

```bash
scp -r /Users/xxy/Documents/英语学习agent构建 root@47.94.15.202:/opt/grammar-agent
```

## 3. 安装 Python 依赖

```bash
cd /opt/grammar-agent
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

导入示例课程：

```bash
.venv/bin/python scripts/import_lessons.py examples/lessons.sample.json
```

## 4. 配置环境变量

```bash
cp deploy/env.production.example .env
nano .env
```

DeepSeek 配置示例：

```dotenv
LLM_PROVIDER=deepseek
LLM_API_KEY=你的_deepseek_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

飞书配置先填：

```dotenv
FEISHU_APP_ID=你的_app_id
FEISHU_APP_SECRET=你的_app_secret
FEISHU_VERIFICATION_TOKEN=你的_verification_token
```

`FEISHU_DEFAULT_RECEIVE_ID` 可以等你第一次给机器人发消息后，从服务日志里确认用户 `open_id` 再填。

## 5. 先本机启动测试

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个 SSH 窗口测试：

```bash
curl http://127.0.0.1:8000/health
```

看到下面结果说明后端正常：

```json
{"status":"ok"}
```

## 6. 配置 systemd 常驻运行

```bash
cp deploy/grammar-agent.service /etc/systemd/system/grammar-agent.service
systemctl daemon-reload
systemctl enable grammar-agent
systemctl start grammar-agent
systemctl status grammar-agent
```

查看日志：

```bash
journalctl -u grammar-agent -f
```

## 7. 配置 Nginx

先把模板里的 `grammar.example.com` 换成你的域名：

```bash
cp deploy/nginx.grammar-agent.conf /etc/nginx/sites-available/grammar-agent
nano /etc/nginx/sites-available/grammar-agent
ln -s /etc/nginx/sites-available/grammar-agent /etc/nginx/sites-enabled/grammar-agent
nginx -t
systemctl reload nginx
```

如果还没有域名，可以临时直接开放 `8000` 端口测试，但正式接飞书建议使用 HTTPS 域名。

## 8. 配置 HTTPS

如果域名已经解析到服务器公网 IP，安装 Certbot：

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名
```

完成后，飞书事件订阅地址填写：

```text
https://你的域名/feishu/events
```

## 9. 云服务器安全组

在云厂商控制台开放：

```text
22   SSH
80   HTTP
443  HTTPS
```

如果只是临时测试裸端口，再开放：

```text
8000
```

正式使用时不建议暴露 `8000`，让外部只访问 `443`。

## 10. 飞书后台配置

1. 创建企业自建应用。
2. 开启机器人能力。
3. 在“凭证与基础信息”复制 `App ID` 和 `App Secret`。
4. 在“事件订阅”复制 `Verification Token`。
5. 请求地址填 `https://你的域名/feishu/events`。
6. 订阅 `im.message.receive_v1`。
7. 发布或启用应用后，给机器人发 `/today` 测试。

## 常见问题

- 飞书验证失败：检查 `FEISHU_VERIFICATION_TOKEN` 是否和飞书后台一致。
- 收不到消息：检查事件订阅是否启用、Nginx 是否 reload、安全组是否开放 443。
- 主动推送失败：检查 `FEISHU_DEFAULT_RECEIVE_ID` 是否是你的 `open_id`。
- AI 没有回答：检查 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。
