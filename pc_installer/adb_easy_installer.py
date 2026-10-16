# -*- coding: utf-8 -*-
"""ADB Easy Installer: install and manage Android apps from Windows."""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "ADB Easy Installer"
APP_VERSION = "1.0.0"


def resource_path(relative_path):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def adb_path():
    bundled = resource_path(os.path.join("platform-tools", "adb.exe"))
    return bundled if os.path.isfile(bundled) else "adb"


def adb(args, timeout=60):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        p = subprocess.run(
            [adb_path(), *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=flags, check=False
        )
        return p.returncode, (p.stdout or "").strip()
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        raise RuntimeError(f"ADB hết thời gian chờ ({timeout} giây).\n{out}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("Không tìm thấy adb.exe. Hãy dùng bản EXE đã phát hành hoặc đặt thư mục platform-tools cạnh chương trình.") from exc


def parse_devices(output):
    devices = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        model = next((p.split(":", 1)[1].replace("_", " ") for p in parts[2:] if p.startswith("model:")), "")
        if state == "device":
            label = f"{model or 'Thiết bị Android'} | {serial} [đã kết nối]"
        elif state == "unauthorized":
            label = f"{serial} [chưa cấp quyền USB]"
        else:
            label = f"{serial} [{state}]"
        devices.append({"serial": serial, "state": state, "model": model, "label": label})
    return devices


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("920x700")
        self.root.minsize(820, 620)
        self.root.configure(bg="#101827")
        self.events = queue.Queue()
        self.busy = False
        self.devices = []
        self.device_map = {}
        self.apk_var = tk.StringVar()
        self.device_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Đang khởi động...")
        self.package_count = tk.StringVar(value="Chưa tải danh sách")

        self.style()
        self.ui()
        self.root.after(100, self.poll)
        self.root.after(500, self.refresh_devices)

    def style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", font=("Segoe UI", 10))
        s.configure("TFrame", background="#101827")
        s.configure("Panel.TFrame", background="#19263A")
        s.configure("TLabel", background="#101827", foreground="#E7EDF7")
        s.configure("Muted.TLabel", background="#101827", foreground="#A8B8CE")
        s.configure("Panel.TLabel", background="#19263A", foreground="#E7EDF7")
        s.configure("Title.TLabel", background="#101827", foreground="#FFFFFF", font=("Segoe UI", 19, "bold"))
        s.configure("TButton", padding=(11, 8), background="#2B3D59", foreground="#FFFFFF", borderwidth=0)
        s.map("TButton", background=[("active", "#3A5478"), ("disabled", "#273246")])
        s.configure("Accent.TButton", padding=(14, 10), background="#2673E8", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", "#4188F5"), ("disabled", "#354A69")])
        s.configure("TEntry", padding=8, fieldbackground="#0F1725", foreground="#E7EDF7")
        s.configure("TCombobox", padding=7, fieldbackground="#0F1725", foreground="#E7EDF7")
        s.map("TCombobox", fieldbackground=[("readonly", "#0F1725")], foreground=[("readonly", "#E7EDF7")])
        s.configure("TNotebook", background="#101827", borderwidth=0)
        s.configure("TNotebook.Tab", padding=(15, 9), background="#1B2A40", foreground="#E7EDF7")
        s.map("TNotebook.Tab", background=[("selected", "#2673E8")], foreground=[("selected", "#FFFFFF")])
        s.configure("Treeview", background="#0F1725", fieldbackground="#0F1725", foreground="#E7EDF7", rowheight=27)
        s.configure("Treeview.Heading", background="#2B3D59", foreground="#FFFFFF")

    def ui(self):
        outer = ttk.Frame(self.root, padding=17)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="ADB EASY INSTALLER", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Cài APK từ PC vào Android qua cáp USB — không cần mở APK trên điện thoại.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 14))

        panel = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        panel.pack(fill="x", pady=(0, 12))
        ttk.Label(panel, text="THIẾT BỊ", style="Panel.TLabel").grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.device_combo = ttk.Combobox(panel, textvariable=self.device_var, state="readonly", width=49)
        self.device_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.refresh_btn = ttk.Button(panel, text="↻ Kiểm tra kết nối", command=self.refresh_devices)
        self.refresh_btn.grid(row=0, column=2)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, textvariable=self.status_var, style="Panel.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        tabs = ttk.Notebook(outer)
        tabs.pack(fill="both", expand=True)
        install_tab = ttk.Frame(tabs, padding=17)
        apps_tab = ttk.Frame(tabs, padding=14)
        help_tab = ttk.Frame(tabs, padding=17)
        tabs.add(install_tab, text="  Cài APK  ")
        tabs.add(apps_tab, text="  Quản lý ứng dụng  ")
        tabs.add(help_tab, text="  Hướng dẫn  ")

        ttk.Label(install_tab, text="Chọn APK trên máy tính", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(2, 7))
        ttk.Label(install_tab, text="Chương trình sẽ gửi file qua ADB và cài lên thiết bị đã chọn.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        row = ttk.Frame(install_tab)
        row.pack(fill="x", pady=(0, 13))
        ttk.Entry(row, textvariable=self.apk_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(row, text="Chọn APK…", command=self.choose_apk).pack(side="right")
        self.install_btn = ttk.Button(install_tab, text="⬇  CÀI APK VÀO ĐIỆN THOẠI",
                                      style="Accent.TButton", command=self.install)
        self.install_btn.pack(anchor="w")
        ttk.Label(install_tab,
                  text="Cài cập nhật sẽ giữ dữ liệu ứng dụng nếu Android cho phép. Nếu có xung đột chữ ký, chương trình sẽ báo lỗi và không tự gỡ bản cũ.",
                  style="Muted.TLabel", wraplength=800, justify="left").pack(anchor="w", pady=(15, 0))

        top = ttk.Frame(apps_tab)
        top.pack(fill="x", pady=(0, 9))
        ttk.Label(top, text="Ứng dụng của người dùng", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.apps_refresh_btn = ttk.Button(top, text="↻ Tải danh sách", command=self.refresh_packages)
        self.apps_refresh_btn.pack(side="right")
        ttk.Label(apps_tab, textvariable=self.package_count, style="Muted.TLabel").pack(anchor="w", pady=(0, 7))
        body = ttk.Frame(apps_tab)
        body.pack(fill="both", expand=True)
        self.package_tree = ttk.Treeview(body, columns=("package",), show="headings", selectmode="browse")
        self.package_tree.heading("package", text="Tên gói ứng dụng")
        self.package_tree.column("package", width=700, anchor="w")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.package_tree.yview)
        self.package_tree.configure(yscrollcommand=scroll.set)
        self.package_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ttk.Button(apps_tab, text="Gỡ ứng dụng đã chọn", command=self.uninstall).pack(anchor="w", pady=(10, 0))
        ttk.Label(apps_tab, text="Gỡ ứng dụng có thể xóa dữ liệu. Chương trình sẽ hỏi xác nhận trước khi gỡ.",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

        help_content = (
            "KẾT NỐI\n"
            "1. Dùng cáp USB có truyền dữ liệu và mở khóa điện thoại.\n"
            "2. Bật Tùy chọn nhà phát triển → Gỡ lỗi USB.\n"
            "3. Khi điện thoại hỏi cấp quyền gỡ lỗi USB, bấm Cho phép.\n"
            "4. Bấm Kiểm tra kết nối ở phía trên.\n\n"
            "NẾU KHÔNG NHẬN ĐIỆN THOẠI\n"
            "• Chưa cấp quyền USB: mở khóa điện thoại và chấp nhận lời nhắc trên màn hình.\n"
            "• Offline: rút cáp, cắm lại rồi kiểm tra kết nối.\n"
            "• Không thấy thiết bị: thử cáp/cổng USB khác; có thể cần driver USB của hãng trên Windows.\n"
            "• Cài đặt thất bại: đọc dòng Failure trong Nhật ký. APK có thể không tương thích hoặc Android đang chặn cài đặt.\n\n"
            "Công cụ dùng ADB thông thường, không tự bật gỡ lỗi USB và không vượt khóa quản trị hay chính sách bảo mật."
        )
        ttk.Label(help_tab, text=help_content, style="Muted.TLabel", justify="left",
                  wraplength=800).pack(anchor="nw", fill="x")

        log_frame = ttk.Frame(outer, style="Panel.TFrame", padding=9)
        log_frame.pack(fill="both", pady=(12, 0))
        head = ttk.Frame(log_frame, style="Panel.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text="NHẬT KÝ", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(head, text="Xóa", command=self.clear_log).pack(side="right")
        self.log_box = tk.Text(log_frame, height=6, wrap="word", bg="#0B1220", fg="#DCE7F8",
                               insertbackground="#FFFFFF", relief="flat", font=("Consolas", 9),
                               padx=7, pady=6, state="disabled")
        self.log_box.pack(fill="both", pady=(7, 0))
        self.log("Sẵn sàng. Cắm điện thoại đã bật Gỡ lỗi USB rồi bấm Kiểm tra kết nối.")

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", str(text).rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.log(value)
                elif kind == "devices":
                    self.devices = value
                    self.device_map = {d["label"]: d for d in value}
                    labels = [d["label"] for d in value]
                    self.device_combo["values"] = labels
                    active = next((d for d in value if d["state"] == "device"), None)
                    if active:
                        self.device_var.set(active["label"])
                        self.status_var.set("Đã kết nối: " + (active["model"] or active["serial"]))
                    elif labels:
                        self.device_var.set(labels[0])
                        self.status_var.set("Thiết bị cần xử lý quyền/trạng thái. Xem Hướng dẫn.")
                    else:
                        self.device_var.set("")
                        self.status_var.set("Chưa thấy điện thoại. Kiểm tra cáp và Gỡ lỗi USB.")
                elif kind == "packages":
                    for iid in self.package_tree.get_children():
                        self.package_tree.delete(iid)
                    for package in value:
                        self.package_tree.insert("", "end", values=(package,))
                    self.package_count.set(f"{len(value)} ứng dụng")
                elif kind == "error":
                    self.log("LỖI: " + str(value))
                    messagebox.showerror("Không hoàn tất", str(value), parent=self.root)
                elif kind == "done":
                    self.set_busy(False)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def set_busy(self, value):
        self.busy = bool(value)
        state = "disabled" if self.busy else "normal"
        self.refresh_btn.configure(state=state)
        self.install_btn.configure(state=state)
        self.apps_refresh_btn.configure(state=state)

    def task(self, label, fn):
        if self.busy:
            return
        self.set_busy(True)
        self.status_var.set(label)

        def worker():
            try:
                fn()
            except Exception as exc:
                self.events.put(("error", str(exc)))
            finally:
                self.events.put(("done", None))
        threading.Thread(target=worker, daemon=True).start()

    def chosen_device(self):
        d = self.device_map.get(self.device_var.get())
        if not d:
            messagebox.showwarning("Chưa có điện thoại", "Hãy kết nối điện thoại rồi bấm Kiểm tra kết nối.", parent=self.root)
            return None
        if d["state"] != "device":
            tip = "Mở khóa điện thoại và bấm Cho phép trên yêu cầu Gỡ lỗi USB." if d["state"] == "unauthorized" else "Rút cáp, cắm lại và thử lại."
            messagebox.showwarning("Thiết bị chưa sẵn sàng", f"Trạng thái: {d['state']}\n{tip}", parent=self.root)
            return None
        return d

    def refresh_devices(self):
        if self.busy:
            return
        def work():
            self.events.put(("log", "\n--- Kiểm tra ADB ---"))
            _, startup = adb(["start-server"], timeout=30)
            if startup:
                self.events.put(("log", startup))
            _, output = adb(["devices", "-l"], timeout=20)
            if output:
                self.events.put(("log", output))
            found = parse_devices(output)
            self.events.put(("devices", found))
            if not found:
                self.events.put(("log", "Chưa thấy thiết bị. Thử cáp USB dữ liệu và chấp nhận lời nhắc Gỡ lỗi USB."))
        self.task("Đang kiểm tra điện thoại...", work)

    def choose_apk(self):
        path = filedialog.askopenfilename(parent=self.root, title="Chọn file APK",
                                          filetypes=[("Android package", "*.apk"), ("Tất cả tệp", "*.*")])
        if path:
            self.apk_var.set(path)

    def install(self):
        device = self.chosen_device()
        if not device:
            return
        path = self.apk_var.get().strip().strip('"')
        if not path:
            self.choose_apk()
            path = self.apk_var.get().strip().strip('"')
        if not path:
            return
        apk_file = Path(path)
        if not apk_file.is_file():
            messagebox.showerror("Không tìm thấy APK", "Đường dẫn file không tồn tại.", parent=self.root)
            return
        if apk_file.suffix.lower() != ".apk" and not messagebox.askyesno(
                "Kiểm tra tệp", "Tệp không có đuôi .apk. Vẫn thử cài?", parent=self.root):
            return
        serial = device["serial"]
        self.events.put(("log", f"\n--- Cài {apk_file.name} lên {serial} ---"))

        def work():
            code, output = adb(["-s", serial, "install", "-r", str(apk_file)], timeout=300)
            self.events.put(("log", output or "(ADB không trả nội dung.)"))
            if code == 0 and "Success" in output:
                self.events.put(("log", "HOÀN TẤT: cài APK thành công."))
            else:
                lower = output.lower()
                if "unauthorized" in lower:
                    hint = "Điện thoại chưa cấp quyền Gỡ lỗi USB."
                elif "no devices" in lower or "device not found" in lower:
                    hint = "ADB không tìm thấy điện thoại. Kiểm tra cáp, driver và Gỡ lỗi USB."
                elif "version_downgrade" in lower:
                    hint = "APK có phiên bản thấp hơn ứng dụng đang cài."
                elif "update_incompatible" in lower or "signatures" in lower:
                    hint = "Bản APK ký khác với bản đang cài. Công cụ không tự gỡ bản cũ để tránh mất dữ liệu."
                elif "insufficient_storage" in lower:
                    hint = "Có thể điện thoại không còn đủ dung lượng."
                elif "user_restricted" in lower or "policy" in lower or "blocked" in lower:
                    hint = "Android có thể đang chặn cài đặt bởi cài đặt bảo mật hoặc chính sách quản lý."
                else:
                    hint = "Xem dòng Failure chi tiết trong Nhật ký; APK có thể không tương thích hoặc bị Android chặn."
                raise RuntimeError("Cài đặt thất bại.\n" + hint + "\n\nChi tiết ADB:\n" + output)
        self.task("Đang cài APK — giữ điện thoại kết nối...", work)

    def package_list(self, serial):
        code, output = adb(["-s", serial, "shell", "pm", "list", "packages", "-3"], timeout=90)
        if code != 0:
            raise RuntimeError("Không tải được danh sách ứng dụng.\n" + output)
        result = []
        for line in output.splitlines():
            item = line.strip()
            if item.startswith("package:"):
                result.append(item[len("package:"):].strip())
        return sorted(set(filter(None, result)), key=str.lower)

    def refresh_packages(self):
        device = self.chosen_device()
        if not device:
            return
        serial = device["serial"]
        def work():
            self.events.put(("log", f"\n--- Tải danh sách ứng dụng từ {serial} ---"))
            packages = self.package_list(serial)
            self.events.put(("packages", packages))
            self.events.put(("log", f"Đã tải {len(packages)} gói ứng dụng."))
        self.task("Đang tải danh sách ứng dụng...", work)

    def uninstall(self):
        device = self.chosen_device()
        if not device:
            return
        chosen = self.package_tree.selection()
        if not chosen:
            messagebox.showinfo("Chưa chọn ứng dụng", "Chọn một ứng dụng trong danh sách trước.", parent=self.root)
            return
        values = self.package_tree.item(chosen[0], "values")
        if not values:
            return
        package = values[0]
        ok = messagebox.askyesno(
            "Xác nhận gỡ ứng dụng",
            f"Gỡ ứng dụng này khỏi điện thoại?\n\n{package}\n\nThao tác có thể xóa dữ liệu. Không thể tự hoàn tác.",
            icon="warning", parent=self.root
        )
        if not ok:
            return
        serial = device["serial"]
        def work():
            self.events.put(("log", f"\n--- Gỡ {package} khỏi {serial} ---"))
            code, output = adb(["-s", serial, "uninstall", package], timeout=120)
            self.events.put(("log", output or "(ADB không trả nội dung.)"))
            if code != 0 or "Success" not in output:
                raise RuntimeError("Gỡ ứng dụng thất bại.\n" + output)
            self.events.put(("packages", self.package_list(serial)))
            self.events.put(("log", "Đã gỡ ứng dụng đã chọn." ))
        self.task("Đang gỡ ứng dụng...", work)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
