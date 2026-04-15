# SkillLint Input Validation

## 1. 目标

SkillLint 在真正进入 regex / package / semantic / dataflow 引擎之前，会先对输入做统一校验。

目的包括：

1. 过滤明显不是 skill 的输入；
2. 防止 zip slip、异常路径、symlink archive entry 等危险归档；
3. 防止超大目录、超大文件、超深路径拖慢或拖垮扫描；
4. 在 Web/API 场景中降低 SSRF 与恶意远程下载风险。

## 2. 校验发生的位置

主要在：

- `src/skilllint/core/input_validation.py`
- `src/skilllint/core/workspace.py`
- `src/app/static/app.js`

设计原则是：

- **统一在 workspace 归一化阶段校验**
- 不管输入来自目录、zip、URL 还是 git，尽量复用同一套限制
- Web 前端先做轻量预检查，后端仍保留权威校验

## 2.1 Web 前端预检查

Web UI 会在真正调用 `/api/scan/*` 前做一轮浏览器侧预检查。

这不是安全边界，主要目的是：

- 尽早提示用户；
- 避免明显无效的大目录上传；
- 减少无意义的网络往返。

当前前端预检查包括：

- archive：
  - 文件名必须是 `.zip`
  - 上传 zip 体积不能超过 `100MB`
- directory：
  - 文件数不能超过 `1000`
  - 至少存在一个 `SKILL.md`
  - 单文件不能超过 `20MB`
  - 总体积不能超过 `200MB`
  - 路径长度和层级不能超过默认限制
- URL：
  - scheme 必须是 `http` / `https`
  - 不能带内嵌用户名/密码
  - 不能是 localhost、private、link-local、metadata 等明显不安全 host

注意：前端检查可被绕过，因此后端仍会执行完整校验。

## 3. 目录输入校验

目录输入支持自动识别“外层多包一层目录”的常见情况：

- 若用户传入的是父目录；
- 且里面只包含一个真正的 skill 子目录；
- 则 SkillLint 会自动下钻到那个 skill 根。

默认校验包括：

- 归一化后不能为空
- 默认必须存在 `SKILL.md`
- 文件总数不能超过 `max_input_files`
- 单文件大小不能超过 `max_single_file_mb`
- 总体积不能超过 `max_total_input_mb`
- 路径深度不能超过 `max_path_depth`
- 路径长度不能超过 `max_path_length`

## 4. 压缩包输入校验

zip 输入在真正解压前就会检查成员表：

- 文件数量
- 单文件大小
- 总解压体积
- 路径深度 / 长度
- 空路径 entry
- `..` 路径穿越
- 绝对路径
- Windows drive-qualified path
- symlink entry

这样可以避免：

- zip slip
- 异常层级压缩包
- 恶意超大展开

## 5. URL 输入校验

远程 URL 扫描属于高风险入口，因为服务端会主动发起下载。

因此当前会额外校验：

- scheme 必须是 `http` / `https`
- URL 不能带内嵌凭证
- 不能没有 hostname
- 禁止以下类型的 host：
  - `localhost`
  - `.local`
  - loopback IP
  - private IP
  - link-local IP
  - metadata service host

同时下载过程还会限制：

- 最大下载大小
- 最大重定向次数

若发生重定向，新的目标 URL 也会再次通过同样的远程 URL 校验。

## 6. 结构化错误码

当请求进入 SkillLint 自身的输入校验逻辑后，Web/API 会返回结构化错误：

```json
{
  "detail": {
    "code": "unsafe_remote_host",
    "message": "Remote URL host is not allowed: 127.0.0.1.",
    "metadata": {
      "host": "127.0.0.1"
    }
  }
}
```

常见错误码包括：

| Code | 含义 |
|---|---|
| `empty_input` | 归一化后没有有效内容 |
| `missing_skill_entry` | 没有找到 `SKILL.md` |
| `missing_root_skill_entry` | 看起来传入了父目录而不是 skill 根目录 |
| `too_many_files` | 文件数量超限 |
| `file_too_large` | 单文件超限 |
| `input_too_large` | 总体积超限 |
| `archive_too_large` | 本地压缩包体积超限 |
| `unsafe_archive_path` | zip 中存在路径穿越或异常路径 |
| `archive_symlink_entry` | zip 中存在 symlink entry |
| `invalid_archive` | 无效 zip 文件 |
| `path_too_deep` | 路径层级超限 |
| `path_too_long` | 路径长度超限 |
| `unsupported_remote_scheme` | 远程 URL scheme 非 http/https |
| `remote_credentials_not_allowed` | URL 带有内嵌凭证 |
| `unsafe_remote_host` | 远程 host 不安全 |
| `remote_too_large` | 远程内容超出下载大小限制 |
| `too_many_redirects` | 重定向次数超限 |

## 7. 配置项

默认配置位于：

- `config/skilllint.default.yaml`

当前相关输入配置：

```yaml
inputs:
  allow_remote: true
  download_timeout_seconds: 60
  max_archive_size_mb: 100
  max_redirects: 5
  max_input_files: 1000
  max_single_file_mb: 20
  max_total_input_mb: 200
  max_path_depth: 20
  max_path_length: 240
  require_skill_entry: true
```

## 8. 特殊说明

为了兼容 golden/baseline 评估中的少量“故意无效输入”样本：

- 正常 `scan` 默认要求 `require_skill_entry = true`
- baseline / evaluate-golden 会把它临时调成 `false`

这样既能保证生产扫描严格，又不会破坏已有评估样本集。
