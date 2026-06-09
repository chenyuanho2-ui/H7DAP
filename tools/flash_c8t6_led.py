#!/usr/bin/env python3
"""
烧录 c8t6_led 到 STM32F103C8T6 (蓝 pills)

支持:
  1. 通过外购 DAPLink 烧录
  2. 通过 H750 DAPLink 烧录 (如果 H750 被正确识别)

用法:
    # 通过外购 DAPLink 烧录
    python flash_c8t6_led.py --daplink purchased

    # 通过 H750 DAPLink 烧录 (如果 H750 DAPLink 可用)
    python flash_c8t6_led.py --daplink h750

    # 指定 UID
    python flash_c8t6_led.py --uid <UID>

    # 不烧录，只检测 H750 DAPLink
    python flash_c8t6_led.py --check-h750

    # 完整流程: 先编译 H750 固件 → 用外购 DAPLink 烧录到 H750 → 验证 H750 DAPLink → 烧录 c8t6_led
    python flash_c8t6_led.py --all
"""

import sys
import os
import subprocess
import argparse
import time

# ---------- 路径配置 ----------
# H750 项目目录
H750_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H750_ELF = os.path.join(H750_DIR, "build", "Debug", "daplink.elf")
H750_BIN = os.path.join(H750_DIR, "build", "Debug", "daplink.bin")

# c8t6_led 项目目录
C8T6_LED_DIR = os.path.abspath(
    os.path.join(H750_DIR, "..", "..", "..", "CMAKE", "c8t6_led", "LED")
)
C8T6_LED_ELF = os.path.join(C8T6_LED_DIR, "build", "Debug", "LED.elf")

# 外购 DAPLink UID (pyocd list 获取)
PURCHASED_DAPLINK_UID = "00000080204985410516800413598705a5a5a5a59796990e"

# 默认目标
H750_TARGET = "stm32h750xx"
C8T6_TARGET = "stm32f103rc"


def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"命令未找到: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"


def find_daplink(uid=None):
    """检测 DAPLink"""
    rc, out, err = run_cmd(["pyocd", "list"])
    if rc != 0:
        return None, f"pyOCD 命令失败: {err}"

    if uid:
        if uid in out:
            return uid, None
        return None, f"未找到 UID 为 {uid[:20]}... 的 DAPLink"

    # 返回第一个 CMSIS-DAP
    for line in out.split('\n'):
        if 'CMSIS-DAP' in line:
            parts = line.strip().split()
            if len(parts) >= 5 and parts[1].startswith('CMSIS-DAP'):
                # 格式: 0   Luxiaoban Flash Pro(CMSIS-DAP)   UID   n/a
                # 但 UID 的位置可能不同，我们找包含数字+字母的字段
                for p in parts:
                    if len(p) > 20 and any(c.isalpha() for c in p) and any(c.isdigit() for c in p):
                        return p, None
                return parts[2], None
    return None, "未检测到 CMSIS-DAP 设备"


def check_h750_daplink():
    """检查 H750 是否被检测为 DAPLink"""
    print("=" * 55)
    print("  检查 H750 DAPLink 状态")
    print("=" * 55)

    uid, err = find_daplink()
    if err:
        print(f"❌ {err}")
        print()
        print("H750 DAPLink 未被检测到。可能的原因:")
        print("  1. H750 的 USB 未连接")
        print("  2. 固件未正确烧录")
        print("  3. Windows 驱动问题 (需要用 Zadig 安装 WinUSB)")
        print("  4. USB 线只供电不传数据")
        print()
        print("💡 请确认:")
        print("  - 拔掉外购 DAPLink (如有)")
        print("  - 单独插入 H750 的 USB 口")
        print("  - 打开设备管理器检查是否出现新设备")
        print("  - 如有 'CMSIS-DAP v2 Debugger' 但带黄色感叹号，用 Zadig 安装 WinUSB")
        return False

    # 检测到的 UID
    print(f"✅ 检测到 DAPLink!")
    print(f"   UID: {uid}")

    # 查看设备详情
    rc, out, err = run_cmd(["pyocd", "commander", "-u", uid, "-c", "info"], timeout=15)
    if rc == 0:
        print(f"   设备信息:\n{out}")
    else:
        print(f"   ⚠️  无法获取设备详细信息")

    return True


def flash_h750(uid):
    """用外购 DAPLink 烧录 H750"""
    print(f"\n🔥 烧录 H750 (使用 DAPLink: {uid[:20]}...)")

    if not os.path.exists(H750_ELF):
        print(f"❌ 未找到 {H750_ELF}")
        print("   请先编译 H750 固件: cd daplink && cmake --build --preset Debug")
        return False

    cmd = [
        "pyocd", "flash",
        "-t", H750_TARGET,
        "-u", uid,
        "-e", "chip",
        "-a", "0x08000000",
        H750_ELF
    ]

    rc, out, err = run_cmd(cmd, timeout=120)
    if rc != 0:
        print(f"❌ 烧录失败:\n{err}")
        return False

    print(f"✅ H750 烧录成功!")
    return True


