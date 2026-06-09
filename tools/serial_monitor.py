#!/usr/bin/env python3
"""
DAPLink 串口监视器 — 通过 DAPLink 虚拟串口读取目标板调试输出。

默认连接 COM33 (外购 DAPLink 的 VCP 端口)，波特率 115200。

用法:
    python serial_monitor.py                  # 默认 COM33 115200
    python serial_monitor.py --port COM33     # 指定串口
    python serial_monitor.py --baud 921600    # 指定波特率
    python serial_monitor.py --save log.txt   # 保存到文件
    python serial_monitor.py --list           # 列出可用串口
"""

import sys
import time
import argparse
import signal
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("❌ 需要 pyserial: pip install pyserial")
    sys.exit(1)


# 默认配置
DEFAULT_PORT = "COM13"
DEFAULT_BAUD = 115200


def list_serial_ports():
    """列出可用串口"""
    ports = list_ports.comports()
    if not ports:
        print("未找到可用串口")
        return

    print(f"{'端口':<12} {'描述':<40} {'硬件ID':<50}")
    print("-" * 102)
    for p in sorted(ports, key=lambda x: x.device):
        desc = p.description[:38] if p.description else "(无描述)"
        hwid = p.hwid[:48] if p.hwid else "(无)"
        print(f"{p.device:<12} {desc:<40} {hwid:<50}")


def serial_monitor(port, baudrate, save_path=None, timeout=0.01):
    """
    串口监视器主循环
    """
    print(f"🔌 连接 {port} @ {baudrate} baud...")
    print("   按 Ctrl+C 退出\n")

    out_file = None
    if save_path:
        try:
            out_file = open(save_path, "a", encoding="utf-8")
            print(f"   📝 日志保存到: {save_path}")
        except IOError as e:
            print(f"   ⚠️  无法打开日志文件: {e}")

    ser = None
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )
    except serial.SerialException as e:
        print(f"❌ 无法打开串口 {port}: {e}")
        print("\n可能的原因:")
        print("  - 串口被其他程序占用")
        print("  - 设备未连接")
        print("  - 驱动问题 (检查设备管理器)")
        if out_file:
            out_file.close()
        sys.exit(1)

    # 刷新输入缓冲区
    ser.reset_input_buffer()

    # 行缓冲区 (用于带时间戳打印)
    line_buf = bytearray()
    last_receive_time = time.time()

    try:
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                now = datetime.now()
                timestamp = now.strftime("%H:%M:%S.%f")[:-3]
                last_receive_time = time.time()

                # 写入文件 (原始数据)
                if out_file:
                    out_file.write(data.decode("utf-8", errors="replace"))
                    out_file.flush()

                # 按行打印 (带时间戳)
                for byte in data:
                    if byte == 0x0A:  # LF
                        line_buf.append(byte)
                        line = line_buf.decode("utf-8", errors="replace").rstrip("\r\n")
                        if line:
                            print(f"[{timestamp}] {line}")
                        line_buf = bytearray()
                    elif byte == 0x0D:  # CR — 忽略, 等待 LF
                        pass
                    else:
                        line_buf.append(byte)

            else:
                # 空闲时短暂休眠以减少 CPU 占用
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n👋 用户中断")

    finally:
        # 输出剩余数据
        if line_buf:
            line = line_buf.decode("utf-8", errors="replace")
            if line.strip():
                now = datetime.now()
                ts = now.strftime("%H:%M:%S.%f")[:-3]
                print(f"[{ts}] {line}")

        if ser and ser.is_open:
            ser.close()
            print(f"🔌 {port} 已断开")

        if out_file:
            # 记录结束时间
            out_file.write(f"\n--- 会话结束于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            out_file.close()
            print(f"📝 日志已保存到: {save_path}")


def main():
    parser = argparse.ArgumentParser(
        description="DAPLink 串口监视器 — 读取目标板调试输出",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                        # 默认 COM33 115200
  %(prog)s --port COM3 --baud 9600
  %(prog)s -p COM33 -b 921600 -s debug.log
  %(prog)s --list                  # 列出可用串口
        """
    )
    parser.add_argument("-p", "--port", default=DEFAULT_PORT,
                        help=f"串口号 (默认: {DEFAULT_PORT})")
    parser.add_argument("-b", "--baud", type=int, default=DEFAULT_BAUD,
                        help=f"波特率 (默认: {DEFAULT_BAUD})")
    parser.add_argument("-s", "--save", help="保存日志到文件")
    parser.add_argument("-l", "--list", action="store_true",
                        help="列出可用串口并退出")
    parser.add_argument("--raw", action="store_true",
                        help="原始模式 (不添加时间戳)")

    args = parser.parse_args()

    # 列出串口
    if args.list:
        list_serial_ports()
        return

    print("=" * 55)
    print("  DAPLink 串口监视器")
    print("=" * 55)
    print(f"  端口:   {args.port}")
    print(f"  波特率: {args.baud}")
    print(f"  保存:   {args.save or '(不保存)'}")
    print("=" * 55)

    serial_monitor(args.port, args.baud, args.save)


if __name__ == "__main__":
    main()
