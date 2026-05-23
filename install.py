#!/usr/bin/env python3
"""
QQBot 安装与环境检测脚本
支持: Windows / Linux / macOS
"""

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

REQUIRED_PYTHON_VERSION = (3, 10)
PROJECT_DIR = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_DIR / "venv"
CONFIG_FILE = PROJECT_DIR / "config.json"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"


def color(text: str, code: str) -> str:
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
        return text
    colors = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "bold": "1"}
    codes = [colors.get(c, "0") for c in code.split(",") if c in colors]
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def print_step(step: str, status: str, detail: str = ""):
    status_map = {
        "ok": color(" ✓", "green"),
        "fail": color(" ✗", "red"),
        "warn": color(" ⚠", "yellow"),
        "info": color(" ℹ", "cyan"),
    }
    icon = status_map.get(status, "")
    detail_str = f" - {detail}" if detail else ""
    print(f"  {icon} {step}{detail_str}")


def check_python_version() -> bool:
    print(f"\n{'='*50}")
    print("  QQBot 环境检测与安装")
    print(f"{'='*50}\n")

    print("📦 步骤 1/5: 检测 Python 版本")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    if version >= REQUIRED_PYTHON_VERSION:
        print_step(
            f"Python 版本: {version_str} (路径: {sys.executable})",
            "ok"
        )
        return True
    else:
        print_step(
            f"Python 版本: {version_str} (需要 {'.'.join(map(str, REQUIRED_PYTHON_VERSION))}+)",
            "fail"
        )
        print("\n请安装 Python 3.10 或更高版本:")
        print("  https://www.python.org/downloads/")
        return False


def check_pip() -> bool:
    print(f"\n📦 步骤 2/5: 检测 pip")
    if shutil.which("pip") or (hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix):
        pass
    try:
        import pip
        print_step(f"pip 版本: {pip.__version__}", "ok")
        return True
    except ImportError:
        print_step("pip 未安装", "fail")
        print("\n请安装 pip:")
        print("  python -m ensurepip --upgrade")
        return True


def create_venv() -> bool:
    print(f"\n📦 步骤 3/5: 创建虚拟环境")

    if VENV_DIR.exists():
        print_step(f"虚拟环境已存在: {VENV_DIR}", "ok")
        return True

    try:
        import venv
        print(f"  正在创建虚拟环境...")
        venv.create(VENV_DIR, with_pip=True)
        print_step(f"虚拟环境已创建: {VENV_DIR}", "ok")
        return True
    except Exception as e:
        print_step(f"创建虚拟环境失败: {e}", "fail")
        return False


def get_python_in_venv() -> str:
    if platform.system() == "Windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def install_dependencies() -> bool:
    print(f"\n📦 步骤 4/5: 安装依赖")

    python_path = get_python_in_venv()
    if not os.path.exists(python_path):
        print_step(f"虚拟环境 Python 不存在: {python_path}", "fail")
        return False

    try:
        print("  正在安装依赖 (可能需要几分钟)...")
        result = subprocess.run(
            [python_path, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR
        )
        if result.returncode == 0:
            print_step("依赖安装完成", "ok")
            return True
        else:
            print_step("依赖安装失败", "fail")
            print(f"  错误信息: {result.stderr[:500]}")
            return False
    except Exception as e:
        print_step(f"安装过程异常: {e}", "fail")
        return False


def setup_config() -> bool:
    print(f"\n📦 步骤 5/5: 配置文件")

    if CONFIG_FILE.exists():
        print_step(f"配置文件已存在: {CONFIG_FILE}", "ok")
        return True

    default_config = textwrap.dedent("""\
    {
      "ws_host": "0.0.0.0",
      "ws_port": 8080,
      "api_host": "127.0.0.1",
      "api_port": 3000,
      "api_token": "",
      "bot_name": "小助手",
      "welcome_enabled": true,
      "welcome_message": "欢迎新群友 {user_name} 加入本群！请先阅读群公告，祝您玩得开心~",
      "welcome_image": "",
      "log_level": "INFO",
      "web_host": "0.0.0.0",
      "web_port": 9090
    }
    """)
    try:
        CONFIG_FILE.write_text(default_config, encoding="utf-8")
        print_step(f"已生成默认配置文件: {CONFIG_FILE}", "ok")
        return True
    except Exception as e:
        print_step(f"生成配置文件失败: {e}", "fail")
        return False


def print_success():
    system = platform.system()
    python_in_venv = get_python_in_venv()

    print(f"\n{'='*50}")
    print(color("  ✅  安装完成！", "green,bold"))
    print(f"{'='*50}\n")

    print("📋 启动机器人:")
    if system == "Windows":
        print(f"  {color(f'{VENV_DIR}\\Scripts\\activate', 'cyan')}  &&  python main.py")
        print(f"  或直接:  {color('start.bat', 'cyan')}")
    else:
        print(f"  {color(f'source {VENV_DIR}/bin/activate', 'cyan')}  &&  python main.py")

    print(f"\n🔧 napcat 配置说明:")
    print(f"  在 napcat 的 网络配置 中，添加 反向WebSocket 连接:")
    print(f"    地址: {color(f'ws://本机IP:8080/', 'yellow')}")
    print(f"  如果 napcat 和机器人在同一台电脑，本机IP 填 {color('127.0.0.1', 'yellow')}")
    print(f"  如果 napcat 在另一台电脑，请确保 8080 端口已放行防火墙")

    print(f"\n📝 配置文件: {color('config.json', 'cyan')}")
    print(f"  可修改欢迎语、端口、Token 等设置")

    print(f"\n🌐 网页管理后台:")
    print(f"    地址: {color('http://127.0.0.1:9090', 'yellow')}")
    print(f"  如果远程访问，请用 {color('http://本机IP:9090', 'yellow')}")

    print(f"\n{'='*50}\n")


def main():
    steps = [
        ("Python 版本检测", check_python_version),
        ("pip 检测", check_pip),
        ("虚拟环境创建", create_venv),
        ("依赖安装", install_dependencies),
        ("配置文件生成", setup_config),
    ]

    all_ok = True
    for step_name, step_func in steps:
        if not step_func():
            all_ok = False
            print_step(f"{step_name} 失败，后续步骤可能受影响", "warn")

    if all_ok:
        print_success()
    else:
        print(color(f"\n  ❌ 部分步骤未完成，请检查上方错误信息\n", "red,bold"))
        sys.exit(1)


if __name__ == "__main__":
    main()
