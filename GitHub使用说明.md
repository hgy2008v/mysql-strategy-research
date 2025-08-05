# GitHub 使用说明文档

## 目录
- [GitHub 简介](#github-简介)
- [账户设置](#账户设置)
- [仓库管理](#仓库管理)
- [基本操作](#基本操作)
- [分支管理](#分支管理)
- [协作开发](#协作开发)
- [项目管理](#项目管理)
- [高级功能](#高级功能)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## GitHub 简介

### 什么是 GitHub？
GitHub 是全球最大的代码托管平台，基于 Git 版本控制系统，为开发者提供：
- 📁 **代码托管** - 安全存储和管理代码
- 🔄 **版本控制** - 跟踪代码变更历史
- 👥 **协作开发** - 团队协作和代码审查
- 🌐 **开源社区** - 分享和发现优秀项目

### 核心概念
- **Repository (仓库)** - 项目的代码存储空间
- **Commit (提交)** - 代码变更的记录
- **Branch (分支)** - 代码的独立开发线
- **Pull Request (拉取请求)** - 代码合并请求
- **Issue (问题)** - 任务和问题跟踪

## 账户设置

### 1. 注册账户
1. 访问 [GitHub.com](https://github.com)
2. 点击 "Sign up"
3. 填写用户名、邮箱和密码
4. 验证邮箱地址

### 2. 配置 Git
```bash
# 设置用户名和邮箱
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的邮箱@example.com"

# 查看配置
git config --list
```

### 3. 身份验证
#### 方法一：Personal Access Token (推荐)
1. GitHub → Settings → Developer settings → Personal access tokens
2. 点击 "Generate new token"
3. 选择权限范围（至少需要 repo 权限）
4. 复制生成的 token

```bash
# 使用 token 进行身份验证
git remote set-url origin https://你的用户名:你的token@github.com/用户名/仓库名.git
```

#### 方法二：SSH 密钥
```bash
# 生成 SSH 密钥
ssh-keygen -t rsa -b 4096 -C "你的邮箱@example.com"

# 查看公钥
cat ~/.ssh/id_rsa.pub

# 添加到 GitHub
# 复制公钥内容到 GitHub → Settings → SSH and GPG keys
```

## 仓库管理

### 1. 创建仓库

#### 网页端创建：
1. 点击右上角 "+" → "New repository"
2. 填写仓库信息：
   - **Repository name**: 仓库名称（建议使用小写字母和连字符）
   - **Description**: 项目描述
   - **Visibility**: Public（公开）或 Private（私有）
   - **Initialize this repository with**: 选择初始化选项

#### 本地创建：
```bash
# 创建本地仓库
mkdir my-project
cd my-project
git init

# 添加远程仓库
git remote add origin https://github.com/用户名/仓库名.git

# 首次推送
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 2. 克隆仓库
```bash
# 克隆公开仓库
git clone https://github.com/用户名/仓库名.git

# 克隆私有仓库（需要身份验证）
git clone https://github.com/用户名/仓库名.git

# 克隆到指定目录
git clone https://github.com/用户名/仓库名.git my-folder
```

### 3. 仓库设置
- **Settings** → **General**: 基本设置
- **Settings** → **Branches**: 分支保护规则
- **Settings** → **Collaborators**: 协作者管理
- **Settings** → **Pages**: GitHub Pages 设置

## 基本操作

### 1. 日常开发流程
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 查看状态
git status

# 3. 添加文件
git add .                    # 添加所有文件
git add filename.py          # 添加特定文件
git add *.py                 # 添加所有 .py 文件

# 4. 提交更改
git commit -m "描述你的更改"

# 5. 推送到远程
git push origin main
```

### 2. 查看历史
```bash
# 查看提交历史
git log                      # 详细历史
git log --oneline            # 简洁历史
git log --graph              # 图形化显示

# 查看特定提交
git show <commit-hash>       # 查看提交详情
git diff                     # 查看工作区差异
git diff --staged            # 查看暂存区差异
```

### 3. 撤销操作
```bash
# 撤销工作区更改
git checkout -- filename     # 撤销特定文件
git checkout -- .            # 撤销所有文件

# 撤销暂存区
git reset HEAD filename      # 取消暂存特定文件
git reset HEAD               # 取消暂存所有文件

# 撤销提交
git reset --soft HEAD~1      # 撤销提交但保留更改
git reset --hard HEAD~1      # 撤销提交并删除更改
```

## 分支管理

### 1. 分支操作
```bash
# 查看分支
git branch                   # 本地分支
git branch -a                # 所有分支
git branch -r                # 远程分支

# 创建分支
git branch feature-name      # 创建分支
git checkout -b feature-name # 创建并切换到分支

# 切换分支
git checkout feature-name    # 切换到分支
git switch feature-name      # 新版本切换命令

# 删除分支
git branch -d feature-name   # 删除本地分支
git push origin --delete feature-name  # 删除远程分支
```

### 2. 分支策略
#### Git Flow 工作流：
- **main**: 主分支，用于生产环境
- **develop**: 开发分支，用于集成测试
- **feature/***: 功能分支，用于新功能开发
- **release/***: 发布分支，用于版本发布
- **hotfix/***: 热修复分支，用于紧急修复

#### GitHub Flow 工作流：
- **main**: 主分支，始终保持可部署状态
- **feature/***: 功能分支，从 main 创建，完成后合并回 main

### 3. 合并操作
```bash
# 合并分支
git merge feature-name       # 将 feature-name 合并到当前分支

# 变基操作
git rebase main              # 将当前分支变基到 main

# 解决冲突
# 1. 编辑冲突文件
# 2. 添加解决后的文件
git add .
git commit -m "Resolve merge conflicts"
```

## 协作开发

### 1. Fork 和 Pull Request
#### Fork 仓库：
1. 在 GitHub 上点击 "Fork" 按钮
2. 选择目标账户
3. 等待 Fork 完成

#### 创建 Pull Request：
```bash
# 1. 克隆 Fork 的仓库
git clone https://github.com/你的用户名/仓库名.git

# 2. 添加上游仓库
git remote add upstream https://github.com/原作者/仓库名.git

# 3. 创建功能分支
git checkout -b feature-name

# 4. 开发功能
# ... 编写代码 ...

# 5. 提交更改
git add .
git commit -m "Add new feature"
git push origin feature-name

# 6. 在 GitHub 上创建 Pull Request
```

### 2. 代码审查
#### 审查 Pull Request：
1. 查看代码变更
2. 添加评论和建议
3. 请求更改或批准
4. 合并到主分支

#### 审查最佳实践：
- 检查代码质量和风格
- 验证功能实现
- 确保测试覆盖
- 提供建设性反馈

### 3. 协作者管理
- **Settings** → **Collaborators** → **Add people**
- 设置协作者权限：
  - **Read**: 只读权限
  - **Write**: 读写权限
  - **Admin**: 管理权限

## 项目管理

### 1. Issue 管理
#### 创建 Issue：
1. 点击 "Issues" 标签
2. 点击 "New issue"
3. 选择 Issue 模板
4. 填写标题和描述
5. 添加标签和分配人员

#### Issue 类型：
- **Bug**: 错误报告
- **Feature**: 功能请求
- **Documentation**: 文档改进
- **Enhancement**: 功能增强

#### Issue 模板示例：
```markdown
## 问题描述
简要描述问题或需求

## 重现步骤
1. 步骤1
2. 步骤2
3. 步骤3

## 预期行为
描述期望的结果

## 实际行为
描述实际发生的情况

## 环境信息
- 操作系统：
- 版本：
- 浏览器：

## 附加信息
其他相关信息或截图
```

### 2. 项目管理
#### Projects 看板：
- 创建项目看板
- 添加 Issue 和 Pull Request
- 设置列和自动化规则

#### Milestones 里程碑：
- 创建里程碑
- 设置截止日期
- 关联 Issue 和 Pull Request

### 3. Wiki 文档
- 创建项目 Wiki
- 编写使用文档
- 维护项目说明

## 高级功能

### 1. GitHub Actions (CI/CD)
#### 创建工作流：
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest
```

#### 常用 Actions：
- **actions/checkout**: 检出代码
- **actions/setup-python**: 设置 Python 环境
- **actions/setup-node**: 设置 Node.js 环境
- **actions/cache**: 缓存依赖

### 2. GitHub Pages
#### 启用 GitHub Pages：
1. 仓库设置 → Pages
2. 选择源分支（通常是 main）
3. 选择根目录或 /docs 目录
4. 保存设置

#### 自定义域名：
1. 在 Pages 设置中添加自定义域名
2. 在域名提供商处设置 DNS 记录
3. 在仓库根目录创建 CNAME 文件

### 3. GitHub Packages
#### 发布 npm 包：
```bash
# 配置 .npmrc
echo "//npm.pkg.github.com/:_authToken=${{ secrets.GITHUB_TOKEN }}" > .npmrc
echo "@用户名:registry=https://npm.pkg.github.com" >> .npmrc

# 发布包
npm publish
```

#### 发布 Docker 镜像：
```yaml
# GitHub Actions 工作流
- name: Build and push Docker image
  uses: docker/build-push-action@v2
  with:
    push: true
    tags: ghcr.io/用户名/镜像名:latest
```

## 最佳实践

### 1. 提交信息规范
#### 约定式提交：
```bash
# 格式：type(scope): description
git commit -m "feat(auth): add user login functionality"
git commit -m "fix(api): resolve authentication bug"
git commit -m "docs(readme): update installation guide"
```

#### 提交类型：
- **feat**: 新功能
- **fix**: 修复 bug
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建过程或辅助工具变动

### 2. 分支命名规范
```bash
# 功能分支
feature/user-authentication
feature/payment-integration

# 修复分支
fix/login-validation
fix/security-vulnerability

# 发布分支
release/v1.2.0
hotfix/critical-bug-fix
```

### 3. README 文件规范
```markdown
# 项目名称

## 项目简介
简要描述项目功能和目标

## 功能特性
- 特性1
- 特性2
- 特性3

## 安装说明
```bash
# 克隆仓库
git clone https://github.com/用户名/仓库名.git

# 安装依赖
npm install
# 或
pip install -r requirements.txt
```

## 使用方法
```bash
# 启动项目
npm start
# 或
python main.py
```

## 配置说明
描述配置选项和环境变量

## API 文档
描述 API 接口和使用方法

## 贡献指南
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证
MIT License

## 联系方式
- 邮箱：your-email@example.com
- 项目地址：https://github.com/用户名/仓库名
```

### 4. .gitignore 文件
```gitignore
# 依赖文件
node_modules/
venv/
__pycache__/

# 构建文件
dist/
build/
*.pyc

# 环境文件
.env
.env.local

# 日志文件
*.log
logs/

# 临时文件
*.tmp
*.temp

# IDE 文件
.vscode/
.idea/
*.swp

# 操作系统文件
.DS_Store
Thumbs.db
```

## 常见问题

### 1. 身份验证问题
**问题**: 推送时提示身份验证失败
**解决**:
```bash
# 检查远程仓库 URL
git remote -v

# 重新设置身份验证
git remote set-url origin https://用户名:token@github.com/用户名/仓库名.git
```

### 2. 合并冲突
**问题**: 合并时出现冲突
**解决**:
1. 查看冲突文件
2. 手动编辑解决冲突
3. 添加解决后的文件
4. 提交更改

### 3. 撤销错误提交
**问题**: 提交了错误的代码
**解决**:
```bash
# 撤销最后一次提交
git reset --soft HEAD~1

# 撤销多次提交
git reset --soft HEAD~3

# 强制推送（谨慎使用）
git push --force-with-lease origin main
```

### 4. 大文件处理
**问题**: 提交了大文件导致推送失败
**解决**:
```bash
# 使用 Git LFS
git lfs track "*.psd"
git add .gitattributes
git add *.psd
git commit -m "Add large files with LFS"
```

### 5. 网络连接问题
**问题**: 网络连接不稳定
**解决**:
```bash
# 配置代理
git config --global http.proxy http://proxy-server:port
git config --global https.proxy https://proxy-server:port

# 增加缓冲区大小
git config --global http.postBuffer 524288000
```

## 总结

GitHub 是现代软件开发的核心平台，掌握这些基本使用方法将大大提高你的开发效率和团队协作能力。记住：

1. **经常提交** - 小步快跑，频繁提交
2. **写好的提交信息** - 清晰描述每次更改
3. **使用分支** - 避免直接在主分支上开发
4. **代码审查** - 重视代码质量和团队协作
5. **持续学习** - GitHub 功能不断更新，保持学习

祝你使用 GitHub 愉快！🚀

---

*最后更新：2024年*
*版本：1.0* 