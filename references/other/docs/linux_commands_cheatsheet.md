# 🐧 Linux 常用指令速查表

## 📁 文件和目录操作

### 基本操作
```bash
# 列出文件
ls              # 简单列出
ls -l           # 详细列表
ls -la          # 显示所有文件(包括隐藏文件)
ls -lh          # 人性化显示文件大小

# 切换目录
cd /path        # 切换到指定路径
cd ~            # 回到家目录
cd ..           # 返回上一级
cd -            # 返回上一个目录

# 查看当前目录
pwd             # 显示当前工作目录
```

### 文件操作
```bash
# 创建文件
touch file.txt  # 创建空文件

# 创建目录
mkdir dirname   # 创建目录
mkdir -p path/to/dir  # 创建多级目录

# 复制文件
cp file1 file2  # 复制文件
cp -r dir1 dir2 # 递归复制目录

# 移动/重命名
mv old new      # 移动或重命名
mv file dir/    # 移动到目录

# 删除文件
rm file         # 删除文件
rm -r dir       # 递归删除目录
rm -f file      # 强制删除
rm -rf dir      # 强制递归删除(危险!)

# 查看文件内容
cat file        # 显示整个文件
less file       # 分页查看(可上下滚动)
more file       # 分页查看
head -n 10 file # 查看前10行
tail -n 10 file # 查看后10行
tail -f file    # 实时查看日志
```

## 🔍 文件查找和搜索

```bash
# 查找文件
find /path -name "*.txt"      # 按名称查找
find . -type f -name "*.py"   # 查找Python文件
find . -size +10M            # 查找大于10M的文件
find . -mtime -7             # 查找7天内修改的文件

# 文本搜索
grep "text" file            # 在文件中搜索文本
grep -r "text" dir/         # 递归搜索目录
grep -i "text" file         # 忽略大小写
grep -n "text" file         # 显示行号
grep -v "text" file         # 反向搜索(不包含)

# 快速定位文件
locate filename             # 快速查找文件(需要updatedb)
which command              # 查找命令位置
whereis command            # 查找命令及相关文件
```

## 📊 系统信息和进程管理

### 系统信息
```bash
# 系统信息
uname -a                   # 显示所有系统信息
hostname                   # 显示主机名
whoami                     # 显示当前用户

# 磁盘空间
df -h                      # 显示磁盘使用情况(人性化)
du -sh dir/                # 显示目录大小
du -h --max-depth=1        # 显示一级子目录大小

# 内存信息
free -h                    # 显示内存使用情况
top                        # 动态显示进程信息
htop                       # 增强版top(需要安装)
```

### 进程管理
```bash
# 查看进程
ps aux                     # 查看所有进程
ps -ef                     # 查看完整进程列表
ps aux | grep process      # 查找特定进程

# 进程控制
kill PID                   # 终止进程
kill -9 PID                # 强制终止进程
killall processname        # 终止所有同名进程
pkill processname          # 按名称终止进程

# 后台运行
command &                # 后台运行
nohup command &          # 后台运行且退出终端不终止
bg                         # 将暂停的作业放到后台
fg                         # 将后台作业放到前台
jobs                       # 查看后台作业
```

## 🔧 权限和用户管理

### 文件权限
```bash
# 查看权限
ls -l                      # 查看文件权限

# 修改权限
chmod 755 file            # 数字方式修改权限
chmod u+x file            # 给所有者添加执行权限
chmod g-w file            # 移除组写权限
chmod o+r file            # 添加其他用户读权限

# 修改所有者
chown user:group file     # 修改所有者和组
chown user file           # 修改所有者
chgrp group file          # 修改组
```

### 用户管理
```bash
# 用户信息
id                        # 显示当前用户信息
who                       # 显示登录用户
w                         # 显示登录用户及活动

# 切换用户
su username               # 切换用户
sudo command              # 以root权限执行命令
sudo -i                   # 切换到root用户
```

## 🌐 网络相关

```bash
# 网络配置
ifconfig                  # 查看网络接口(旧)
ip addr                  # 查看IP地址
ip link                  # 查看网络链接

# 网络测试
ping example.com         # 测试网络连通性
ping -c 4 example.com    # 发送4个包后停止

# 端口检查
netstat -tlnp            # 查看监听端口
ss -tlnp                 # 新版网络工具
lsof -i :80              # 查看80端口进程

# 下载文件
wget url                 # 下载文件
curl url                 # 获取URL内容
curl -O url              # 下载文件
```

## 📦 包管理

### Ubuntu/Debian (apt)
```bash
# 更新软件包列表
sudo apt update

# 安装软件
sudo apt install package

# 卸载软件
sudo apt remove package
sudo apt purge package   # 彻底删除包括配置

# 升级系统
sudo apt upgrade         # 升级已安装包
sudo apt dist-upgrade    # 智能升级

# 搜索软件
apt search keyword

# 显示软件信息
apt show package
```

