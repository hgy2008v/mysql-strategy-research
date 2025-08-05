# GitHub 代码仓库使用指南

## 目录
- [代码仓库基础](#代码仓库基础)
- [仓库创建和管理](#仓库创建和管理)
- [代码提交和推送](#代码提交和推送)
- [分支管理](#分支管理)
- [版本控制](#版本控制)
- [仓库设置](#仓库设置)
- [代码同步](#代码同步)
- [实用技巧](#实用技巧)

## 代码仓库基础

### 什么是代码仓库？
代码仓库（Repository）是 GitHub 的核心功能，用于存储和管理你的项目代码。每个仓库都包含：
- 📁 **项目文件** - 源代码、文档、配置文件
- 📝 **提交历史** - 所有代码变更的记录
- 🌿 **分支管理** - 不同版本的代码分支
- 📊 **统计信息** - 代码贡献、提交频率等

### 仓库类型
- **Public（公开）** - 任何人都可以查看和克隆
- **Private（私有）** - 只有你和协作者可以访问

## 仓库创建和管理

### 1. 创建新仓库

#### 网页端创建（推荐新手）：
1. 登录 GitHub
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   ```
   Repository name: my-project
   Description: 我的项目描述
   Visibility: Public/Private
   ✓ Add a README file
   ✓ Add .gitignore (选择 Python/Node.js 等)
   ✓ Choose a license
   ```
4. 点击 "Create repository"

#### 本地创建后推送：
```bash
# 1. 创建本地项目文件夹
mkdir my-project
cd my-project

# 2. 初始化 Git 仓库
git init

# 3. 添加文件
echo "# My Project" > README.md
git add README.md
git commit -m "Initial commit"

# 4. 添加远程仓库
git remote add origin https://github.com/用户名/my-project.git

# 5. 推送到 GitHub
git push -u origin main
```

### 2. 克隆现有仓库
```bash
# 克隆公开仓库
git clone https://github.com/用户名/仓库名.git

# 克隆到指定目录
git clone https://github.com/用户名/仓库名.git my-folder

# 克隆特定分支
git clone -b develop https://github.com/用户名/仓库名.git

# 浅克隆（只获取最新提交）
git clone --depth 1 https://github.com/用户名/仓库名.git
```

### 3. 仓库结构建议
```
my-project/
├── README.md              # 项目说明
├── .gitignore             # Git 忽略文件
├── requirements.txt       # Python 依赖
├── package.json           # Node.js 依赖
├── src/                   # 源代码目录
│   ├── main.py
│   └── utils.py
├── tests/                 # 测试文件
│   └── test_main.py
├── docs/                  # 文档目录
│   └── API.md
├── config/                # 配置文件
│   └── settings.py
└── scripts/               # 脚本文件
    └── deploy.sh
```

## 代码提交和推送

### 1. 日常开发流程
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 查看当前状态
git status

# 3. 添加修改的文件
git add .                    # 添加所有文件
git add src/main.py          # 添加特定文件
git add *.py                 # 添加所有 .py 文件

# 4. 提交更改
git commit -m "feat: 添加用户登录功能"

# 5. 推送到远程仓库
git push origin main
```

### 2. 提交信息规范
```bash
# 推荐格式：type(scope): description
git commit -m "feat(auth): add user login functionality"
git commit -m "fix(api): resolve authentication bug"
git commit -m "docs(readme): update installation guide"
git commit -m "style(code): format code according to PEP8"
git commit -m "refactor(utils): simplify data processing logic"
git commit -m "test(auth): add unit tests for login function"
git commit -m "chore(deps): update dependencies to latest versions"
```

### 3. 批量操作
```bash
# 查看所有修改
git diff

# 查看已暂存的修改
git diff --staged

# 添加所有修改（包括删除的文件）
git add -A

# 提交所有修改（跳过暂存）
git commit -am "feat: add new features"

# 查看提交历史
git log --oneline -10
```

## 分支管理

### 1. 分支操作
```bash
# 查看所有分支
git branch                   # 本地分支
git branch -a                # 所有分支（包括远程）
git branch -r                # 远程分支

# 创建新分支
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
#### 简单分支策略（推荐小型项目）：
```
main (主分支)
├── feature/user-login
├── feature/payment
└── hotfix/critical-bug
```

#### 完整分支策略（推荐大型项目）：
```
main (生产环境)
├── develop (开发环境)
│   ├── feature/user-login
│   ├── feature/payment
│   └── feature/notification
├── release/v1.2.0
└── hotfix/critical-bug
```

### 3. 合并操作
```bash
# 合并分支到当前分支
git merge feature-name

# 变基操作（保持提交历史整洁）
git rebase main

# 解决合并冲突
# 1. 编辑冲突文件
# 2. 添加解决后的文件
git add .
git commit -m "Resolve merge conflicts"
```

## 版本控制

### 1. 标签管理
```bash
# 创建标签
git tag v1.0.0              # 轻量标签
git tag -a v1.0.0 -m "Release version 1.0.0"  # 附注标签

# 推送标签
git push origin v1.0.0      # 推送特定标签
git push origin --tags       # 推送所有标签

# 查看标签
git tag                     # 查看所有标签
git show v1.0.0             # 查看标签详情

# 删除标签
git tag -d v1.0.0           # 删除本地标签
git push origin --delete v1.0.0  # 删除远程标签
```

### 2. 版本回退
```bash
# 查看提交历史
git log --oneline

# 回退到指定提交
git reset --hard HEAD~1     # 回退一个提交
git reset --hard abc1234    # 回退到指定提交

# 创建新分支保存当前状态
git checkout -b backup-branch

# 强制推送（谨慎使用）
git push --force-with-lease origin main
```

### 3. 撤销操作
```bash
# 撤销工作区修改
git checkout -- filename    # 撤销特定文件
git checkout -- .           # 撤销所有文件

# 撤销暂存区
git reset HEAD filename     # 取消暂存特定文件
git reset HEAD              # 取消暂存所有文件

# 撤销提交
git reset --soft HEAD~1     # 撤销提交但保留修改
git reset --mixed HEAD~1    # 撤销提交和暂存
git reset --hard HEAD~1     # 撤销提交并删除修改
```

## 仓库设置

### 1. 基本设置
- **Settings** → **General**:
  - Repository name: 仓库名称
  - Description: 仓库描述
  - Website: 项目网站
  - Topics: 标签（便于搜索）

### 2. 分支保护
- **Settings** → **Branches**:
  - 添加分支保护规则
  - 要求代码审查
  - 要求状态检查通过
  - 限制直接推送

### 3. 协作者管理
- **Settings** → **Collaborators**:
  - 添加协作者
  - 设置权限级别：
    - Read: 只读权限
    - Write: 读写权限
    - Admin: 管理权限

### 4. 安全设置
- **Settings** → **Security**:
  - 启用安全扫描
  - 配置依赖更新
  - 设置安全策略

## 代码同步

### 1. 多设备同步
```bash
# 设备A：推送代码
git add .
git commit -m "feat: add new feature"
git push origin main

# 设备B：拉取代码
git pull origin main
```

### 2. 解决同步冲突
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 如果有冲突，手动编辑文件
# 3. 添加解决后的文件
git add .
git commit -m "Resolve sync conflicts"

# 4. 推送解决后的代码
git push origin main
```

### 3. 远程仓库管理
```bash
# 查看远程仓库
git remote -v

# 添加远程仓库
git remote add upstream https://github.com/原作者/仓库名.git

# 更新远程仓库
git remote set-url origin https://github.com/新用户名/仓库名.git

# 删除远程仓库
git remote remove upstream
```

## 实用技巧

### 1. 常用 Git 别名
```bash
# 设置别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative"

# 使用别名
git st    # git status
git co    # git checkout
git br    # git branch
git ci    # git commit
git lg    # 图形化日志
```

### 2. 忽略文件配置
```gitignore
# .gitignore 文件示例
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

# IDE 文件
.vscode/
.idea/
*.swp

# 操作系统文件
.DS_Store
Thumbs.db
```

### 3. 大文件处理
```bash
# 使用 Git LFS 处理大文件
git lfs track "*.psd"
git lfs track "*.zip"
git lfs track "*.pdf"

# 添加 .gitattributes 文件
git add .gitattributes
git commit -m "Add LFS tracking for large files"
```

### 4. 性能优化
```bash
# 浅克隆（只获取最新提交）
git clone --depth 1 https://github.com/用户名/仓库名.git

# 部分克隆（只获取特定目录）
git clone --filter=blob:none --sparse https://github.com/用户名/仓库名.git
cd 仓库名
git sparse-checkout init --cone
git sparse-checkout set src/

# 清理仓库
git gc                    # 垃圾回收
git prune                 # 删除悬空对象
```

### 5. 备份和恢复
```bash
# 创建本地备份
git clone --mirror https://github.com/用户名/仓库名.git 仓库名-backup

# 从备份恢复
cd 仓库名-backup
git push --mirror https://github.com/用户名/仓库名.git
```

## 最佳实践

### 1. 提交频率
- **小步快跑** - 频繁提交，每次提交只做一件事
- **原子提交** - 每个提交都是完整的功能或修复
- **及时提交** - 完成一个小功能就立即提交

### 2. 分支管理
- **主分支保护** - 不要直接在主分支上开发
- **功能分支** - 每个功能创建独立分支
- **及时合并** - 功能完成后及时合并到主分支

### 3. 代码质量
- **代码审查** - 重要更改需要代码审查
- **测试覆盖** - 确保代码有足够的测试
- **文档更新** - 代码更改时同步更新文档

### 4. 安全考虑
- **敏感信息** - 不要提交密码、密钥等敏感信息
- **环境变量** - 使用 .env 文件管理配置
- **访问控制** - 合理设置仓库访问权限

## 常见问题解决

### 1. 推送失败
```bash
# 问题：推送被拒绝
# 解决：先拉取最新代码
git pull origin main
git push origin main
```

### 2. 合并冲突
```bash
# 问题：合并时出现冲突
# 解决：
git status                    # 查看冲突文件
# 手动编辑冲突文件
git add .                     # 添加解决后的文件
git commit -m "Resolve conflicts"
```

### 3. 误删文件恢复
```bash
# 恢复误删的文件
git checkout HEAD -- filename

# 恢复整个目录
git checkout HEAD -- directory/
```

### 4. 提交历史清理
```bash
# 清理提交历史
git rebase -i HEAD~5         # 交互式变基
git push --force-with-lease origin main  # 强制推送
```

---

## 总结

GitHub 代码仓库是现代软件开发的核心工具，掌握这些使用方法将大大提高你的开发效率：

1. **建立好的习惯** - 频繁提交、写好的提交信息
2. **合理使用分支** - 避免直接在主分支上开发
3. **保持代码同步** - 定期拉取和推送代码
4. **重视代码质量** - 代码审查、测试覆盖
5. **做好备份** - 重要代码及时备份

祝你使用 GitHub 代码仓库愉快！🚀

---

*最后更新：2024年*
*版本：1.0* 