def flash_c8t6(uid):
    """通过 DAPLink 烧录 c8t6_led"""
    print(f"\n🔥 烧录 c8t6_led (STM32F103C8T6) ...")

    if not os.path.exists(C8T6_LED_ELF):
        print(f"❌ 未找到 {C8T6_LED_ELF}")
        print("   请确认 c8t6_led 项目已编译")
        return False

    cmd = [
        "pyocd", "flash",
        "-t", C8T6_TARGET,
        "-u", uid,
        "-e", "chip",
        C8T6_LED_ELF
    ]

    rc, out, err = run_cmd(cmd, timeout=120)
    if rc != 0:
        print(f"❌ 烧录失败:\n{err}")
        return False

    print(f"✅ c8t6_led 烧录成功!")
    return True


def build_h750():
    """编译 H750 固件"""
    print("\n🔨 编译 H750 固件...")
    ninja_file = os.path.join(H750_DIR, "build", "Debug", "build.ninja")
    if not os.path.exists(ninja_file):
        rc, _, err = run_cmd(["cmake", "--preset", "Debug"], timeout=60, cwd=H750_DIR)
        if rc != 0:
            print(f"❌ CMake 配置失败: {err}")
            return False

    rc, out, err = run_cmd(["cmake", "--build", "--preset", "Debug"],
                           timeout=120, cwd=H750_DIR)
    if rc != 0:
        print(f"❌ 编译失败:\n{err}")
        return False

    # 生成 .bin
    run_cmd(["arm-none-eabi-objcopy", "-O", "binary", H750_ELF, H750_BIN])

    print(f"✅ 编译成功!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="c8t6_led 烧录工具 — 支持外购 DAPLink 和 H750 DAPLink"
    )
    parser.add_argument("--daplink", choices=["purchased", "h750"],
                        help="使用哪个 DAPLink: purchased (外购) 或 h750 (H750 上的)")
    parser.add_argument("--uid", help="DAPLink UID (覆盖自动检测)")
    parser.add_argument("--check-h750", action="store_true",
                        help="检查 H750 DAPLink 是否被检测到")
    parser.add_argument("--all", action="store_true",
                        help="完整流程: 编译 H750 → 烧录 H750 → 检查 H750 → 烧录 c8t6")
    parser.add_argument("--build", action="store_true",
                        help="先编译 H750 固件")

    args = parser.parse_args()

    # 检查 H750
    if args.check_h750:
        check_h750_daplink()
        return

    # 编译 H750 固件
    if args.build or args.all:
        if not build_h750():
            sys.exit(1)

    # 完整流程
    if args.all:
        print("\n🔄 完整流程: 编译 → 烧录 H750 → 检查 → 烧录 c8t6")

        # 1. 找到外购 DAPLink
        uid, err = find_daplink(PURCHASED_DAPLINK_UID)
        if err:
            print(f"❌ 未找到外购 DAPLink:\n{err}")
            sys.exit(1)
        print(f"✅ 检测到外购 DAPLink: {uid[:20]}...")

        # 2. 烧录 H750
        if not flash_h750(uid):
            print("⚠️  H750 烧录失败")
            sys.exit(1)

        # 3. 等待 H750 枚举
        print("\n⏳ 等待 H750 DAPLink 枚举 (5 秒)...")
        time.sleep(5)

        # 4. 检查 H750 DAPLink
        if not check_h750_daplink():
            print("\n⚠️  H750 DAPLink 未检测到")
            print("   继续用外购 DAPLink 烧录 c8t6_led...")
            h750_uid = uid
        else:
            # 找到新检测到的 UID (非外购 DAPLink)
            new_uid, _ = find_daplink()
            if new_uid and new_uid != PURCHASED_DAPLINK_UID:
                h750_uid = new_uid
                print(f"\n✅ H750 DAPLink 已识别! (UID: {h750_uid[:20]}...)")
            else:
                h750_uid = uid
                print("\n⚠️  使用外购 DAPLink 烧录 c8t6_led")

        # 5. 烧录 c8t6_led
        if not flash_c8t6(h750_uid):
            sys.exit(1)

        print("\n🎉 全部完成!")
        return

    # 指定 DAPLink
    if args.daplink == "purchased":
        uid = args.uid or PURCHASED_DAPLINK_UID
    elif args.daplink == "h750":
        uid, err = find_daplink(args.uid)
        if err:
            print(f"❌ H750 DAPLink 未检测到:\n{err}")
            sys.exit(1)
    else:
        uid = args.uid or PURCHASED_DAPLINK_UID

    # 烧录 c8t6
    if not flash_c8t6(uid):
        sys.exit(1)


if __name__ == "__main__":
    main()
