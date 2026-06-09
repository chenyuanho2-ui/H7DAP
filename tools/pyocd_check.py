#!/usr/bin/env python3
"""
pyOCD 调试器检测与诊断工具

检测所有连接的 CMSIS-DAP 调试器，显示详细信息，
识别 H750 DAPLink 和外购 DAPLink。

用法:
    python pyocd_check.py                  # 检测所有调试器
    python pyocd_check.py --uid <UID>      # 指定 UID
    python pyocd_check.py --target         # 查看可用目标
    python pyocd_check.py --probe          # 查看 probe 详细信息
    python pyocd_check.py --all            # 显示所有信息
"""

import sys
import subprocess
import argparse


def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"命令未找到: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"


def list_probes():
    """列出所有调试探测器"""
    print("=" * 55)
    print("  pyOCD 调试器检测")
    print("=" * 55)

    # pyocd list
    rc, out, err = run_cmd(["pyocd", "list"])
    if rc != 0:
        print(f"❌ pyOCD 命令失败:\n{err}")
        return False

    print("\n📋 pyocd list:")
    print(out)
    return out


def list_targets(filter_str=None):
    """列出可用目标"""
    rc, out, err = run_cmd(["pyocd", "list", "--targets"])
    if rc != 0:
        print(f"❌ 无法获取目标列表:\n{err}")
        return

    lines = out.split('\n')
    # 只显示 STM32 相关
    stm32_lines = [l for l in lines if 'STM32' in l or 'stm32' in l]
    print(f"\n📋 STM32 目标 ({len(stm32_lines)} 个):")
    for l in stm32_lines[:40]:
        print(f"  {l}")


def probe_info(uid=None):
    """获取指定调试器的详细信息"""
    print("\n🔍 调试器详细信息:")

    # 使用 pyocd commander 获取信息
    cmd = ["pyocd", "commander"]
    if uid:
        cmd.extend(["-u", uid])
    cmd.extend(["-c", "info"])

    rc, out, err = run_cmd(cmd, timeout=30)
    if rc == 0:
        # 只显示有用的信息
        for line in out.split('\n'):
            if any(k in line.lower() for k in ['idcode', 'unique', 'vendor',
                                                'part', 'target', 'debug',
                                                'cmsis', 'daplink']):
                print(f"  {line.strip()}")
    else:
        # pyocd commander 失败，尝试用 pyocd list -t
        print(f"  ⚠️  commander 无法获取信息:\n    {err[:100]}")
        rc2, out2, _ = run_cmd(["pyocd", "list", "-t"])
        print(f"  pyocd list -t:\n{out2}")


def check_winusb():
    """检查 WinUSB 驱动状态"""
    print("\n🔧 WinUSB 驱动检查:")

    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        print("  ⚠️  pyserial 未安装，无法枚举串口")

    # 用 powershell 获取 USB 设备信息
    rc, out, err = run_cmd([
        "powershell", "-Command",
        "Get-PnPDevice | Where-Object {$_.Class -eq 'USB' -or "
        "$_.FriendlyName -like '*CMSIS*' -or "
        "$_.FriendlyName -like '*DAP*' -or "
        "$_.FriendlyName -like '*WinUSB*' -or "
        "$_.FriendlyName -like '*ARM*'} | "
        "Format-Table Status, FriendlyName, InstanceId -AutoSize"
    ])
    if rc == 0:
        lines = [l for l in out.split('\n') if l.strip() and '---' not in l]
        for l in lines[:10]:
            print(f"  {l.strip()}")

    # 检查 WinUSB 驱动详情
    print("\n  WinUSB 设备:")
    rc2, out2, _ = run_cmd([
        "powershell", "-Command",
        "Get-PnPDevice -ClassName 'WinUSB' | Format-Table Status, FriendlyName -AutoSize"
    ])
    if rc2 == 0:
        lines2 = [l for l in out2.split('\n') if 'WinUSB' in l or 'winusb' in l or 'CMSIS' in l or 'DAP' in l or 'ARM' in l]
        for l in lines2:
            print(f"  {l.strip()}")


def check_usb_serial():
    """检查 USB 串口"""
    print("\n🔌 USB 串口设备:")
    try:
        import serial
        from serial.tools import list_ports
        ports = list_ports.comports()
        for p in ports:
            if 'USB' in p.hwid or 'VID' in p.hwid:
                print(f"  {p.device:<10} {p.description:<40}")
    except ImportError:
        print("  pyserial not available")


def main():
    parser = argparse.ArgumentParser(description="pyOCD 调试器诊断工具")
    parser.add_argument("--uid", help="指定调试器 UID")
    parser.add_argument("--target", action="store_true", help="查看可用目标芯片")
    parser.add_argument("--probe", action="store_true", help="查看探针详细信息")
    parser.add_argument("--winusb", action="store_true", help="检查 WinUSB 驱动")
    parser.add_argument("--all", action="store_true", help="显示所有信息")
    parser.add_argument("--list", action="store_true", help="仅列出调试器")

    args = parser.parse_args()

    # 默认行为:列出调试器
    output = list_probes()

    if args.list:
        return

    if args.target:
        list_targets()

    if args.probe or args.all:
        probe_info(args.uid)

    if args.winusb or args.all:
        check_winusb()

    if args.all:
        check_usb_serial()

    # 如果没指定具体选项，显示简要摘要
    if not any([args.target, args.probe, args.winusb, args.all]):
        print("\n💡 提示:")
        print("   --target    查看可用目标芯片")
        print("   --probe     查看调试器详细信息")
        print("   --all       显示所有信息")


if __name__ == "__main__":
    main()
