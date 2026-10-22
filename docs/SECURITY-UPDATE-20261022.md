# 2026-10-22 安全更新

适用于当前 Tripwright 单机部署：`/home/ubuntu/tripwright`，Compose 项目名 `ai-guide`。本次只更新依赖、运行时及证书信任；没有数据库表结构变更。

## 更新内容

| 位置 | 修改 |
| --- | --- |
| 后端 Python 镜像 | 3.13.15 → 3.13.17，更新 Python 自带的 pip；显式更新 Debian 系统 CA，并要求至少 `20250419~deb12u2` |
| 后端依赖 | certifi 固定 2026.10.19；安装依赖前用官方带 SHA-256 的 wheel 安装 pip 26.2.2 |
| 前端构建和 CI | Node 22.23.2 → 22.23.4 |
| Caddy | 保留 2.11.4，使用 Go 1.26.10 重新编译，保留标准模块及原镜像的构建标签 |
| Web 系统 CA | 更新 Alpine CA 包，构建时检查实际证书库 |
| 验收 | 镜像构建及 Compose CI 检查应用、pip、系统 CA 和 Caddy 编译工具链；发现受影响根、空证书库或旧版本时失败 |

不使用 PHP 的部署无需安装或升级 PHP。本次不更换数据库、命名卷、域名、证书或模型配置。

## 1. 宿主机

Ubuntu 24.04 应将 `ca-certificates` 更新到 `20260816ubuntu0.24.04.1` 或更新版本。当前服务器已经执行并确认达到该版本。

更新宿主机不会更新已有容器。系统安装程序提示“无需重启容器”不能作为容器内部已修补的依据。

## 2. 本地提交

在笔记本 PowerShell、项目根目录执行：

```powershell
cd D:\F_Drive\AI-Guide
git diff --check
git add .github/workflows/ci.yml backend/Dockerfile backend/requirements.txt backend/requirements.lock.txt backend/requirements-bootstrap.txt backend/app/tls_audit.py web/Dockerfile web/check-tls-trust.sh docs/SECURITY-UPDATE-20261022.md
git --no-pager diff --cached --stat
git commit -m "Patch CA trust stores and security runtimes"
git push origin main
```

提交前核对暂存区只包含本次预期文件。等待本次 GitHub Actions 全部通过，尤其是 Compose 镜像构建及运行时信任检查。本机没有 Docker，不能用本地前端构建或 Shell 测试代替这一项。

## 3. 服务器拉取并备份

以下均在腾讯云 Ubuntu 终端执行，每一步成功后再继续。

```bash
cd /home/ubuntu/tripwright
git status --short
git pull --ff-only origin main
git log -1 --oneline
sudo env COMPOSE_PROJECT_NAME=ai-guide COMPOSE_OVERRIDE_FILE=deploy/compose.small.yml bash deploy/backup.sh
```

若工作区已有修改或备份失败，先处理再更新。备份会短暂停止 API/Worker，完成后恢复。

首次更新前保留正在运行的镜像。以下快照名只使用一次，已有同名快照时不要覆盖：

```bash
sudo docker image tag "$(sudo docker inspect --format '{{.Image}}' ai-guide-api-1)" local/ai-guide-api:pre-security-20261022
sudo docker image tag "$(sudo docker inspect --format '{{.Image}}' ai-guide-web-1)" local/ai-guide-web:pre-security-20261022
```

## 4. 顺序构建和启动

```bash
sudo docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml config --quiet
sudo docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml build --pull api
sudo docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml build --pull web
sudo docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml up -d --no-build
```

`--pull` 拉取对应固定版本的基础镜像，不会绕过版本固定。沿用服务器现有 `.env` 中的镜像 tag，构建后 `up` 使用新镜像重建应用容器。保留 `-p ai-guide`，确保继续挂载原来的数据卷。

首次构建 Web 会编译 Caddy，比之前只复制二进制更耗时。已限制 Go 的编译并行度和 GC 目标，但这不等于测得 2GB 机器上的峰值内存；仍需在服务器观察。两个镜像分开构建，构建失败时不要继续 `up`。

