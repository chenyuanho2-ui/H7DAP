#!/usr/bin/env python3
"""
pyOCD 调试脚本 — 支持断点、单步、寄存器查看、内存读写。

适用于:
  - 通过外购 DAPLink 调试 STM32H750
  - 通过 H750 DAPLink 调试目标板 (如 STM32F103C8T6)

用法:
    # 交互式调试 (连接到目标，进入 pyocd commander)
    python pyocd_debug.py -t stm32h750xx

    # 自动运行: 烧录 → 设置断点 → 运行 → 暂停 → 查看寄存器
    python pyocd_debug.py -t stm32h750xx --elf ../build/Debug/daplink.elf --breakpoint main

    # 连接到指定 DAPLink
    python pyocd_debug.py -t stm32f103c8 -u <UID>

    # 读取指定地址的内存
    python pyocd_debug.py -t stm32h750xx --read-mem 0x08000000 64

    # 读取寄存器
    python pyocd_debug.py -t stm32h750xx --regs
"""

import sys
import os
import subprocess
import argparse
import time
import tempfile


def run_cmd(cmd, timeout=60):
    """运行命令"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"命令未找到: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"


def interactive_commander(target, uid=None):
    """进入 pyocd commander 交互模式"""
    cmd = ["pyocd", "commander", "-t", target]
    if uid:
        cmd.extend(["-u", uid])

    print(f"🚀 启动 pyocd commander (目标: {target})...")
    print(f"   命令: {' '.join(cmd)}")
    print()
    print("常用命令:")
    print("  help            显示帮助")
    print("  info            显示目标信息")
    print("  reg             显示寄存器")
    print("  rd <reg>        读取寄存器 (如 rd r0, rd pc)")
    print("  wt <reg> <val>  写入寄存器")
    print("  step            单步执行")
    print("  go              继续运行")
    print("  halt            暂停")
    print("  hbreak <loc>    设置硬件断点")
    print("  rb <loc>        移除断点")
    print("  md8 <addr> <n>  以字节显示内存")
    print("  mdh <addr> <n>  以半字显示内存")
    print("  mdw <addr> <n>  以字显示内存")
    print("  mw8 <addr> <v>  写入字节到内存")
    print("  reset           复位目标")
    print("  status          目标状态")
    print("  q               退出")
    print()

    # 直接用 subprocess 启动，不通过 run_cmd 包装
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError as e:
        print(f"❌ 命令执行失败: {e}")
        print("请确认 pyocd 已安装: pip install pyocd")


def flash_and_debug(target, elf_path, breakpoint_loc=None, uid=None):
    """烧录并调试"""
    if not os.path.exists(elf_path):
        print(f"❌ 未找到 ELF 文件: {elf_path}")
        return False

    print(f"🎯 目标芯片: {target}")
    print(f"📦 ELF 文件: {elf_path}")

    # 1. 烧录
    flash_cmd = ["pyocd", "flash", "-t", target, "-e", "chip"]
    if uid:
        flash_cmd.extend(["-u", uid])
    flash_cmd.append(elf_path)

    print(f"\n🔥 烧录固件...")
    rc, out, err = run_cmd(flash_cmd, timeout=120)
    if rc != 0:
        print(f"❌ 烧录失败:\n{err}")
        return False
    print(f"✅ 烧录成功")

    # 2. 启动 commander 并执行命令
    cmds = []
    if breakpoint_loc:
        cmds.append(f"hbreak {breakpoint_loc}")
    cmds.append("go")
    cmds.append("sleep 1")
    cmds.append("halt")
    cmds.append("reg")
    cmds.append("info")

    # 写入命令文件
    cmd_file = os.path.join(tempfile.gettempdir(), "pyocd_cmds.txt")
    with open(cmd_file, "w") as f:
        for c in cmds:
            f.write(c + "\n")

    debug_cmd = ["pyocd", "commander", "-t", target]
    if uid:
        debug_cmd.extend(["-u", uid])
    debug_cmd.extend(["-x", cmd_file])

    print(f"\n🔍 运行调试命令...")
    print(f"   断点: {breakpoint_loc or '(无)'}")
    rc2, out2, err2 = run_cmd(debug_cmd, timeout=30)
    if rc2 == 0:
        print(f"📊 调试输出:\n{out2}")
    else:
        print(f"⚠️  调试命令输出:\n{out2}\n{err2}")

    # 清理
    try:
        os.remove(cmd_file)
    except OSError:
        pass

    return True


def read_memory(target, addr, count=16, uid=None):
    """读取目标内存"""
    cmd_file = os.path.join(tempfile.gettempdir(), "pyocd_mem.txt")
    with open(cmd_file, "w") as f:
        f.write(f"mdw {hex(addr)} {count}\n")

    cmd = ["pyocd", "commander", "-t", target]
    if uid:
        cmd.extend(["-u", uid])
    cmd.extend(["-x", cmd_file])

    rc, out, err = run_cmd(cmd, timeout=15)
    if rc == 0:
        print(f"📊 内存 (0x{addr:08X}):\n{out}")
    else:
        print(f"❌ 读取内存失败:\n{err}")

    try:
        os.remove(cmd_file)
    except OSError:
        pass


def read_registers(target, uid=None):
    """读取目标寄存器"""
    cmd_file = os.path.join(tempfile.gettempdir(), "pyocd_regs.txt")
    with open(cmd_file, "w") as f:
        f.write("halt\nreg\ninfo\n")

    cmd = ["pyocd", "commander", "-t", target]
    if uid:
        cmd.extend(["-u", uid])
    cmd.extend(["-x", cmd_file])

    rc, out, err = run_cmd(cmd, timeout=15)
    if rc == 0:
        print(f"📊 寄存器:\n{out}")
    else:
        print(f"❌ 读取寄存器失败:\n{err}")

    try:
        os.remove(cmd_file)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="pyOCD 调试脚本 — 烧录、断点、寄存器读取",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-t", "--target", default="stm32h750xx",
                        help="目标芯片型号 (默认: stm32h750xx)")
    parser.add_argument("-u", "--uid", help="DAPLink UID (留空自动选择)")
    parser.add_argument("--elf", help="ELF 文件路径 (配合 --breakpoint 使用)")
    parser.add_argument("-b", "--breakpoint", dest="breakpoint",
                        help="设置断点 (如 main, HardFault_Handler, 0x08001000)")
    parser.add_argument("--read-mem", nargs=2, metavar=("ADDR", "COUNT"),
                        help="读取内存: --read-mem 0x08000000 64")
    parser.add_argument("--regs", action="store_true", help="读取寄存器")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="交互模式 (进入 pyocd commander)")

    args = parser.parse_args()

    # 读取内存
    if args.read_mem:
        addr = int(args.read_mem[0], 0)  # 支持 0x 前缀
        count = int(args.read_mem[1])
        read_memory(args.target, addr, count, args.uid)
        return

    # 读取寄存器
    if args.regs:
        read_registers(args.target, args.uid)
        return

    # 交互模式
    if args.interactive:
        interactive_commander(args.target, args.uid)
        return

    # 烧录 + 调试 (需要 ELF)
    if args.elf:
        flash_and_debug(args.target, args.elf, args.breakpoint, args.uid)
    else:
        # 默认: 交互模式
        print("💡 未指定操作，进入交互模式")
        interactive_commander(args.target, args.uid)


if __name__ == "__main__":
    main()
