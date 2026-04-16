# SkillLint Web Deployment

## 1. 启动参数

`skilllint-web` 现在支持以下启动参数：

```bash
skilllint-web --host 127.0.0.1 --port 18110
skilllint-web --host 0.0.0.0 --port 18110 --workers 2 --log-level info
skilllint-web --reload
```

支持的参数：

- `--host`
- `--port`
- `--reload`
- `--workers`
- `--log-level`

默认值：

- `host=127.0.0.1`
- `port=18110`
- `reload=false`
- `workers=1`
- `log_level=info`

## 2. 环境变量

也可以用环境变量配置：

```bash
export SKILLLINT_WEB_HOST=0.0.0.0
export SKILLLINT_WEB_PORT=18110
export SKILLLINT_WEB_RELOAD=false
export SKILLLINT_WEB_WORKERS=2
export SKILLLINT_WEB_LOG_LEVEL=info
skilllint-web
```

优先级：

1. CLI 参数
2. 环境变量
3. 默认值

## 3. 开发环境建议

本地开发建议：

```bash
skilllint-web --reload
```

特点：

- 自动重载
- 单进程
- 更适合调试而不是正式部署

注意：

- `--reload` 不能和 `--workers > 1` 同时使用

## 4. 正式部署建议

正式部署建议至少使用：

```bash
skilllint-web --host 0.0.0.0 --port 18110 --workers 2 --log-level info
```

更推荐的方式是放在反向代理后面，例如：

- Nginx
- Caddy
- 云负载均衡

建议：

1. 由反向代理处理 TLS
2. 对外只暴露代理入口
3. SkillLint 监听内网地址或受控端口
4. 配置请求体大小限制
5. 配置访问日志和错误日志

## 5. systemd 示例

仓库内已提供示例文件：

- `deploy/systemd/skilllint-web.service`

```ini
[Unit]
Description=SkillLint Web
After=network.target

[Service]
WorkingDirectory=/opt/skilllint
Environment=SKILLLINT_WEB_HOST=0.0.0.0
Environment=SKILLLINT_WEB_PORT=18110
Environment=SKILLLINT_WEB_WORKERS=2
Environment=SKILLLINT_WEB_LOG_LEVEL=info
ExecStart=/opt/skilllint/.venv/bin/skilllint-web
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## 6. Docker 启动示例

仓库内已提供：

- `Dockerfile`
- `compose.yaml`

```bash
docker build -t skilllint:latest .
docker run --rm -p 18110:18110 \
  -e SKILLLINT_WEB_HOST=0.0.0.0 \
  -e SKILLLINT_WEB_PORT=18110 \
  -e SKILLLINT_WEB_WORKERS=2 \
  skilllint:latest
```

也可以直接：

```bash
docker compose up -d --build
```

默认 compose 会：

- 暴露 `18110:18110`
- 使用 `skilllint-work` volume 保存工作目录
- 以 `unless-stopped` 重启策略运行

## 7. 安全建议

由于 SkillLint Web 支持：

- 上传压缩包
- 上传目录
- 远程 URL 扫描

正式部署时建议额外配置：

1. 反向代理侧的请求大小限制
2. 出站网络策略
3. API 访问控制
4. 进程级资源限制
5. 临时目录和磁盘空间监控
