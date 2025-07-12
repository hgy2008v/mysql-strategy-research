# GitHub自动推送配置说明

## 概述

本项目已配置了自动推送功能，可以将代码更改自动推送到GitHub仓库。系统包含以下组件：

1. **Git仓库初始化** - 已完成的本地Git仓库
2. **自动推送脚本** - `auto_push.py`
3. **定时任务设置** - `setup_auto_push_scheduler.py`
4. **配置文件** - `.gitignore`

## 配置步骤

### 1. 配置Git用户信息

首先需要设置您的Git用户信息：

```bash
git config user.name "您的GitHub用户名"
git config user.email "您的邮箱@example.com"
```

### 2. 创建GitHub仓库

在GitHub上创建一个新的仓库，然后获取仓库URL。

### 3. 配置远程仓库

使用以下命令配置远程仓库：

```bash
git remote add origin <您的GitHub仓库URL>
```

或者使用自动配置脚本：

```bash
python auto_push.py setup <您的GitHub仓库URL>
```

### 4. 设置自动推送定时任务

运行定时任务设置脚本：

```bash
python setup_auto_push_scheduler.py
```

选择选项1创建定时任务。任务将在每天晚上8:00自动运行。

## 使用方法

### 手动推送

直接运行自动推送脚本：

```bash
python auto_push.py
```

### 定时自动推送

系统已配置定时任务，每天晚上8:00自动检查并推送更改。

### 管理定时任务

使用以下命令管理定时任务：

```bash
# 查看任务状态
schtasks /query /tn AutoPushToGitHub

# 立即运行任务
schtasks /run /tn AutoPushToGitHub

# 删除任务
schtasks /delete /tn AutoPushToGitHub /f
```

## 文件说明

### auto_push.py
- **功能**: 自动检查Git状态，提交更改并推送到GitHub
- **用法**: `python auto_push.py` 或 `python auto_push.py setup <仓库URL>`
- **日志**: 输出到 `auto_push.log`

### setup_auto_push_scheduler.py
- **功能**: 创建和管理自动推送的Windows定时任务
- **用法**: `python setup_auto_push_scheduler.py`
- **日志**: 输出到 `auto_push_scheduler.log`

### .gitignore
- **功能**: 排除不需要版本控制的文件
- **包含**: Python缓存、日志文件、数据文件、大文件等

## 注意事项

1. **首次推送**: 首次推送到GitHub时，可能需要配置SSH密钥或使用个人访问令牌
2. **网络连接**: 确保网络连接正常，能够访问GitHub
3. **权限设置**: 确保GitHub仓库有推送权限
4. **日志监控**: 定期检查日志文件，确保推送正常进行

## 故障排除

### 常见问题

1. **推送失败**
   - 检查网络连接
   - 验证GitHub仓库URL
   - 确认推送权限

2. **定时任务不运行**
   - 检查任务是否创建成功
   - 查看Windows事件日志
   - 手动运行测试

3. **认证失败**
   - 配置SSH密钥
   - 或使用个人访问令牌

### 日志文件

- `auto_push.log` - 自动推送脚本日志
- `auto_push_scheduler.log` - 定时任务设置日志

## 安全建议

1. 不要在代码中硬编码敏感信息（如API密钥）
2. 使用环境变量存储敏感配置
3. 定期更新Git和Python依赖
4. 监控推送日志，确保没有意外推送

## 联系支持

如果遇到问题，请检查：
1. 日志文件中的错误信息
2. Git状态和配置
3. 网络连接和GitHub访问权限 