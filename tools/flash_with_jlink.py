#!/usr/bin/env python3
"""
JLink 烧录脚本 — 使用 JLink 烧录 STM32H750XBH6

用法:
    python flash_with_jlink.py                          # 编译 + 烧录
    python flash_with_jlink.py --no-build               # 只烧录不编译
    python flash_with_jlink.py --no-flash               # 只验证不烧录
    python flash_with_jlink.py --device STM32H750IB     # 指定设备名
    python flash_with_jlink.py --elf path/to/firmware.elf

环境变量:
    PYTHONIOENCODING=utf-8  (推荐设置，解决 Win 终端编码问题)
"""

import subprocess
import sys
import os
import tempfile

# 设置 stdout 编码 (Windows GBK 兼容)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ---------- 配置 ----------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELF_FILE    = os.path.join(PROJECT_DIR, "build", "Debug", "daplink.elf")
BIN_FILE    = os.path.join(PROJECT_DIR, "build", "Debug", "daplink.bin")

# JLink 路径
JLINK_DIR   = "C:/Users/miku666/AppData/Local/stm32cube/bundles/jlink-gdbserver/9.24.0+st.1/bin"
JLINK_EXE   = os.path.join(JLINK_DIR, "JLink.exe")

# JLink 设备型号
DEFAULT_DEVICE = "STM32H750IB"

# 标记符号 (GBK 兼容)
OK    = "[OK]"
ERR   = "[ERR]"
WARN  = "[WARN]"
INFO  = " .."
ARROW = " ->"


def log(msg):
    print(msg)


