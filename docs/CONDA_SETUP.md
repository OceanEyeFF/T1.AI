# Conda 环境配置指南

本文档介绍如何使用 Conda 创建和管理 A-Share Lab 项目的独立 Python 环境。

---

## 🎯 为什么使用 Conda？

✅ **依赖隔离** - 不影响系统 Python 和其他项目
✅ **版本管理** - 精确控制 Python 和库的版本
✅ **跨平台** - Windows/Linux/macOS 统一管理
✅ **科学计算优化** - PyTorch、NumPy 等库的优化版本

---

## 📋 前置要求

### 安装 Conda

**选择一个安装（推荐 Miniconda）：**

#### Option 1: Miniconda（轻量级，推荐）⭐

```bash
# Linux
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# macOS
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# 或使用 brew (macOS)
brew install miniconda
```

#### Option 2: Anaconda（完整版，包含Jupyter等工具）

访问：https://www.anaconda.com/download

---

## 🚀 快速开始（一键安装）

### 方法1：使用自动化脚本（推荐）✨

```bash
# 运行自动化设置脚本
bash scripts/setup_conda_env.sh
```

**脚本会自动完成：**
1. 检查 conda 是否安装
2. 创建名为 `ashare-lab` 的环境
3. 安装所有依赖（PyTorch、pandas、tushare等）
4. 安装项目到开发模式

**预期时间：** 3-5分钟

**完成后激活环境：**
```bash
conda activate ashare-lab
```

---

### 方法2：手动安装

#### Step 1: 创建环境

```bash
# 使用 environment.yml 创建环境
conda env create -f environment.yml
```

**预期输出：**
```
Collecting package metadata (repodata.json): done
Solving environment: done

Downloading and Extracting Packages:
...

Preparing transaction: done
Verifying transaction: done
Executing transaction: done
#
# To activate this environment, use:
#     conda activate ashare-lab
```

#### Step 2: 激活环境

```bash
conda activate ashare-lab
```

**验证环境：**
```bash
# 检查 Python 版本
python --version
# 应该显示：Python 3.10.x

# 检查环境名称（命令行提示符应该显示 (ashare-lab)）
conda env list
# 应该看到 * ashare-lab 标记
```

#### Step 3: 安装项目（开发模式）

```bash
# 在项目根目录执行
pip install -e ".[dev]"
```

**验证安装：**
```bash
# 运行测试
pytest tests/

# 应该看到：125 passed
```

---

## 🔧 环境管理常用命令

### 激活/退出环境

```bash
# 激活环境
conda activate ashare-lab

# 退出环境
conda deactivate
```

### 查看已安装的包

```bash
# 查看所有包
conda list

# 查看特定包
conda list pandas
conda list torch
```

### 更新环境

**更新所有包：**
```bash
# 激活环境后
conda update --all
```

**更新特定包：**
```bash
conda update pandas
# 或使用 pip
pip install --upgrade tushare
```

### 重建环境

**如果环境出现问题，可以删除并重建：**

```bash
# 1. 删除环境
conda env remove -n ashare-lab

# 2. 重新创建
conda env create -f environment.yml

# 3. 重新安装项目
conda activate ashare-lab
pip install -e ".[dev]"
```

### 导出环境（分享给他人）

```bash
# 导出精确版本（包含所有依赖）
conda env export > environment-lock.yml

# 导出简化版本（只包含手动安装的包）
conda env export --from-history > environment-minimal.yml
```

---

## 🎓 配置开发环境

### 1. 设置自动激活环境

**方法A：修改 shell 配置文件**

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# 自动激活 ashare-lab 环境（当进入项目目录时）
if [[ $PWD == /home/oceaneye/gitee/T1.AI* ]]; then
    conda activate ashare-lab
fi
```

**方法B：使用 direnv（更优雅）**

```bash
# 安装 direnv
# Ubuntu/Debian
sudo apt-get install direnv

# macOS
brew install direnv

# 配置 shell hook
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # 或 ~/.zshrc

# 在项目根目录创建 .envrc
echo 'layout anaconda ashare-lab' > .envrc
echo 'dotenv' >> .envrc