### CentOS/RHEL (yum/dnf)
```bash
# 更新软件包列表
sudo yum check-update
sudo dnf check-update

# 安装软件
sudo yum install package
sudo dnf install package

# 卸载软件
sudo yum remove package
sudo dnf remove package

# 搜索软件
yum search keyword
dnf search keyword
```

## 🔄 压缩和解压缩

```bash
# tar压缩
tar -czf archive.tar.gz dir/   # 创建gzip压缩包
tar -xzf archive.tar.gz        # 解压gzip压缩包
tar -cjf archive.tar.bz2 dir/  # 创建bz2压缩包
tar -xjf archive.tar.bz2       # 解压bz2压缩包

# zip压缩
zip archive.zip file1 file2    # 创建zip压缩包
unzip archive.zip              # 解压zip压缩包

# gzip压缩
gzip file                      # 压缩文件
gunzip file.gz                 # 解压文件
```

## ⚡ 实用技巧

```bash
# 命令历史
history                      # 查看命令历史
!!                          # 重复上一条命令
!n                          # 执行历史中第n条命令
!string                     # 执行最近以string开头的命令

# 快捷键
Ctrl + C                    # 终止当前命令
Ctrl + Z                    # 暂停当前命令
Ctrl + D                    # 退出终端/结束输入
Ctrl + L                    # 清屏
Ctrl + A                    # 移动到行首
Ctrl + E                    # 移动到行尾
Ctrl + U                    # 删除到行首
Ctrl + K                    # 删除到行尾
Ctrl + R                    # 反向搜索历史命令

# 重定向和管道
command > file            # 输出重定向到文件(覆盖)
command >> file           # 输出重定向到文件(追加)
command < file            # 从文件输入
command1 | command2         # 管道: command1输出作为command2输入

# 组合命令
command1 && command2       # 命令1成功才执行命令2
command1 || command2        # 命令1失败才执行命令2
command1 ; command2         # 顺序执行两个命令

# 别名设置
alias ll='ls -alF'         # 创建别名
alias grep='grep --color=auto'
unalias ll                 # 删除别名
```

## 🐧 系统管理

```bash
# 服务管理 (systemd)
sudo systemctl start service    # 启动服务
sudo systemctl stop service     # 停止服务
sudo systemctl restart service  # 重启服务
sudo systemctl status service   # 查看服务状态
sudo systemctl enable service   # 设置开机启动
sudo systemctl disable service  # 禁用开机启动

# 服务管理 (init.d)
sudo service service start      # 启动服务
sudo service service stop       # 停止服务
sudo service service restart    # 重启服务

# 定时任务
crontab -l                    # 查看当前用户的定时任务
crontab -e                    # 编辑定时任务
crontab -r                    # 删除所有定时任务

# 系统日志
journalctl -xe                # 查看系统日志
dmesg                         # 查看内核日志
tail -f /var/log/syslog       # 实时查看系统日志
```

## 🔒 安全相关

```bash
# SSH相关
ssh user@host                # SSH连接
scp file user@host:path      # 安全复制文件
scp -r dir user@host:path    # 安全复制目录

# 防火墙 (ufw)
sudo ufw enable              # 启用防火墙
sudo ufw disable             # 禁用防火墙
sudo ufw status              # 查看防火墙状态
sudo ufw allow 22            # 允许SSH端口
sudo ufw deny 22             # 拒绝SSH端口

# 文件完整性
md5sum file                  # 计算MD5校验和
sha256sum file               # 计算SHA256校验和
```

## 📝 文本处理

```bash
# 文本处理
sort file                   # 排序文件
uniq file                   # 去除重复行
wc file                     # 统计行数、单词数、字符数
cut -d',' -f1 file          # 按逗号分隔取第一列
awk '{print $1}' file       # 打印第一列
sed 's/old/new/g' file      # 替换文本
tr 'a-z' 'A-Z' < file      # 转换大小写

# 比较文件
diff file1 file2            # 比较文件差异
cmp file1 file2             # 比较文件是否相同
```

---

## 💡 使用提示

1. **使用tab补全**: 输入部分命令或文件名后按Tab键自动补全
2. **查看命令帮助**: `command --help` 或 `man command`
3. **学习新命令**: 使用`man`命令查看详细手册
4. **小心rm -rf**: 这是最危险的命令之一，使用前务必确认路径
5. **使用history**: 充分利用命令历史提高效率

## 🆘 紧急情况

- **误删重要文件**: 立即停止写入操作，尝试恢复工具
- **系统无法启动**: 使用Live USB尝试修复
- **忘记root密码**: 进入单用户模式重置
- **磁盘空间满**: 清理日志和临时文件

---

*最后更新: 2026-04-16*
*适用于大多数Linux发行版*