#!/usr/bin/env python3
"""
DAPLink 烧录与验证工具 (pyOCD 版)
使用外购 DAPLink (Luxiaoban Flash Pro) 烧录 STM32H750XBH6。

用法:
    python flash_and_verify.py                              # 默认: 编译 + 烧录 + 验证
    python flash_and_verify.py --no-build                    # 只烧录不编译
    python flash_and_verify.py --no-flash                    # 只验证不烧录
    python flash_and_verify.py --target stm32f103c8          # 烧录到其他目标芯片
"""

import subprocess
import sys
import time
import os
import json

# ---------- 配置 ----------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELF_FILE    = os.path.join(PROJECT_DIR, "build", "Debug", "daplink.elf")
BIN_FILE    = os.path.join(PROJECT_DIR, "build", "Debug", "daplink.bin")

# 外购 DAPLink 的 UID (pyocd list 获取)
# 如果更换了设备，请修改此值或传入 --uid 参数
PURCHASED_DAPLINK_UID = "00000080204985410516800413598705a5a5a5a59796990e"

# 默认目标芯片
DEFAULT_TARGET = "stm32h750xx"


def run_cmd(cmd, timeout=60, cwd=None):
    """运行命令并返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"命令未找到: {cmd[0]}，请确认已安装并加入 PATH"
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"


def check_tools():
    """检查必要工具是否可用"""
    print("\n检查必要工具...")
    missing = []

    # 检查 pyocd
    rc, out, _ = run_cmd(["pyocd", "--version"])
    if rc != 0:
        missing.append("pyocd → pip install pyocd")
    else:
        ver = out.strip()
        print(f"  pyocd: {ver}")

    # 检查 arm-none-eabi-objcopy (编译时需要)
    rc2, _, _ = run_cmd(["arm-none-eabi-objcopy", "--version"])
    if rc2 != 0:
        missing.append("arm-none-eabi-gcc toolchain → 请安装 ARM GCC")

    # 检查 cmake
    rc3, _, _ = run_cmd(["cmake", "--version"])
    if rc3 != 0:
        missing.append("cmake → 请安装 CMake")

    # 检查 ninja
    rc4, _, _ = run_cmd(["ninja", "--version"])
    if rc4 != 0:
        missing.append("ninja → 请安装 Ninja build")

    if missing:
        print("❌ 缺少以下工具:")
        for m in missing:
            print(f"   {m}")
        return False

    print("✅ 必要工具已就绪")
    return True


def find_purchased_daplink(uid=None):
    """检测外购 DAPLink (Luxiaoban Flash Pro) 是否连接"""
    print("\n[检测 DAPLink] 扫描调试器...")

    rc, out, err = run_cmd(["pyocd", "list"])

    if rc != 0:
        print(f"❌ pyOCD 命令失败: {err}")
        return False

    print(f"  pyocd list 输出:\n{out}")

    # 查找指定 UID 或任意 CMSIS-DAP
    search_uid = uid or PURCHASED_DAPLINK_UID
    if search_uid in out:
        print(f"✅ 找到 DAPLink (UID: {search_uid[:20]}...)")
        return search_uid
    elif "CMSIS-DAP" in out or "daplink" in out.lower():
        # 尝试提取第一个 CMSIS-DAP 的 UID
        print("⚠️  未找到指定 UID 的 DAPLink，但检测到其他 CMSIS-DAP 设备")
        return False
    else:
        print("❌ 未检测到 DAPLink 设备")
        print("   请确认:")
        print("     - DAPLink 已插入 USB")
        print("     - 目标板已上电")
        print("     - SWD 线已连接 (SWCLK, SWDIO, GND)")
        return False


def build_firmware():
    """编译固件"""
    print("\n[编译固件]...")

    project_build = os.path.join(PROJECT_DIR, "build", "Debug")

    # 确保 build 目录已配置
    ninja_file = os.path.join(project_build, "build.ninja")
    if not os.path.exists(ninja_file):
        print("  CMake 配置...")
        rc1, _, err1 = run_cmd(["cmake", "--preset", "Debug"], timeout=60, cwd=PROJECT_DIR)
        if rc1 != 0:
            print(f"  ❌ CMake 配置失败:\n{err1}")
            return False

    rc, out, err = run_cmd(["cmake", "--build", "--preset", "Debug"],
                           timeout=120, cwd=PROJECT_DIR)
    if rc != 0:
        print("  ❌ 编译失败:")
        for line in (out + err).split('\n'):
            if 'error:' in line.lower():
                print(f"    {line.strip()}")
        return False

    if not os.path.exists(ELF_FILE):
        print(f"  ❌ 未找到 {ELF_FILE}")
        return False

    # 生成 .bin 文件
    rc2, _, _ = run_cmd(["arm-none-eabi-objcopy", "-O", "binary", ELF_FILE, BIN_FILE])
    if rc2 != 0 or not os.path.exists(BIN_FILE):
        print("  ❌ 生成 .bin 文件失败")
        return False

    elf_size = os.path.getsize(ELF_FILE)
    bin_size = os.path.getsize(BIN_FILE)
    print(f"  ✅ 编译成功")
    print(f"     ELF: {elf_size / 1024:.1f} KB")
    print(f"     BIN: {bin_size / 1024:.1f} KB")
    return True


def flash_with_pyocd(uid, elf_path, target=DEFAULT_TARGET):
    """通过 pyocd + 外购 DAPLink 烧录固件到指定目标"""
    print(f"\n[烧录] 目标: {target}, DAPLink UID: {uid[:20]}...")

    cmd = [
        "pyocd", "flash",
        "-t", target,
        "-u", uid,
        "-e", "chip",       # 整片擦除
        "--no-reset",       # 烧录后不立即复位 (由程序自行复位)
        "-a", "0x08000000", # 起始地址
        elf_path
    ]

    rc, out, err = run_cmd(cmd, timeout=120)
    if rc != 0:
        print(f"  ❌ 烧录失败: {err}")
        for line in out.split('\n'):
            if line.strip():
                print(f"    {line.strip()}")
        # 如果第一次失败，尝试用 .bin 文件
        print("\n  尝试用 .bin 文件烧录...")
        bin_path = elf_path.replace('.elf', '.bin')
        if os.path.exists(bin_path):
            cmd2 = [
                "pyocd", "flash",
                "-t", target,
                "-u", uid,
                "-e", "chip",
                "-a", "0x08000000",
                bin_path
            ]
            rc2, out2, err2 = run_cmd(cmd2, timeout=120)
            if rc2 == 0:
                print("  ✅ 烧录成功 (使用 .bin)!")
                return True
            print(f"  ❌ .bin 烧录也失败: {err2}")
        return False

    print("  ✅ 烧录成功!")
    return True


def verify_daplink(target_chip=None):
    """验证 DAPLink (H750) 是否正常枚举"""
    print("\n[验证] 检查 CMSIS-DAP v2 调试器...")

    # 等待 USB 枚举
    print("  等待 USB 枚举 (3 秒)...")
    time.sleep(3)

    # pyocd list
    rc, out, err = run_cmd(["pyocd", "list"])

    if rc != 0:
        print(f"  ❌ pyOCD 命令失败")
        return False

    print(f"  pyOCD list 输出:\n{out}")

    if "daplink" in out.lower() or "cmsis-dap" in out.lower() or "winusb" in out.lower():
        print("  ✅ DAPLink 设备已检测到!")
    else:
        print("  ❌ 未检测到 DAPLink 设备")
        print("    请检查:")
        print("      - USB 线是否连接")
        print("      - Windows 是否用 Zadig 安装了 WinUSB 驱动")
        print("      - 设备管理器中有 'WinUSB Device' 或 'CMSIS-DAP'")
        return False

    # 如果指定了目标芯片，尝试 pyocd commander
    if target_chip:
        print(f"\n  [验证] 尝试连接目标芯片 ({target_chip})...")

        # 尝试 info
        rc2, out2, err2 = run_cmd([
            "pyocd", "commander",
            "-t", target_chip,
            "-c", "info"
        ], timeout=15)

        if "IDCODE" in out2 or "Unique ID" in out2 or rc2 == 0:
            print(f"  ✅ 成功连接到目标芯片!")
            for line in out2.split('\n'):
                if any(k in line.lower() for k in ['idcode', 'unique', 'target', 'vendor', 'part']):
                    print(f"    {line.strip()}")
        else:
            print(f"  ⚠️  未能连接目标芯片")
            print(f"    {err2[:200] if err2 else out2[:200]}")

    return True


def main():
    print("=" * 55)
    print("  DAPLink 烧录与验证工具 (pyOCD + 外购 DAPLink)")
    print("=" * 55)

    # 解析参数
    no_build = "--no-build" in sys.argv
    no_flash = "--no-flash" in sys.argv
    target = DEFAULT_TARGET
    uid = PURCHASED_DAPLINK_UID
    for arg in sys.argv:
        if arg.startswith("--target="):
            target = arg.split("=", 1)[1]
        if arg.startswith("--uid="):
            uid = arg.split("=", 1)[1]

    # 检查工具链
    if not check_tools():
        sys.exit(1)

    # 检测 DAPLink
    found_uid = find_purchased_daplink(uid)
    if not found_uid:
        sys.exit(1)

    # 编译
    if not no_build:
        if not build_firmware():
            sys.exit(1)
    else:
        if not os.path.exists(ELF_FILE):
            print(f"❌ 未找到 {ELF_FILE}，无法烧录")
            sys.exit(1)

    # 烧录
    if not no_flash:
        if not flash_with_pyocd(found_uid, ELF_FILE, target):
            print("\n⚠️  烧录失败。")
            sys.exit(1)

    # 验证 (如果烧录的是 H750，验证它是否作为 DAPLink 正常工作)
    if target == DEFAULT_TARGET and not no_flash:
        print("\n[验证] H750 DAPLink 功能...")
        # 注意: 这里只是提示，实际需要用户手动拔掉外购 DAPLink 再插入 H750 USB
        print("  提示: 如果烧录成功，请:")
        print("    1. 拔掉外购 DAPLink")
        print("    2. 重新插入 H750 的 USB")
        print("    3. 运行 python tools/pyocd_check.py 来检测")
        print("    4. 如果 Windows 没有自动加载驱动，用 Zadig 安装 WinUSB")

    print("\n" + "=" * 55)
    print("  完成!")
    print("=" * 55)


if __name__ == "__main__":
    main()
