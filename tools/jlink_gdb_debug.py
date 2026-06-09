#!/usr/bin/env python3
"""
JLink GDB 调试 — 启动 JLinkGDBServer + arm-none-eabi-gdb，支持断点。

用法:
    python jlink_gdb_debug.py                                   # 交互式 GDB
    python jlink_gdb_debug.py --elf build/Debug/daplink.elf
    python jlink_gdb_debug.py --elf build/Debug/daplink.elf --breakpoint main
    python jlink_gdb_debug.py --elf build/Debug/daplink.elf --breakpoint HardFault_Handler
    python jlink_gdb_debug.py --elf build/Debug/daplink.elf --auto  # 自动: 烧录->断点->运行->寄存器
    python jlink_gdb_debug.py --server-only                      # 只启动 GDB Server
    python jlink_gdb_debug.py --remote localhost:2331             # 连接远程 GDB Server
"""

import subprocess
import sys
import os
import signal
import tempfile
import time
import socket
import argparse

# 设置 stdout 编码
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ---------- 配置 ----------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ELF = os.path.join(PROJECT_DIR, "build", "Debug", "daplink.elf")

JLINK_DIR   = "C:/Users/miku666/AppData/Local/stm32cube/bundles/jlink-gdbserver/9.24.0+st.1/bin"
GDBSERVER   = os.path.join(JLINK_DIR, "JLinkGDBServerCL.exe")
GDB         = "arm-none-eabi-gdb"

DEFAULT_DEVICE = "STM32H750IB"
GDB_PORT    = 2331
SWO_PORT    = 2332
TELNET_PORT = 2333

MARK_OK = "[OK]"
MARK_ERR = "[ERR]"


def log(msg):
    print(msg)


# ======================================================================
#  JLinkGDBServer
# ======================================================================

class GdbServer:
    def __init__(self, device=DEFAULT_DEVICE, port=GDB_PORT, silent=False):
        self.device = device
        self.port = port
        self.silent = silent
        self.process = None

    def start(self):
        log(f"[GDB] starting JLinkGDBServer (port {self.port})...")

        cmd = [
            GDBSERVER,
            "-device", self.device,
            "-if", "SWD",
            "-speed", "4000",
            "-port", str(self.port),
            "-SWOPort", str(SWO_PORT),
            "-TelnetPort", str(TELNET_PORT),
            "-singlerun",
            "-halt",
        ]
        stdout = subprocess.DEVNULL if self.silent else None
        self.process = subprocess.Popen(cmd, stdout=stdout, stderr=stdout)

        log("  waiting for server...")
        for i in range(30):
            if self._is_port_open():
                log(f"  {MARK_OK} server ready")
                return True
            time.sleep(0.3)

        log(f"  {MARK_ERR} server timeout")
        self.stop()
        return False

    def _is_port_open(self):
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                return True
        except:
            return False

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


# ======================================================================
#  GDB commands
# ======================================================================

def make_gdb_script(elf_path, breakpoints, auto_mode):
    lines = []
    lines.append("set confirm off")
    lines.append("set pagination off")
    if elf_path:
        lines.append(f"file {elf_path}")
    lines.append(f"target remote localhost:{GDB_PORT}")
    lines.append("monitor reset")
    lines.append("monitor halt")

    if auto_mode:
        for bp in (breakpoints or []):
            lines.append(f"thbreak {bp}")
        if elf_path:
            lines.append("load")
        lines.append("monitor reset")
        lines.append("monitor halt")
        if breakpoints:
            for bp in breakpoints:
                lines.append(f"thbreak {bp}")
            lines.append("continue")
        lines.append("info registers")
        lines.append("bt")
    else:
        for bp in (breakpoints or []):
            lines.append(f"thbreak {bp}")
        lines.append('echo \\n=== GDB ready. type "continue" to run ===\\n')

    return "\n".join(lines)


def run_gdb(elf_path, breakpoints=None, auto_mode=False):
    script = make_gdb_script(elf_path, breakpoints, auto_mode)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.gdb', delete=False,
                                     encoding='utf-8') as f:
        f.write(script)
        sf = f.name

    try:
        log(f"[GDB] launching arm-none-eabi-gdb...")
        log("\nGDB quick reference:")
        log("  continue|c   run")
        log("  step|s       step into")
        log("  next|n       step over")
        log("  finish       run to return")
        log("  info reg     show registers")
        log("  bt           backtrace")
        log("  list         source code")
        log("  print x      print variable")
        log("  break func   set breakpoint")
        log("  delete       delete breakpoints")
        log("  quit|q       exit\n")

        cmd = [GDB, "-x", sf]
        if elf_path:
            cmd.append(elf_path)
        subprocess.run(cmd)
    except FileNotFoundError:
        log(f"{MARK_ERR} gdb not found: {GDB}")
        log("  install ARM GCC toolchain and ensure arm-none-eabi-gdb is in PATH")
    finally:
        try:
            os.remove(sf)
        except OSError:
            pass


def connect_remote(elf_path, host="localhost", port=GDB_PORT):
    script = f"set confirm off\nset pagination off\n"
    if elf_path:
        script += f"file {elf_path}\n"
    script += f"target remote {host}:{port}\n"
    script += "monitor halt\n"
    script += 'echo connected.\n'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.gdb', delete=False,
                                     encoding='utf-8') as f:
        f.write(script)
        sf = f.name

    try:
        log(f"[GDB] connecting to {host}:{port}...")
        subprocess.run([GDB, "-x", sf])
    except FileNotFoundError:
        log(f"{MARK_ERR} gdb not found: {GDB}")
    finally:
        try:
            os.remove(sf)
        except OSError:
            pass


# ======================================================================
#  Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="JLink GDB Debug Tool")
    parser.add_argument("--elf", default=DEFAULT_ELF)
    parser.add_argument("-b", "--breakpoint", dest="breakpoints", action="append",
                        help="breakpoint (can be specified multiple times)")
    parser.add_argument("--auto", action="store_true",
                        help="auto mode: flash -> breakpoint -> run -> reg dump")
    parser.add_argument("--server-only", action="store_true",
                        help="start GDBServer only")
    parser.add_argument("-r", "--remote", metavar="HOST:PORT",
                        help="connect to remote GDBServer")
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--port", type=int, default=GDB_PORT,
                        help="GDBServer port (default: 2331)")

    args = parser.parse_args()

    if args.remote:
        parts = args.remote.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else GDB_PORT
        connect_remote(args.elf, host, port)
        return

    if args.server_only:
        srv = GdbServer(args.device, args.port)
        try:
            if srv.start():
                log(f"  GDBServer running: localhost:{args.port}")
                log("  Ctrl+C to stop")
                while True:
                    time.sleep(1)
            else:
                sys.exit(1)
        except KeyboardInterrupt:
            pass
        finally:
            srv.stop()
        return

    srv = GdbServer(args.device, args.port)
    try:
        if not srv.start():
            sys.exit(1)
        run_gdb(args.elf, args.breakpoints, args.auto)
    finally:
        srv.stop()


if __name__ == "__main__":
    main()