不运行 `down -v`。应用镜像变更不要求升级 MySQL 或 Redis，也不需要恢复数据库备份。

## 5. 验收

```bash
sudo docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml ps -a
sudo docker exec ai-guide-api-1 python -m app.tls_audit --system
sudo docker exec ai-guide-worker-1 python -m app.tls_audit --system
sudo docker exec ai-guide-web-1 sh /usr/local/bin/check-tls-trust.sh
curl -fsS https://guide.dirtydev.cc/api/health/ready
sudo docker stats --no-stream
free -h
```

应得到：

- API/Worker 检查均返回 `"ok": true`，certifi 2026.10.19、pip 26.2.2；三个证书库的 `blocked_roots` 都为空，且 `root_count` 大于零。
- Web 检查显示 Caddy 的 Go 为 1.26.10，系统 CA 中没有受影响根。Caddy 功能版本仍为 2.11.4 是预期结果。
- API healthy，迁移容器退出码 0，健康检查通过。
- 登录、已有旅行、真实模型响应、地图搜索和路线正常。真实外部调用用于验证接入，不能由离线 CA 检查代替。

检查脚本只读取版本和公开 CA 信息，不打印生产 `.env` 或请求密钥。若上游服务更新后出现证书错误，应修复其证书链或代理信任配置，不能关闭 TLS 验证。

宿主机内其他长期运行的 TLS 客户端可能缓存系统信任库。Docker daemon 若已缓存旧 CA，应在维护窗口重启或更新后重新启动，让它重新加载信任库；这会影响容器运行，需先完成备份并检查重启策略，不要把宿主机包安装程序的提示当作所有进程都已刷新信任库的证明。

## 6. 出错时

构建失败时，原容器仍使用原镜像运行，保留报错排查即可。

新容器出现应用回归时，可临时使用已保存的旧镜像恢复可用性：

```bash
sudo env IMAGE_REGISTRY=local APP_VERSION=pre-security-20261022 docker compose -p ai-guide -f docker-compose.yml -f deploy/compose.small.yml up -d --no-build
```

此命令仅临时覆盖镜像变量，不改 `.env`。后续不带该覆盖的 `up` 会再次选择 `.env` 中的镜像。旧镜像仍有本次安全问题，回退用于恢复可用性，不能作为修补完成。无需回退数据库或恢复旧 CA。

## 依据

- [Python 安全公告](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
- [Python 3.13.17 安全发布](https://www.python.org/downloads/release/python-31317/)
- [Debian CA 修复版本](https://security-tracker.debian.org/tracker/source-package/ca-certificates)
- [Ubuntu 24.04 CA 修复](https://ubuntu.com/security/notices/USN-8944-1)
- [Go 修复公告](https://groups.google.com/g/golang-announce/c/66pojueaQek)
- [Node 22.23.4 安全发布](https://nodejs.org/en/blog/release/v22.23.4)

## 本地验证记录

- 使用经过官方 SHA-256 校验的便携 Node 22.23.4，Vue 类型检查和 Vite 生产构建通过。
- 本地项目虚拟环境已更新至 pip 26.2.2、certifi 2026.10.19，依赖一致性检查通过。
- 以更新前真实 certifi CA 文件验证拒绝路径，新证书库验证成功，空证书库验证失败。
- Web Shell 检查验证 Go 1.26.10、1.27.3 通过，旧版本和未知版本失败，旧 CA 库失败；Caddy 版本输出在此单测中使用夹具，未运行 Linux Caddy 二进制。
- 9 项仓库脚本测试、Compose 静态检查、环境模板一致性检查和秘密扫描通过。
- Docker 构建、Linux 容器运行、Python 3.13.17 内的后端全套测试和服务器真实调用尚待本次 CI/部署验收；未执行 Git 提交、push 或生产部署。

本地全局 Node 仍为 24.14.0。本轮测试使用工作区内的修复版；后续开发应切换到受支持的修复版本，避免继续用旧运行时安装依赖或构建。