def run_cmd(cmd, timeout=60, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"cmd not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def check_tools():
    log("\n检查工具...")
    ok = True

    if not os.path.exists(JLINK_EXE):
        log(f"  {ERR} JLink.exe not found: {JLINK_EXE}")
        ok = False
    else:
        rc, out, _ = run_cmd([JLINK_EXE], timeout=10)
        for line in out.split('\n'):
            if 'J-Link Commander' in line:
                log(f"  {OK} {line.strip()}")
                break

    for tool, name in [("arm-none-eabi-objcopy", "ARM GCC"),
                       ("cmake", "CMake"),
                       ("ninja", "Ninja")]:
        rc, _, _ = run_cmd([tool, "--version"], timeout=5)
        if rc != 0:
            log(f"  {ERR} {name} not found")
            ok = False

    if ok:
        log(f"  {OK} checks passed")
    return ok


def build_firmware():
    log("\n编译固件...")
    project_build = os.path.join(PROJECT_DIR, "build", "Debug")
    ninja_file = os.path.join(project_build, "build.ninja")

    if not os.path.exists(ninja_file):
        log("  CMake configure...")
        rc, _, err = run_cmd(["cmake", "--preset", "Debug"], timeout=60, cwd=PROJECT_DIR)
        if rc != 0:
            log(f"  {ERR} CMake failed:\n{err}")
            return False

    rc, out, err = run_cmd(["cmake", "--build", "--preset", "Debug"],
                           timeout=120, cwd=PROJECT_DIR)
    if rc != 0:
        log(f"  {ERR} build failed:")
        for line in (out + err).split('\n'):
            if 'error:' in line.lower():
                log(f"    {line.strip()}")
        return False

    if not os.path.exists(ELF_FILE):
        log(f"  {ERR} {ELF_FILE} not found")
        return False

    rc2, _, _ = run_cmd(["arm-none-eabi-objcopy", "-O", "binary", ELF_FILE, BIN_FILE])
    if rc2 != 0 or not os.path.exists(BIN_FILE):
        log(f"  {ERR} bin generation failed")
        return False

    log(f"  {OK} build OK ({os.path.getsize(ELF_FILE)//1024} KB)")
    return True


def flash_via_jlink(elf_path, device_name):
    if not os.path.exists(elf_path):
        log(f"{ERR} ELF not found: {elf_path}")
        return False

    log(f"\n烧录 {device_name} ...")
    log(f"  file: {os.path.basename(elf_path)}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jlink', delete=False,
                                     encoding='utf-8') as f:
        f.write("r\n")
        f.write(f"loadfile {elf_path}\n")
        f.write("r\n")
        f.write("g\n")
        f.write("exit\n")
        cmd_file = f.name

    try:
        cmd = [
            JLINK_EXE,
            "-device", device_name,
            "-if", "SWD",
            "-speed", "4000",
            "-autoconnect", "1",
            "-CommanderScript", cmd_file
        ]

        rc, out, err = run_cmd(cmd, timeout=120)

        # print key lines
        for line in out.split('\n'):
            if any(k in line for k in ['Download', 'Erase', 'Program',
                                       'Flash', 'error', 'Error',
                                       'FAILED', 'O.K.', 'success',
                                       'unknown', 'unsupported']):
                log(f"  {line.strip()}")

        if "O.K." in out and "error" not in out.lower():
            log(f"  {OK} flash OK")
            return True

        # retry with .bin if ELF not recognized
        if "unknown" in out.lower() or "unsupported" in out.lower():
            bin_path = elf_path.replace('.elf', '.bin')
            if os.path.exists(bin_path):
                log(f"  {WARN} ELF not recognized, retry with .bin...")
                with open(cmd_file, 'w') as f:
                    f.write("r\n")
                    f.write(f"loadfile {bin_path} 0x08000000\n")
                    f.write("r\n")
                    f.write("g\n")
                    f.write("exit\n")

                rc2, out2, err2 = run_cmd(cmd, timeout=120)
                for line in out2.split('\n'):
                    if any(k in line for k in ['Download', 'Erase', 'Program',
                                               'Flash', 'error', 'Error']):
                        log(f"  {line.strip()}")
                if "O.K." in out2 or rc2 == 0:
                    log(f"  {OK} flash OK (via .bin)")
                    return True

        log(f"  {ERR} flash failed")
        return False

    finally:
        try:
            os.remove(cmd_file)
        except OSError:
            pass


def verify_jlink(device_name):
    log("\n验证烧录...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jlink', delete=False,
                                     encoding='utf-8') as f:
        f.write("mem 0x08000000 16\n")
        f.write("exit\n")
        cmd_file = f.name

    try:
        cmd = [
            JLINK_EXE,
            "-device", device_name,
            "-if", "SWD",
            "-speed", "4000",
            "-autoconnect", "1",
            "-CommanderScript", cmd_file
        ]

        rc, out, err = run_cmd(cmd, timeout=30)

        for line in out.split('\n'):
            if line.startswith('08000000'):
                # JLink outputs bytes: "08000000 = 00 00 02 20 A5 B1 00 08 ..."
                vals = line.split('=')[1].strip().split()
                # Little-endian: first 4 bytes = SP, next 4 bytes = Reset Vector
                sp = int(vals[3] + vals[2] + vals[1] + vals[0], 16)
                pc = int(vals[7] + vals[6] + vals[5] + vals[4], 16)
                log(f"  向量表: SP=0x{sp:08X}, PC=0x{pc:08X}")
                if 0x20000000 <= sp <= 0x30000000 and 0x08000000 <= pc <= 0x08100000:
                    log(f"  {OK} flash content valid")
                else:
                    log(f"  {WARN} vector table looks wrong")
                break

        return True
    finally:
        try:
            os.remove(cmd_file)
        except OSError:
            pass


def main():
    log("=" * 55)
    log("  JLink Flash Tool -- STM32H750XBH6")
    log("=" * 55)

    no_build = "--no-build" in sys.argv
    no_flash = "--no-flash" in sys.argv
    device = DEFAULT_DEVICE
    elf_path = ELF_FILE

    for arg in sys.argv:
        if arg.startswith("--device="):
            device = arg.split("=", 1)[1]
        if arg.startswith("--elf="):
            elf_path = arg.split("=", 1)[1]

    if not check_tools():
        sys.exit(1)

    if not no_build:
        if not build_firmware():
            sys.exit(1)

    if not no_flash:
        if not flash_via_jlink(elf_path, device):
            sys.exit(1)
    else:
        log("\nskip flash")

    verify_jlink(device)

    if os.path.exists(ELF_FILE) and not no_flash:
        log("\n下一步:")
        log("  serial:  python tools/jlink_serial_monitor.py")
        log("  gdb:     python tools/jlink_gdb_debug.py --elf build/Debug/daplink.elf")
        log("  rtt:     python tools/jlink_serial_monitor.py --rtt")

    log("\n" + "=" * 55)
    log("  Done!")
    log("=" * 55)


if __name__ == "__main__":
    main()
