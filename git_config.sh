#!/bin/bash

# Git配置脚本

echo "开始配置Git..."

# 配置用户信息
read -p "请输入你的用户名: " username
read -p "请输入你的邮箱: " email

git config --global user.name "$username"
git config --global user.email "$email"

# 配置默认编辑器
git config --global core.editor "vim"

# 配置默认分支名
git config --global init.defaultBranch "main"

# 配置常用别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative"

# 配置提交时自动修正CRLF为LF
git config --global core.autocrlf input

# 配置使用https时记住密码
git config --global credential.helper store

# 配置pull策略
git config --global pull.rebase false

echo "Git配置完成！当前配置信息："
git config --list

echo "是否生成SSH密钥? (y/n)"
read generate_ssh

if [ "$generate_ssh" = "y" ]; then
    ssh-keygen -t rsa -b 4096 -C "$email"
    echo "SSH密钥已生成，公钥内容如下:"
    cat ~/.ssh/id_rsa.pub
    echo "请将以上公钥添加到你的Git托管服务中。"
fi

echo "Git配置脚本执行完毕!"

git st

ssh -T git@github.com

mkdir test-repo
cd test-repo
git init
touch README.md
git add README.md
git commit -m "初始提交"