# 授权
direnv allow
```

### 2. 配置 IDE（VS Code / PyCharm）

#### VS Code

1. 安装 Python 扩展
2. 打开命令面板（Ctrl+Shift+P）
3. 选择 `Python: Select Interpreter`
4. 选择 `ashare-lab` 环境（通常路径为 `~/miniconda3/envs/ashare-lab/bin/python`）

**或编辑 `.vscode/settings.json`：**
```json
{
    "python.defaultInterpreterPath": "~/miniconda3/envs/ashare-lab/bin/python",
    "python.terminal.activateEnvironment": true
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. 点击齿轮图标 → Add
3. 选择 Conda Environment → Existing environment
4. 选择 `ashare-lab` 环境

### 3. Jupyter Notebook 配置

```bash
# 激活环境
conda activate ashare-lab

# 安装 ipykernel
conda install ipykernel

# 注册 kernel
python -m ipykernel install --user --name=ashare-lab --display-name "A-Share Lab"

# 启动 Jupyter
jupyter notebook
```

在 Jupyter 中选择 "A-Share Lab" kernel 即可使用项目环境。

---

## 🐛 常见问题

### Q1: `conda: command not found`

**解决方案：**

```bash
# 检查是否安装了 conda
which conda

# 如果没有，需要初始化 conda
~/miniconda3/bin/conda init bash  # 或 zsh

# 重启终端或重新加载配置
source ~/.bashrc  # 或 ~/.zshrc
```

---

### Q2: 创建环境时报错 `PackagesNotFoundError`

**可能原因：** 某些包在指定 channel 中不存在

**解决方案：**

```bash
# 方法1: 添加更多 channel
conda config --add channels conda-forge
conda config --add channels pytorch

# 方法2: 使用 pip 安装缺失的包
conda env create -f environment.yml
conda activate ashare-lab
pip install <missing-package>
```

---

### Q3: PyTorch 安装错误（CUDA 版本）

**CPU 版本（默认）：**
```yaml
# environment.yml 中
- pytorch>=2.0
- pytorch-mutex=1.0=cpu
```

**GPU 版本（NVIDIA CUDA）：**
```yaml
# 修改 environment.yml
- pytorch>=2.0
- pytorch-cuda=11.8  # 或 12.1，根据你的 CUDA 版本
```

**或直接使用 pip：**
```bash
# CPU
pip install torch --index-url https://download.pytorch.org/whl/cpu

# GPU (CUDA 11.8)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**检查 CUDA 版本：**
```bash
nvidia-smi  # 查看 CUDA 版本
```

---

### Q4: 环境变量 TUSHARE_TOKEN 在 conda 环境中失效

**解决方案：**

```bash
# 方法1: 每次激活环境后手动加载
conda activate ashare-lab
source scripts/load_env.sh

# 方法2: 设置环境变量到 conda 环境（推荐）
conda env config vars set TUSHARE_TOKEN="your_token_here"
# 需要重新激活环境
conda deactivate
conda activate ashare-lab

# 验证
echo $TUSHARE_TOKEN
```

---

### Q5: pip install 时提示权限错误

**原因：** 混用了系统 Python 和 conda 环境

**解决方案：**

```bash
# 确保在 conda 环境中
conda activate ashare-lab

# 使用 conda 环境的 pip
which pip  # 应该显示 ~/miniconda3/envs/ashare-lab/bin/pip

# 如果不是，强制使用 conda 的 pip
python -m pip install -e ".[dev]"
```

---

## 📊 环境信息

**查看环境详细信息：**

```bash
# 激活环境
conda activate ashare-lab

# 查看环境信息
conda info

# 查看已安装包
conda list

# 导出环境用于分享
conda env export
```

---

## 🔄 卸载环境

**如果不再需要该环境：**

```bash
# 退出环境
conda deactivate

# 删除环境
conda env remove -n ashare-lab

# 验证
conda env list  # 不应再看到 ashare-lab
```

---

## 📚 参考资源

- **Conda 官方文档：** https://docs.conda.io/
- **Conda Cheat Sheet：** https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html
- **PyTorch 安装指南：** https://pytorch.org/get-started/locally/

---

**文档维护者：** 浮浮酱 & A-Share Lab Team
**最后更新：** 2025-01-15
**版本：** v1.0
