#!/usr/bin/env python3
"""
JLink 串口监视器 — 通过 JLink CDC UART (COM9) 读取目标板调试输出。

用法:
    python jlink_serial_monitor.py              # COM9 115200
    python jlink_serial_monitor.py --port COM9
    python jlink_serial_monitor.py --baud 921600 --save log.txt
    python jlink_serial_monitor.py --list       # 列出串口
    python jlink_serial_monitor.py --rtt        # 启动 JLinkRTTViewer
"""

import sys
import os
import time
import argparse
import subprocess
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("[ERR] need pyserial: pip install pyserial")
    sys.exit(1)

DEFAULT_PORT = "COM9"
DEFAULT_BAUD = 115200


def list_serial_ports():
    ports = list_ports.comports()
    if not ports:
        print("No serial ports found")
        return
    print(f"{'Port':<12} {'Description':<45} {'HWID':<50}")
    print("-" * 107)
    for p in sorted(ports, key=lambda x: x.device):
        print(f"{p.device:<12} {p.description[:43]:<45} {p.hwid[:48]:<50}")


def serial_monitor(port, baudrate, save_path=None):
    print(f"[CONN] {port} @ {baudrate} baud")
    print("       Ctrl+C to exit")

    out_file = None
    if save_path:
        try:
            out_file = open(save_path, "a", encoding="utf-8")
            print(f"[SAVE] {save_path}")
        except IOError as e:
            print(f"[WARN] {e}")

    try:
        ser = serial.Serial(port, baudrate,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=0.01)
    except serial.SerialException as e:
        print(f"[ERR] {e}")
        print("  check: port in use / device disconnected / driver issue")
        if out_file:
            out_file.close()
        sys.exit(1)

    ser.reset_input_buffer()
    line_buf = bytearray()

    try:
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                if out_file:
                    out_file.write(data.decode("utf-8", errors="replace"))
                    out_file.flush()

                for byte in data:
                    if byte == 0x0A:  # LF
                        line_buf.append(byte)
                        line = line_buf.decode("utf-8", errors="replace").rstrip("\r\n")
                        if line:
                            print(f"[{ts}] {line}")
                        line_buf = bytearray()
                    elif byte == 0x0D:
                        pass
                    else:
                        line_buf.append(byte)
            else:
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[EXIT] user interrupt")

    finally:
        if line_buf:
            line = line_buf.decode("utf-8", errors="replace")
            if line.strip():
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {line}")
        if ser and ser.is_open:
            ser.close()
        if out_file:
            out_file.write(f"\n--- end {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            out_file.close()


def rtt_viewer():
    """启动 JLinkRTTViewer"""
    jlink_bin = "C:/Users/miku666/AppData/Local/stm32cube/bundles/jlink-gdbserver/9.24.0+st.1/bin"
    rtt_exe = os.path.join(jlink_bin, "JLinkRTTViewer.exe")

    if not os.path.exists(rtt_exe):
        print(f"[ERR] JLinkRTTViewer not found: {rtt_exe}")
        return

    print(f"[RTT] starting JLinkRTTViewer...")
    cmd = [rtt_exe, "-device", "STM32H750IB", "-if", "SWD",
           "-speed", "4000", "-RTTChannel", "0"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="JLink Serial Monitor (COM9)")
    parser.add_argument("-p", "--port", default=DEFAULT_PORT)
    parser.add_argument("-b", "--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("-s", "--save", help="save log to file")
    parser.add_argument("--list", action="store_true", help="list ports")
    parser.add_argument("--rtt", action="store_true", help="use JLinkRTTViewer")

    args = parser.parse_args()

    if args.list:
        list_serial_ports()
        return

    if args.rtt:
        rtt_viewer()
        return

    print("=" * 55)
    print("  JLink Serial Monitor (COM9)")
    print("=" * 55)
    serial_monitor(args.port, args.baud, args.save)


if __name__ == "__main__":
    main()
