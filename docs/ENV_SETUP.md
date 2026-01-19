# 环境配置快速指南

本指南帮助你快速配置 TuShare Token 和环境变量。

---

## 📋 前置要求

### 1. 获取 TuShare Token

**步骤：**

1. 访问 TuShare Pro 官网：https://tushare.pro/register
2. 注册账号（可以使用邮箱或手机号）
3. 登录后，进入「个人中心」→「接口TOKEN」
4. 复制你的 Token（类似：`1234567890abcdef1234567890abcdef`）

**示例：**
```
Token: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

---

## 🔧 配置环境变量

### 方法1：使用 .env 文件（推荐）✨

#### Step 1: 编辑 .env 文件

```bash
# 打开 .env 文件
vim .env  # 或使用其他编辑器: code .env, nano .env

# 或者直接用命令替换
# 将下面的 YOUR_ACTUAL_TOKEN 替换为你的实际 Token
sed -i 's/your_tushare_token_here/YOUR_ACTUAL_TOKEN/' .env
```

**修改后的 .env 文件应该像这样：**
```bash
TUSHARE_TOKEN=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
CACHE_DIR=data/cache
OUTPUT_DIR=output
MODEL_DIR=models
```

#### Step 2: 加载环境变量

```bash
# 方法A：使用 source 命令（推荐）
source scripts/load_env.sh

# 方法B：手动加载（如果脚本有问题）
export $(cat .env | xargs)

# 方法C：每次打开终端自动加载
# 在 ~/.bashrc 或 ~/.zshrc 中添加：
# source /home/oceaneye/gitee/T1.AI/scripts/load_env.sh
```

**验证：**
```bash
# 检查环境变量是否设置成功
echo $TUSHARE_TOKEN

# 预期输出：1234567890abcdef...（你的实际Token）
```

---

### 方法2：直接在终端设置（临时）

```bash
# 设置环境变量（仅在当前终端会话有效）
export TUSHARE_TOKEN="your_actual_token_here"

# 验证
echo $TUSHARE_TOKEN
```

**注意：** 关闭终端后会失效，需要重新设置 ⚠️

---

### 方法3：在脚本中设置（不推荐）

```bash
# 在运行脚本前临时设置
TUSHARE_TOKEN="your_token" python scripts/build_sequence_dataset.py ...
```

**缺点：** Token 暴露在命令历史中，不安全 ⚠️

---

## ✅ 验证配置

### 快速测试脚本

创建测试脚本验证 Token 是否有效：

```bash
# 创建测试脚本
cat > test_tushare_token.py << 'EOF'
#!/usr/bin/env python
"""测试 TuShare Token 是否有效"""
import os
import sys

# 检查环境变量
token = os.environ.get("TUSHARE_TOKEN")
if not token or token == "your_tushare_token_here":
    print("❌ 错误：TUSHARE_TOKEN 未设置或使用默认值")
    print("请先设置环境变量：")
    print("  export TUSHARE_TOKEN='your_actual_token'")
    sys.exit(1)

print(f"✅ Token 已设置: {token[:8]}****{token[-4:]}")

# 测试 API 调用
try:
    import tushare as ts
    pro = ts.pro_api(token)

    # 测试查询沪深300成分股
    df = pro.index_weight(index_code='000300.SH', start_date='20240101', end_date='20240101')

    if df.empty:
        print("⚠️  警告：API 调用成功但返回空数据（可能是积分不足）")
    else:
        print(f"✅ API 测试成功！查询到 {len(df)} 条数据")
        print("\n示例数据（前3条）：")
        print(df.head(3))

except ImportError:
    print("❌ 错误：未安装 tushare 库")
    print("请安装：pip install tushare")
    sys.exit(1)
except Exception as e:
    print(f"❌ API 调用失败：{e}")
    print("\n可能的原因：")
    print("  1. Token 无效")
    print("  2. 积分不足（部分接口需要积分）")
    print("  3. 网络问题")
    sys.exit(1)

print("\n🎉 环境配置完成！可以开始使用了")
EOF

# 运行测试
python test_tushare_token.py
```

**预期输出：**
```
✅ Token 已设置: 12345678****cdef
✅ API 测试成功！查询到 300 条数据

示例数据（前3条）：
  index_code   con_code     trade_date  weight
0  000300.SH  600519.SH     20240101    2.45
1  000300.SH  000333.SZ     20240101    1.82
2  000300.SH  601318.SH     20240101    3.12

🎉 环境配置完成！可以开始使用了
```

---

## 🔒 安全建议

### 1. 保护 .env 文件

```bash
# 确保 .env 不会被提交到 Git
cat .gitignore | grep ".env"
# 应该看到：.env

# 如果没有，手动添加
echo ".env" >> .gitignore
```

### 2. 使用环境变量管理工具（可选）

**推荐工具：**
- `direnv` - 自动加载目录级环境变量
- `python-dotenv` - Python 项目中加载 .env

**安装 direnv：**
```bash
# Ubuntu/Debian
sudo apt-get install direnv

# macOS
brew install direnv

# 配置（添加到 ~/.bashrc 或 ~/.zshrc）
eval "$(direnv hook bash)"  # 或 zsh

# 使用
# 创建 .envrc 文件
echo "dotenv" > .envrc
direnv allow
```

---

## 🛠️ 常见问题

### Q1: Token 设置了但脚本仍然报错

**检查清单：**
```bash
# 1. 验证环境变量
echo $TUSHARE_TOKEN

# 2. 检查是否在新终端中
# 如果是新终端，需要重新加载环境变量
source scripts/load_env.sh

# 3. 检查脚本是否正确读取
python -c "import os; print(os.environ.get('TUSHARE_TOKEN'))"
```

### Q2: API 调用提示积分不足

**解决方案：**
- 查看你的积分：https://tushare.pro/user/token
- 部分接口需要积分，参考：[docs/TUSHARE_API_REFERENCE.md](TUSHARE_API_REFERENCE.md)
- 使用免费接口（如 `daily` 日线行情）

### Q3: 如何在多个项目中共享 Token

**方法1：全局环境变量**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export TUSHARE_TOKEN="your_token"
```

**方法2：中央配置文件**
```bash
# 创建 ~/.tushare_token
echo "your_token" > ~/.tushare_token
chmod 600 ~/.tushare_token

# 在脚本中读取
export TUSHARE_TOKEN=$(cat ~/.tushare_token)
```

---

## 📚 下一步

配置完成后，你可以：

1. **运行数据拉取测试：**
   ```bash
   python scripts/build_sequence_dataset.py \
     --start 20240101 \
     --end 20240131 \
     --symbols 600519,000333,601318 \
     --source tushare \
     --seq-len 30
   ```

2. **查看完整训练流程：**
   - [docs/QUICKSTART.md](QUICKSTART.md) - 完整训练流程
   - [docs/ACTUAL_COMMANDS.md](ACTUAL_COMMANDS.md) - 实际可用命令

3. **扩展特征：**
   - [docs/TUSHARE_API_REFERENCE.md](TUSHARE_API_REFERENCE.md) - TuShare 高阶数据接口

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-15
