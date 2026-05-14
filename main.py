import csv
import io
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import shlex
import shutil
import webbrowser

VERSION = "26.5.7.04"


class GAMGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self._dark = True
        self.title(f"GAM GUI  v{VERSION}")
        self.geometry("780x740")
        self.minsize(640, 580)
        try:
            base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
            self.iconbitmap(os.path.join(base, "gam_logo.ico"))
        except Exception:
            pass
        ttk.Style().theme_use("clam")
        self._build_ui()
        self._check_gam()
        self._apply_theme()
        self.after(100, self._show_startup_notice)

    def _show_startup_notice(self):
        dlg = tk.Toplevel(self)
        dlg.title("Before You Begin")
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Frame(dlg, bg="#8b0000", height=6).pack(fill="x")

        body = tk.Frame(dlg, padx=28, pady=20)
        body.pack()

        tk.Label(
            body,
            text="⚠  You must have GAM installed and connected to\nyour Domain before using this tool!",
            font=("Segoe UI", 11, "bold"),
            justify="center",
        ).pack(pady=(0, 14))

        link = tk.Label(
            body,
            text="GAM Installation & Setup Guide →",
            font=("Segoe UI", 10, "underline"),
            fg="#8b0000",
            cursor="hand2",
        )
        link.pack(pady=(0, 18))
        link.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/GAM-team/GAM/wiki"))

        ttk.Button(dlg, text="I have GAM installed — Continue", command=dlg.destroy).pack(pady=(0, 16))

        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    def _check_gam(self):
        if not shutil.which("gam"):
            self.log(
                "WARNING: 'gam' not found in PATH. "
                "Make sure GAM is installed and accessible from the terminal.",
                "warning",
            )

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        header = tk.Frame(self, bg="#8b0000", height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._header = header
        tk.Label(
            header, text="GAM GUI",
            font=("Segoe UI", 15, "bold"), fg="white", bg="#8b0000",
        ).pack(side="left", padx=16, pady=10)
        tk.Label(
            header, text=f"v{VERSION}",
            font=("Segoe UI", 9), fg="#ffcccc", bg="#8b0000",
        ).pack(side="left", pady=10)
        self._theme_btn = tk.Button(
            header, text="☾  Dark",
            bg="#6b0000", fg="white", activebackground="#560000", activeforeground="white",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            font=("Segoe UI", 9),
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right", padx=12)

        body = tk.Frame(self, bg="#f5f5f5")
        body.pack(fill="both", expand=True, padx=16, pady=14)

        notebook = ttk.Notebook(body)
        notebook.pack(fill="x")

        # ── Gmail ──────────────────────────────────────────────────────────
        gmail_frame = ttk.Frame(notebook)
        notebook.add(gmail_frame, text="  Gmail  ")
        gmail_nb = ttk.Notebook(gmail_frame)
        gmail_nb.pack(fill="both", expand=True)

        tab_msgid = ttk.Frame(gmail_nb, padding=12)
        gmail_nb.add(tab_msgid, text="  Delete by Message-ID  ")
        self.msgid_tab = self._build_list_tab(
            tab_msgid,
            query_label="Message-ID(s):",
            query_hint="One per line",
            on_preview=lambda: self._run_list_tab(self.msgid_tab, "msgid", dry_run=True),
            on_delete=self._confirm_delete_msgid,
        )

        tab_sender = ttk.Frame(gmail_nb, padding=12)
        gmail_nb.add(tab_sender, text="  Delete by Sender  ")
        self.sender_tab = self._build_list_tab(
            tab_sender,
            query_label="Sender Email(s):",
            query_hint="One per line",
            on_preview=lambda: self._run_list_tab(self.sender_tab, "sender", dry_run=True),
            on_delete=self._confirm_delete_sender,
        )

        tab_props = ttk.Frame(gmail_nb, padding=12)
        gmail_nb.add(tab_props, text="  Delete by Properties  ")
        self.props_tab = self._build_properties_tab(tab_props)

        # ── Google Drive ───────────────────────────────────────────────────
        drive_frame = ttk.Frame(notebook)
        notebook.add(drive_frame, text="  Google Drive  ")
        drive_nb = ttk.Notebook(drive_frame)
        drive_nb.pack(fill="both", expand=True)

        tab_drive = ttk.Frame(drive_nb, padding=12)
        drive_nb.add(tab_drive, text="  Delete Drive Files  ")
        self.drive_tab = self._build_drive_tab(tab_drive)

        # ── Google Classroom ───────────────────────────────────────────────
        classroom_frame = ttk.Frame(notebook)
        notebook.add(classroom_frame, text="  Google Classroom  ")
        tab_classroom = ttk.Frame(classroom_frame, padding=12)
        tab_classroom.pack(fill="both", expand=True)
        self.classroom_tab = self._build_classroom_tab(tab_classroom)

        # ── Custom Command ─────────────────────────────────────────────────
        custom_frame = ttk.Frame(notebook)
        notebook.add(custom_frame, text="  Custom Command  ")
        tab_custom = ttk.Frame(custom_frame, padding=12)
        tab_custom.pack(fill="both", expand=True)
        self.custom_tab = self._build_custom_tab(tab_custom)

        self._build_log_section(body)

    # ---------------------------------------------------------------- tabs --

    def _build_target_section(self, parent, row=0):
        """Shared target radio + email/domain rows. Returns refs dict."""
        target_var = tk.StringVar(value="specific")
        radio_frame = tk.Frame(parent)
        radio_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(radio_frame, text="Target:").pack(side="left", padx=(0, 12))
        for text, value in [("Specific User", "specific"), ("Domain", "domain"), ("All Users", "all")]:
            ttk.Radiobutton(
                radio_frame, text=text, variable=target_var, value=value,
            ).pack(side="left", padx=(0, 10))

        email_label = ttk.Label(parent, text="Mailbox Owner Email:")
        email_label.grid(row=row + 1, column=0, sticky="w", pady=(0, 8))
        email_var = tk.StringVar()
        email_entry = ttk.Entry(parent, textvariable=email_var, font=("Segoe UI", 10))
        email_entry.grid(row=row + 1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 8))

        domain_label = ttk.Label(parent, text="Domain:")
        domain_var = tk.StringVar()
        domain_entry = ttk.Entry(parent, textvariable=domain_var, font=("Segoe UI", 10))

        refs = {
            "target_var": target_var,
            "email_var": email_var, "email_label": email_label, "email_entry": email_entry,
            "domain_var": domain_var, "domain_label": domain_label, "domain_entry": domain_entry,
            "_target_row": row + 1,
        }
        target_var.trace_add("write", lambda *_: self._on_target_change(refs))
        return refs

    def _build_list_tab(self, parent, query_label, query_hint, on_preview, on_delete):
        parent.columnconfigure(1, weight=1)
        refs = self._build_target_section(parent, row=0)

        ttk.Label(parent, text=query_label).grid(row=3, column=0, sticky="nw")
        ttk.Label(parent, text=query_hint, style="Hint.TLabel").grid(
            row=4, column=0, sticky="nw"
        )
        txt_frame = tk.Frame(parent)
        txt_frame.grid(row=3, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        txt_frame.columnconfigure(0, weight=1)
        txt_frame.rowconfigure(0, weight=1)
        query_text = tk.Text(
            txt_frame, height=5, font=("Courier New", 9), wrap="none",
            relief="flat", highlightthickness=1, highlightbackground="#cccccc",
        )
        query_text.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(txt_frame, orient="vertical", command=query_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        query_text.configure(yscrollcommand=sb.set)

        btn_row = tk.Frame(parent)
        btn_row.grid(row=5, column=0, columnspan=3, sticky="e", pady=(10, 0))
        delete_btn = ttk.Button(btn_row, text="Delete Messages", command=on_delete)
        delete_btn.pack(side="right")
        preview_btn = ttk.Button(btn_row, text="Preview", command=on_preview)
        preview_btn.pack(side="right", padx=(0, 6))
        ttk.Button(
            btn_row, text="Clear Fields",
            command=lambda: [refs["email_var"].set(""), refs["domain_var"].set(""),
                             query_text.delete("1.0", "end")],
        ).pack(side="right", padx=(0, 6))

        refs.update({"query_text": query_text, "delete_btn": delete_btn, "preview_btn": preview_btn})
        return refs

    def _build_properties_tab(self, parent):
        parent.columnconfigure(1, weight=1)
        refs = self._build_target_section(parent, row=0)

        # From field
        ttk.Label(parent, text="From:").grid(row=3, column=0, sticky="w", pady=(0, 8))
        from_var = tk.StringVar()
        ttk.Entry(parent, textvariable=from_var, font=("Segoe UI", 10)).grid(
            row=3, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 8)
        )

        # Keywords field (searches subject + body)
        ttk.Label(parent, text="Keywords:").grid(row=4, column=0, sticky="w", pady=(0, 4))
        ttk.Label(
            parent, text="Searches subject and body — paste filename or phrase as seen in the email",
            style="Hint.TLabel",
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))
        subject_var = tk.StringVar()
        ttk.Entry(parent, textvariable=subject_var, font=("Segoe UI", 10)).grid(
            row=4, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4)
        )

        # Date range
        date_frame = tk.Frame(parent)
        date_frame.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(date_frame, text="After (YYYY-MM-DD):").pack(side="left")
        after_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=after_var, width=14, font=("Segoe UI", 10)).pack(
            side="left", padx=(6, 20)
        )
        ttk.Label(date_frame, text="Before (YYYY-MM-DD):").pack(side="left")
        before_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=before_var, width=14, font=("Segoe UI", 10)).pack(
            side="left", padx=(6, 0)
        )

        # Live query preview
        ttk.Label(parent, text="Gmail Query:").grid(row=7, column=0, sticky="w", pady=(0, 4))
        ttk.Label(
            parent, text="Auto-built from fields above — review before running",
            style="Hint.TLabel",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 6))
        query_preview_var = tk.StringVar()
        query_preview = ttk.Entry(
            parent, textvariable=query_preview_var, font=("Courier New", 9),
            state="readonly",
        )
        query_preview.grid(row=7, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4))

        # Buttons
        btn_row = tk.Frame(parent)
        btn_row.grid(row=9, column=0, columnspan=3, sticky="e", pady=(6, 0))
        delete_btn = ttk.Button(
            btn_row, text="Delete Messages",
            command=lambda: self._confirm_delete_props(),
        )
        delete_btn.pack(side="right")
        preview_btn = ttk.Button(
            btn_row, text="Preview",
            command=lambda: self._run_props(dry_run=True),
        )
        preview_btn.pack(side="right", padx=(0, 6))
        find_btn = ttk.Button(
            btn_row, text="Find Messages",
            command=lambda: self._find_messages_props(),
        )
        find_btn.pack(side="right", padx=(0, 6))
        ttk.Button(
            btn_row, text="Clear Fields",
            command=lambda: [
                refs["email_var"].set(""), refs["domain_var"].set(""),
                from_var.set(""), subject_var.set(""),
                after_var.set(""), before_var.set(""),
            ],
        ).pack(side="right", padx=(0, 6))

        refs.update({
            "from_var": from_var,
            "subject_var": subject_var,
            "after_var": after_var,
            "find_btn": find_btn,
            "before_var": before_var,
            "query_preview_var": query_preview_var,
            "delete_btn": delete_btn,
            "preview_btn": preview_btn,
        })

        # Wire live query preview updates
        for var in (from_var, subject_var, after_var, before_var):
            var.trace_add("write", lambda *_: self._update_props_query(refs))

        return refs

    def _build_custom_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="GAM Command:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        cmd_var = tk.StringVar(value="gam ")
        cmd_entry = ttk.Entry(parent, textvariable=cmd_var, font=("Courier New", 10))
        cmd_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 4))
        cmd_entry.bind("<Return>", lambda _: self._run_custom_command())

        ttk.Label(parent, text="Type any GAM command — press Enter or Run to execute",
                  style="Hint.TLabel").grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        ttk.Label(parent, text="Recent:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        history_cb = ttk.Combobox(parent, state="readonly", font=("Courier New", 9))
        history_cb.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(0, 4))
        history_cb.bind("<<ComboboxSelected>>", lambda _: cmd_var.set(history_cb.get()))
        ttk.Label(parent, text="Commands run this session",
                  style="Hint.TLabel").grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        btn_row = tk.Frame(parent)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(0, 16))
        run_btn = ttk.Button(btn_row, text="Run Command", command=lambda: self._run_custom_command())
        run_btn.pack(side="right")
        ttk.Button(btn_row, text="Clear",
                   command=lambda: cmd_var.set("gam ")).pack(side="right", padx=(0, 6))

        ttk.Separator(parent, orient="horizontal").grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        atlas_lf = ttk.LabelFrame(parent, text="GAM Atlas — AI Assistant", padding=10)
        atlas_lf.grid(row=6, column=0, columnspan=2, sticky="ew")
        atlas_lf.columnconfigure(0, weight=1)

        ttk.Label(
            atlas_lf,
            text="GAM Atlas is a custom AI assistant trained on GAM commands and syntax.\n"
                 "It can help you build commands, troubleshoot errors, and explore GAM features.",
            style="Hint.TLabel",
            wraplength=580,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Label(
            atlas_lf,
            text="Opens as a companion window next to this app (Edge app-mode — no address bar or tabs).\n"
                 "Requires a ChatGPT account. Your session is preserved between opens.",
            style="Hint.TLabel",
            wraplength=580,
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        ttk.Button(
            atlas_lf,
            text="Open GAM Atlas  →",
            command=self._open_atlas,
        ).grid(row=2, column=0, sticky="w")

        return {
            "cmd_var": cmd_var,
            "cmd_entry": cmd_entry,
            "history_cb": history_cb,
            "run_btn": run_btn,
            "history": [],
        }

    def _build_log_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Output Log", padding=8)
        frame.pack(fill="both", expand=True, pady=(12, 0))

        self.log_area = scrolledtext.ScrolledText(
            frame, height=10, font=("Courier New", 9), state="disabled",
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", relief="flat",
        )
        self.log_area.pack(fill="both", expand=True)

        self.log_area.tag_config("success", foreground="#4ec9b0")
        self.log_area.tag_config("error", foreground="#f44747")
        self.log_area.tag_config("warning", foreground="#dcdcaa")
        self.log_area.tag_config("info", foreground="#9cdcfe")
        self.log_area.tag_config("cmd", foreground="#c586c0")
        self.log_area.tag_config("preview", foreground="#ce9178")

        log_btn_row = tk.Frame(frame)
        log_btn_row.pack(anchor="e", pady=(6, 0))

        def _export_log(fmt):
            content = self.log_area.get("1.0", "end").strip()
            if not content:
                messagebox.showwarning("Export", "The log is empty.")
                return
            default = f"gam_log.{fmt}"
            path = filedialog.asksaveasfilename(
                parent=self, title="Export Log", initialfile=default,
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    if fmt == "csv":
                        writer = csv.writer(f)
                        writer.writerow(["Line", "Text"])
                        for i, line in enumerate(content.splitlines(), 1):
                            writer.writerow([i, line])
                    else:
                        f.write(content + "\n")
                messagebox.showinfo("Export", f"Log saved to:\n{path}")
            except OSError as e:
                messagebox.showerror("Export Failed", str(e))

        ttk.Button(log_btn_row, text="Export .csv", command=lambda: _export_log("csv")).pack(side="left")
        ttk.Button(log_btn_row, text="Export .txt", command=lambda: _export_log("txt")).pack(side="left", padx=(6, 0))
        ttk.Button(log_btn_row, text="Clear Log", command=self._clear_log).pack(side="left", padx=(6, 0))

    def _build_drive_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        # Row 0: Scope selector
        scope_var = tk.StringVar(value="user")
        scope_frame = tk.Frame(parent)
        scope_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(scope_frame, text="Scope:").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(scope_frame, text="Single User", variable=scope_var, value="user").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(scope_frame, text="Organizational Unit", variable=scope_var, value="ou").pack(side="left")

        # Row 1: User email (single-user mode) — shown/hidden by scope
        email_label = ttk.Label(parent, text="User Email:")
        email_var = tk.StringVar()
        email_entry = ttk.Entry(parent, textvariable=email_var, font=("Segoe UI", 10))
        email_hint = ttk.Label(parent, text="User who owns or has access to the target files",
                               style="Hint.TLabel")

        # Row 1: OU path (OU mode) — shown/hidden by scope
        ou_label = ttk.Label(parent, text="OU Path:")
        ou_var = tk.StringVar()
        ou_frame = tk.Frame(parent)
        ou_entry = ttk.Entry(ou_frame, textvariable=ou_var, font=("Segoe UI", 10))
        ou_entry.pack(side="left", fill="x", expand=True)
        ou_browse_btn = ttk.Button(ou_frame, text="Browse OUs…",
                                   command=lambda: self._browse_drive_ous(refs))
        ou_browse_btn.pack(side="left", padx=(6, 0))
        ou_hint = ttk.Label(parent, text="Full OU path, e.g.  /Students/Grade 9  •  use Browse to pick from domain",
                            style="Hint.TLabel")

        # Row 3: Drive type
        drive_type_var = tk.StringVar(value="mydrive")
        dt_frame = tk.Frame(parent)
        dt_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(dt_frame, text="Drive:").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(dt_frame, text="My Drive", variable=drive_type_var, value="mydrive").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(dt_frame, text="Shared Drive", variable=drive_type_var, value="shared").pack(side="left")

        # Row 4: Shared Drive ID (conditional)
        shared_label = ttk.Label(parent, text="Shared Drive ID:")
        shared_var = tk.StringVar()
        shared_entry = ttk.Entry(parent, textvariable=shared_var, font=("Segoe UI", 10))

        # Row 5: Method selector
        method_var = tk.StringVar(value="fileid")
        m_frame = tk.Frame(parent)
        m_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(m_frame, text="Find by:").pack(side="left", padx=(0, 12))
        fileid_radio = ttk.Radiobutton(m_frame, text="File ID(s)", variable=method_var, value="fileid")
        fileid_radio.pack(side="left", padx=(0, 10))
        ttk.Radiobutton(m_frame, text="File Name", variable=method_var, value="name").pack(side="left")

        # Rows 6/7: File ID input
        fileid_label = ttk.Label(parent, text="File ID(s):")
        fileid_hint = ttk.Label(parent, text="One per line  •  copy the ID from the file's Drive share URL",
                                style="Hint.TLabel")
        fileid_outer = tk.Frame(parent)
        fileid_outer.columnconfigure(0, weight=1)
        fileid_outer.rowconfigure(0, weight=1)
        fileid_text = tk.Text(fileid_outer, height=4, font=("Courier New", 9), wrap="none",
                              relief="flat", highlightthickness=1, highlightbackground="#cccccc")
        _fsb = ttk.Scrollbar(fileid_outer, orient="vertical", command=fileid_text.yview)
        fileid_text.configure(yscrollcommand=_fsb.set)
        fileid_text.grid(row=0, column=0, sticky="nsew")
        _fsb.grid(row=0, column=1, sticky="ns")

        # Rows 6/7/8: File Name input
        name_label = ttk.Label(parent, text="File Name:")
        name_var = tk.StringVar()
        name_entry = ttk.Entry(parent, textvariable=name_var, font=("Segoe UI", 10))
        name_hint = ttk.Label(parent, text="Finds files whose name contains this text  •  case-insensitive",
                              style="Hint.TLabel")
        drive_q_label = ttk.Label(parent, text="Drive Query:")
        drive_q_var = tk.StringVar()
        drive_q_preview = ttk.Entry(parent, textvariable=drive_q_var,
                                    font=("Courier New", 9), state="readonly")

        # Row 9: Purge
        purge_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            parent, text="Permanently delete (skip trash — cannot be recovered)",
            variable=purge_var,
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # Row 10: Buttons
        btn_row = tk.Frame(parent)
        btn_row.grid(row=10, column=0, columnspan=3, sticky="e", pady=(10, 0))
        delete_btn = ttk.Button(btn_row, text="Delete Files",
                                command=lambda: self._confirm_delete_drive())
        delete_btn.pack(side="right")
        find_btn = ttk.Button(btn_row, text="Find Files",
                              command=lambda: self._find_drive_files())
        find_btn.pack(side="right", padx=(0, 6))
        ttk.Button(
            btn_row, text="Clear Fields",
            command=lambda: [
                email_var.set(""), shared_var.set(""), ou_var.set(""),
                fileid_text.delete("1.0", "end"),
                name_var.set(""),
            ],
        ).pack(side="right", padx=(0, 6))

        refs = {
            "scope_var": scope_var,
            "email_label": email_label, "email_var": email_var,
            "email_entry": email_entry, "email_hint": email_hint,
            "ou_label": ou_label, "ou_var": ou_var,
            "ou_frame": ou_frame, "ou_hint": ou_hint,
            "fileid_radio": fileid_radio,
            "drive_type_var": drive_type_var,
            "shared_label": shared_label, "shared_var": shared_var, "shared_entry": shared_entry,
            "method_var": method_var,
            "fileid_label": fileid_label, "fileid_hint": fileid_hint, "fileid_outer": fileid_outer,
            "fileid_text": fileid_text,
            "name_label": name_label, "name_var": name_var, "name_entry": name_entry,
            "name_hint": name_hint,
            "drive_q_label": drive_q_label, "drive_q_var": drive_q_var, "drive_q_preview": drive_q_preview,
            "purge_var": purge_var,
            "delete_btn": delete_btn, "find_btn": find_btn,
        }

        scope_var.trace_add("write", lambda *_: self._on_drive_scope_change(refs))
        drive_type_var.trace_add("write", lambda *_: self._on_drive_type_change(refs))
        method_var.trace_add("write", lambda *_: self._on_drive_method_change(refs))
        name_var.trace_add("write", lambda *_: self._update_drive_query(refs))

        self._on_drive_scope_change(refs)
        self._on_drive_type_change(refs)
        self._on_drive_method_change(refs)

        return refs

    def _build_classroom_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="Teacher Email:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        teacher_var = tk.StringVar()
        ttk.Entry(parent, textvariable=teacher_var, font=("Segoe UI", 10)).grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4)
        )
        ttk.Label(parent, text="Leave blank to search all courses in the domain",
                  style="Hint.TLabel").grid(
            row=1, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=(0, 8)
        )

        ttk.Label(parent, text="Course Name:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        name_var = tk.StringVar()
        ttk.Entry(parent, textvariable=name_var, font=("Segoe UI", 10)).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4)
        )
        ttk.Label(parent, text="Optional — filters results by course name (partial match, case-insensitive)",
                  style="Hint.TLabel").grid(
            row=3, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=(0, 8)
        )

        state_var = tk.StringVar(value="all")
        state_frame = tk.Frame(parent)
        state_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(state_frame, text="State:").pack(side="left", padx=(0, 12))
        for text, value in [("All", "all"), ("Active", "ACTIVE"), ("Archived", "ARCHIVED"), ("Provisioned", "PROVISIONED")]:
            ttk.Radiobutton(state_frame, text=text, variable=state_var, value=value).pack(side="left", padx=(0, 10))

        top_btn_row = tk.Frame(parent)
        top_btn_row.grid(row=5, column=0, columnspan=3, sticky="e", pady=(0, 8))
        find_btn = ttk.Button(top_btn_row, text="Find Classrooms", command=lambda: self._find_classrooms())
        find_btn.pack(side="right")
        ttk.Button(
            top_btn_row, text="Clear Fields",
            command=lambda: self._clear_classrooms(),
        ).pack(side="right", padx=(0, 6))

        results_label_var = tk.StringVar(value="No results — use Find Classrooms to search")
        ttk.Label(parent, textvariable=results_label_var,
                  style="Hint.TLabel").grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 4))

        tree_frame = tk.Frame(parent)
        tree_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("id", "name", "owner", "state")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            selectmode="extended", height=8)
        col_cfg = [("id", "Course ID", 160), ("name", "Course Name", 280),
                   ("owner", "Owner Email", 210), ("state", "State", 100)]
        for col, heading, width in col_cfg:
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        action_row = tk.Frame(parent)
        action_row.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        def _export_classrooms(fmt):
            rows = [tree.item(iid)["values"] for iid in tree.get_children()]
            if not rows:
                messagebox.showwarning("Export", "No results to export.", parent=self)
                return
            col_headings = ["Course ID", "Course Name", "Owner Email", "State"]
            default = f"classrooms.{fmt}"
            path = filedialog.asksaveasfilename(
                parent=self, title="Export Results", initialfile=default,
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    if fmt == "csv":
                        writer = csv.writer(f)
                        writer.writerow(col_headings)
                        for row in rows:
                            writer.writerow(row)
                    else:
                        col_w = [max(len(col_headings[i]), max((len(str(r[i])) for r in rows), default=0)) for i in range(len(col_headings))]
                        header = "  ".join(col_headings[i].ljust(col_w[i]) for i in range(len(col_headings)))
                        sep = "  ".join("-" * w for w in col_w)
                        f.write(f"{header}\n{sep}\n")
                        for row in rows:
                            f.write("  ".join(str(row[i]).ljust(col_w[i]) for i in range(len(col_headings))) + "\n")
                messagebox.showinfo("Export", f"Saved {len(rows)} row(s) to:\n{path}", parent=self)
            except OSError as e:
                messagebox.showerror("Export Failed", str(e), parent=self)

        ttk.Button(action_row, text="Export .csv", command=lambda: _export_classrooms("csv")).pack(side="left")
        ttk.Button(action_row, text="Export .txt", command=lambda: _export_classrooms("txt")).pack(side="left", padx=(6, 0))

        delete_btn = ttk.Button(action_row, text="Delete Selected",
                                command=lambda: self._confirm_delete_classrooms())
        delete_btn.pack(side="right")
        ttk.Button(action_row, text="Deselect All",
                   command=lambda: tree.selection_remove(tree.get_children())).pack(side="right", padx=(0, 6))
        ttk.Button(action_row, text="Select All",
                   command=lambda: tree.selection_set(tree.get_children())).pack(side="right", padx=(0, 6))

        return {
            "teacher_var": teacher_var,
            "name_var": name_var,
            "state_var": state_var,
            "find_btn": find_btn,
            "delete_btn": delete_btn,
            "tree": tree,
            "results_label_var": results_label_var,
        }

    # ------------------------------------------------------------- Actions --

    def _on_target_change(self, refs):
        target = refs["target_var"].get()
        row = refs["_target_row"]
        refs["email_label"].grid_remove()
        refs["email_entry"].grid_remove()
        refs["domain_label"].grid_remove()
        refs["domain_entry"].grid_remove()
        if target == "specific":
            refs["email_label"].grid(row=row, column=0, sticky="w", pady=(0, 8))
            refs["email_entry"].grid(row=row, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 8))
        elif target == "domain":
            refs["domain_label"].grid(row=row, column=0, sticky="w", pady=(0, 8))
            refs["domain_entry"].grid(row=row, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 8))

    def _target_label(self, target, email, domain):
        if target == "all":
            return "all active (non-suspended) mailboxes"
        if target == "domain":
            return f"all active users in @{domain}"
        return email

    def _build_cmd(self, target, email, domain, query, dry_run):
        if target == "all":
            base = ["gam", "query", "isSuspended=false", "delete", "messages", "query", query]
        elif target == "domain":
            base = ["gam", "domains_ns", domain, "delete", "messages", "query", query]
        else:
            base = ["gam", "user", email, "delete", "messages", "query", query]
        if not dry_run:
            base.append("doit")
        return base

    # --- Properties tab query builder ---

    def _normalize_subject(self, raw: str) -> str:
        """
        Prepare a subject string for Gmail phrase search.
        - Strips surrounding/internal quote characters copied from email headers
        - Replaces underscores with spaces (Gmail tokenizes on underscores)
        - Strips common file extensions which Gmail indexes separately
        - Collapses whitespace
        """
        s = raw.strip()
        # Remove all quote characters — surrounding and internal — before building the phrase
        s = s.replace('"', '').replace("'", '')
        # Replace underscores with spaces
        s = s.replace("_", " ")
        # Strip common file extensions
        s = re.sub(r'\.(docx?|xlsx?|pptx?|pdf|csv|txt|zip|msg)\b', '', s, flags=re.IGNORECASE)
        # Collapse multiple spaces
        s = re.sub(r'\s{2,}', ' ', s).strip()
        return s

    def _build_props_query(self, refs) -> str:
        parts = []
        from_val = refs["from_var"].get().strip()
        subject_val = refs["subject_var"].get().strip()
        after_val = refs["after_var"].get().strip()
        before_val = refs["before_var"].get().strip()

        if from_val:
            # Strip any operator prefix the user may have pasted (e.g. "from:user@example.com")
            clean_from = re.sub(r'^from:', '', from_val, flags=re.IGNORECASE).strip()
            if clean_from:
                parts.append(f"from:{clean_from}")
        if subject_val:
            # Strip any operator prefix the user may have pasted (subject:, from:, etc.)
            clean_subject = re.sub(r'^\w+:', '', subject_val, flags=re.IGNORECASE).strip()
            normalized = self._normalize_subject(clean_subject)
            if normalized:
                # Plain phrase search (no subject: qualifier) — matches subject AND body.
                # Drive share filenames live in the body, not the subject line.
                parts.append(f'"{normalized}"')
        if after_val:
            parts.append(f"after:{after_val.replace('-', '/')}")
        if before_val:
            parts.append(f"before:{before_val.replace('-', '/')}")
        return " ".join(parts)

    def _update_props_query(self, refs):
        refs["query_preview_var"].set(self._build_props_query(refs))

    # --- Find Messages ---

    def _find_messages_props(self):
        refs = self.props_tab
        target = refs["target_var"].get()
        email = refs["email_var"].get().strip()
        domain = refs["domain_var"].get().strip()
        if not self._validate_target(target, email, domain):
            return
        query = self._build_props_query(refs)
        if not query:
            messagebox.showwarning("Missing Input", "Please fill in at least one search field.")
            return
        if target in ("all", "domain"):
            messagebox.showinfo(
                "Specific User Required",
                "Find Messages works on a single mailbox so you can verify your query\n"
                "before running a domain-wide delete.\n\n"
                "Switch to Specific User, pick someone you know received the email,\n"
                "confirm the query is right, then switch back to Domain / All Users to delete.",
            )
            return

        refs["find_btn"].config(state="disabled")
        thread = threading.Thread(
            target=self._find_messages_worker,
            args=(target, email, domain, query, refs),
            daemon=True,
        )
        thread.start()

    def _find_messages_worker(self, target, email, domain, query, refs):
        if target == "domain":
            base = ["gam", "domains_ns", domain]
        else:
            base = ["gam", "user", email]

        cmd = base + [
            "print", "messages",
            "query", query,
            "headers", "Subject,From,Date",
            "max_to_print", "50",
        ]

        self.log(f"[FIND] {' '.join(cmd)}", "cmd")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if stderr:
                self.log(f"  {stderr}", "warning")

            if not stdout:
                self.log("  No messages returned — the mailbox may have no matching messages.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return

            rows = list(csv.DictReader(io.StringIO(stdout)))
            if not rows:
                self.log("  GAM returned output but no parseable rows.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return

            # Log a summary so there's always something visible in the log
            col_map = {k.lower(): k for k in rows[0].keys()}
            subj_key = col_map.get("subject", "")
            self.log(f"  Found {len(rows)} message(s):", "preview")
            for r in rows:
                self.log(f"    Subject: {r.get(subj_key, '(no subject)')}", "preview")

            self.after(0, lambda: self._show_find_results(rows, query, refs))

        except subprocess.TimeoutExpired:
            self.log("  TIMEOUT during Find Messages.", "error")
        except FileNotFoundError:
            self.log("ERROR: 'gam' not found.", "error")

        self.after(0, lambda: refs["find_btn"].config(state="normal"))

    def _show_find_results(self, rows, query, refs):
        refs["find_btn"].config(state="normal")
        if not rows:
            messagebox.showinfo("Find Messages", "No messages matched the query.")
            return

        win = tk.Toplevel(self)
        win.title(f"Found Messages — {len(rows)} result(s)")
        win.geometry("860x460")
        win.minsize(600, 250)

        ttk.Label(win, text=f'Query: {query}', font=("Segoe UI", 9),
                  style="Hint.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(win, text=f"{len(rows)} message(s) matched  •  max 50 shown",
                  style="Hint.TLabel").pack(anchor="w", padx=12, pady=(0, 6))

        # Detect available columns (GAM may capitalise differently)
        sample = rows[0]
        col_map = {k.lower(): k for k in sample.keys()}
        subject_key = col_map.get("subject", "")
        from_key    = col_map.get("from", "")
        date_key    = col_map.get("date", "")
        user_key    = col_map.get("user", "")

        display_cols = [c for c in (user_key, date_key, from_key, subject_key) if c]
        if not display_cols:
            display_cols = list(sample.keys())

        _gmail_labels = {"user": "User Email", "date": "Date", "from": "From", "subject": "Subject"}
        col_labels = [_gmail_labels.get(c.lower(), c) or c for c in display_cols]

        def _export_gmail(fmt):
            default = f"gmail_results.{fmt}"
            path = filedialog.asksaveasfilename(
                parent=win, title="Export Results", initialfile=default,
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    if fmt == "csv":
                        writer = csv.writer(f)
                        writer.writerow(col_labels)
                        for row in rows:
                            writer.writerow([row.get(c, "") for c in display_cols])
                    else:
                        col_w = [max(len(col_labels[i]), max((len(str(row.get(display_cols[i], ""))) for row in rows), default=0)) for i in range(len(display_cols))]
                        header = "  ".join(col_labels[i].ljust(col_w[i]) for i in range(len(col_labels)))
                        sep = "  ".join("-" * w for w in col_w)
                        f.write(f"Query: {query}\n{header}\n{sep}\n")
                        for row in rows:
                            f.write("  ".join(str(row.get(display_cols[i], "")).ljust(col_w[i]) for i in range(len(display_cols))) + "\n")
                messagebox.showinfo("Export", f"Saved {len(rows)} row(s) to:\n{path}", parent=win)
            except OSError as e:
                messagebox.showerror("Export Failed", str(e), parent=win)

        btn_row = tk.Frame(win)
        btn_row.pack(fill="x", padx=12, pady=(0, 10), side="bottom")
        ttk.Button(btn_row, text="Export .csv", command=lambda: _export_gmail("csv")).pack(side="left")
        ttk.Button(btn_row, text="Export .txt", command=lambda: _export_gmail("txt")).pack(side="left", padx=(6, 0))
        ttk.Button(btn_row, text="Close", command=win.destroy).pack(side="right")

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        tree = ttk.Treeview(frame, columns=display_cols, show="headings", selectmode="browse")
        col_widths = {"subject": 340, "from": 200, "date": 160, "user": 200}
        for col in display_cols:
            width = col_widths.get(col.lower(), 180)
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=80)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        for row in rows:
            tree.insert("", "end", values=[row.get(c, "") for c in display_cols])

        self._theme_toplevel(win)

    # --- List tab confirm/run ---

    def _get_list_inputs(self, tab):
        return (
            tab["target_var"].get(),
            tab["email_var"].get().strip(),
            tab["domain_var"].get().strip(),
            [l.strip() for l in tab["query_text"].get("1.0", "end").splitlines() if l.strip()],
        )

    def _validate_target(self, target, email, domain):
        if target == "specific" and not email:
            messagebox.showwarning("Missing Input", "Please enter a mailbox owner email address.")
            return False
        if target == "domain" and not domain:
            messagebox.showwarning("Missing Input", "Please enter a domain (e.g. marshallpublicschools.org).")
            return False
        return True

    def _confirm_delete_msgid(self):
        target, email, domain, msg_ids = self._get_list_inputs(self.msgid_tab)
        if not self._validate_target(target, email, domain):
            return
        if not msg_ids:
            messagebox.showwarning("Missing Input", "Please enter at least one Message-ID.")
            return
        plural = "message" if len(msg_ids) == 1 else "messages"
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(msg_ids)} {plural} from:\n\n    {self._target_label(target, email, domain)}\n\n"
            "This action cannot be undone. Continue?",
        ):
            self._run_list_tab(self.msgid_tab, "msgid", dry_run=False)

    def _confirm_delete_sender(self):
        target, email, domain, senders = self._get_list_inputs(self.sender_tab)
        if not self._validate_target(target, email, domain):
            return
        if not senders:
            messagebox.showwarning("Missing Input", "Please enter at least one sender email.")
            return
        plural = "sender" if len(senders) == 1 else "senders"
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete all messages from {len(senders)} {plural}:\n\n"
            + "\n".join(f"    {s}" for s in senders)
            + f"\n\nTarget: {self._target_label(target, email, domain)}\n\n"
            "This action cannot be undone. Continue?",
        ):
            self._run_list_tab(self.sender_tab, "sender", dry_run=False)

    def _run_list_tab(self, tab, mode, dry_run):
        target, email, domain, values = self._get_list_inputs(tab)
        if not self._validate_target(target, email, domain):
            return
        if not values:
            return
        tab["delete_btn"].config(state="disabled")
        tab["preview_btn"].config(state="disabled")
        thread = threading.Thread(
            target=self._worker,
            args=(tab, target, email, domain, values, mode, dry_run),
            daemon=True,
        )
        thread.start()

    # --- Properties tab confirm/run ---

    def _confirm_delete_props(self):
        refs = self.props_tab
        target = refs["target_var"].get()
        email = refs["email_var"].get().strip()
        domain = refs["domain_var"].get().strip()
        if not self._validate_target(target, email, domain):
            return
        query = self._build_props_query(refs)
        if not query:
            messagebox.showwarning("Missing Input", "Please fill in at least one search field (From, Subject, or Date).")
            return
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete all messages matching:\n\n    {query}\n\n"
            f"Target: {self._target_label(target, email, domain)}\n\n"
            "This action cannot be undone. Continue?",
        ):
            self._run_props(dry_run=False)

    def _run_props(self, dry_run):
        refs = self.props_tab
        target = refs["target_var"].get()
        email = refs["email_var"].get().strip()
        domain = refs["domain_var"].get().strip()
        if not self._validate_target(target, email, domain):
            return
        query = self._build_props_query(refs)
        if not query:
            messagebox.showwarning("Missing Input", "Please fill in at least one search field (From, Subject, or Date).")
            return
        refs["delete_btn"].config(state="disabled")
        refs["preview_btn"].config(state="disabled")
        thread = threading.Thread(
            target=self._worker,
            args=(refs, target, email, domain, [query], "query", dry_run),
            daemon=True,
        )
        thread.start()

    # --- Drive tab helpers ---

    def _on_drive_scope_change(self, refs):
        is_ou = refs["scope_var"].get() == "ou"
        for w in ("email_label", "email_entry", "email_hint"):
            refs[w].grid_remove()
        for w in ("ou_label", "ou_frame", "ou_hint"):
            refs[w].grid_remove()
        if is_ou:
            refs["ou_label"].grid(row=1, column=0, sticky="w", pady=(0, 4))
            refs["ou_frame"].grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4))
            refs["ou_hint"].grid(row=2, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=(0, 10))
            refs["fileid_radio"].config(state="disabled")
            if refs["method_var"].get() == "fileid":
                refs["method_var"].set("name")
        else:
            refs["email_label"].grid(row=1, column=0, sticky="w", pady=(0, 4))
            refs["email_entry"].grid(row=1, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4))
            refs["email_hint"].grid(row=2, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=(0, 10))
            refs["fileid_radio"].config(state="normal")

    def _on_drive_type_change(self, refs):
        refs["shared_label"].grid_remove()
        refs["shared_entry"].grid_remove()
        if refs["drive_type_var"].get() == "shared":
            refs["shared_label"].grid(row=4, column=0, sticky="w", pady=(0, 8))
            refs["shared_entry"].grid(row=4, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 8))

    def _on_drive_method_change(self, refs):
        for k in ("fileid_label", "fileid_hint", "fileid_outer",
                  "name_label", "name_entry", "name_hint", "drive_q_label", "drive_q_preview"):
            refs[k].grid_remove()
        if refs["method_var"].get() == "fileid":
            refs["fileid_label"].grid(row=6, column=0, sticky="nw", pady=(0, 4))
            refs["fileid_hint"].grid(row=7, column=0, sticky="nw", pady=(0, 4))
            refs["fileid_outer"].grid(row=6, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        else:
            refs["name_label"].grid(row=6, column=0, sticky="w", pady=(0, 4))
            refs["name_entry"].grid(row=6, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4))
            refs["name_hint"].grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 6))
            refs["drive_q_label"].grid(row=8, column=0, sticky="w", pady=(0, 4))
            refs["drive_q_preview"].grid(row=8, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(0, 4))

    def _update_drive_query(self, refs):
        name = refs["name_var"].get().strip()
        if name:
            clean = name.replace("'", "\\'")
            refs["drive_q_var"].set(f"name contains '{clean}'")
        else:
            refs["drive_q_var"].set("")

    # --- Drive find ---

    def _find_drive_files(self):
        refs = self.drive_tab
        scope = refs["scope_var"].get()
        method = refs["method_var"].get()
        drive_type = refs["drive_type_var"].get()
        shared_id = refs["shared_var"].get().strip()
        if drive_type == "shared" and not shared_id:
            messagebox.showwarning("Missing Input", "Please enter the Shared Drive ID.")
            return

        refs["find_btn"].config(state="disabled")

        if scope == "ou":
            ou_path = refs["ou_var"].get().strip()
            if not ou_path:
                messagebox.showwarning("Missing Input", "Please enter an OU path or use Browse to select one.")
                refs["find_btn"].config(state="normal")
                return
            name = refs["name_var"].get().strip()
            if not name:
                messagebox.showwarning("Missing Input", "Please enter a file name to search for.")
                refs["find_btn"].config(state="normal")
                return
            threading.Thread(
                target=self._find_drive_by_name_ou_worker,
                args=(ou_path, drive_type, shared_id, name, refs),
                daemon=True,
            ).start()
        else:
            email = refs["email_var"].get().strip()
            if not email:
                messagebox.showwarning("Missing Input", "Please enter a user email address.")
                refs["find_btn"].config(state="normal")
                return
            if method == "fileid":
                file_ids = [l.strip() for l in refs["fileid_text"].get("1.0", "end").splitlines() if l.strip()]
                if not file_ids:
                    messagebox.showwarning("Missing Input", "Please enter at least one File ID.")
                    refs["find_btn"].config(state="normal")
                    return
                threading.Thread(
                    target=self._find_drive_by_ids_worker,
                    args=(email, file_ids, refs),
                    daemon=True,
                ).start()
            else:
                name = refs["name_var"].get().strip()
                if not name:
                    messagebox.showwarning("Missing Input", "Please enter a file name to search for.")
                    refs["find_btn"].config(state="normal")
                    return
                threading.Thread(
                    target=self._find_drive_by_name_worker,
                    args=(email, drive_type, shared_id, name, refs),
                    daemon=True,
                ).start()

    def _find_drive_by_ids_worker(self, email, file_ids, refs):
        self.log(f"[FIND] Checking {len(file_ids)} file ID(s) for {email}", "preview")
        for fid in file_ids:
            cmd = ["gam", "user", email, "info", "drivefile", fid]
            self.log(">> " + " ".join(cmd), "cmd")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                for line in (result.stdout + result.stderr).splitlines():
                    if line.strip():
                        self.log("  " + line, "preview")
            except subprocess.TimeoutExpired:
                self.log(f"  TIMEOUT for file ID: {fid}", "error")
            except FileNotFoundError:
                self.log("ERROR: 'gam' not found.", "error")
                break
        self.after(0, lambda: refs["find_btn"].config(state="normal"))

    def _find_drive_by_name_worker(self, email, drive_type, shared_id, name, refs):
        clean = name.replace("'", "\\'")
        query = f"name contains '{clean}'"
        cmd = ["gam", "user", email, "print", "filelist"]
        if drive_type == "shared" and shared_id:
            cmd += ["teamdriveid", shared_id]
        cmd += ["query", query, "fields", "id,name,mimeType,size,modifiedTime", "maxfiles", "100"]

        self.log(f"[FIND] {' '.join(cmd)}", "cmd")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.stderr.strip():
                self.log("  " + result.stderr.strip(), "warning")
            stdout = result.stdout.strip()
            if not stdout:
                self.log("  No files found.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return
            rows = list(csv.DictReader(io.StringIO(stdout)))
            if not rows:
                self.log("  No files matched the search.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return
            col_map = {k.lower(): k for k in rows[0].keys()}
            name_key = col_map.get("name", "name")
            id_key = col_map.get("id", "id")
            self.log(f"  Found {len(rows)} file(s):", "preview")
            for r in rows:
                self.log(f"    {r.get(name_key, '(unknown)')}  ({r.get(id_key, '')})", "preview")
            self.after(0, lambda: self._show_drive_find_results(rows, query, refs))
        except subprocess.TimeoutExpired:
            self.log("  TIMEOUT during Find Files.", "error")
            self.after(0, lambda: refs["find_btn"].config(state="normal"))
        except FileNotFoundError:
            self.log("ERROR: 'gam' not found.", "error")
            self.after(0, lambda: refs["find_btn"].config(state="normal"))

    def _find_drive_by_name_ou_worker(self, ou_path, drive_type, shared_id, name, refs):
        clean = name.replace("'", "\\'")
        query = f"name contains '{clean}'"
        cmd = ["gam", "ou_and_children", ou_path, "print", "filelist"]
        if drive_type == "shared" and shared_id:
            cmd += ["teamdriveid", shared_id]
        cmd += ["query", query, "fields", "id,name,mimeType,size,modifiedTime,ownerEmail", "maxfiles", "500"]

        self.log(f"[FIND] OU: {ou_path}  •  {' '.join(cmd)}", "cmd")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.stderr.strip():
                self.log("  " + result.stderr.strip(), "warning")
            stdout = result.stdout.strip()
            if not stdout:
                self.log("  No files found.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return
            rows = list(csv.DictReader(io.StringIO(stdout)))
            if not rows:
                self.log("  No files matched the search.", "warning")
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return
            col_map = {k.lower(): k for k in rows[0].keys()}
            name_key = col_map.get("name", "name")
            id_key = col_map.get("id", "id")
            owner_key = col_map.get("owneremail", "")
            self.log(f"  Found {len(rows)} file(s) across OU {ou_path}:", "preview")
            for r in rows:
                owner = f"  owner: {r.get(owner_key)}" if owner_key else ""
                self.log(f"    {r.get(name_key, '(unknown)')}  ({r.get(id_key, '')}){owner}", "preview")
            self.after(0, lambda: self._show_drive_find_results(rows, query, refs))
        except subprocess.TimeoutExpired:
            self.log("  TIMEOUT during Find Files (OU scans may take longer for large OUs).", "error")
            self.after(0, lambda: refs["find_btn"].config(state="normal"))
        except FileNotFoundError:
            self.log("ERROR: 'gam' not found.", "error")
            self.after(0, lambda: refs["find_btn"].config(state="normal"))

    def _browse_drive_ous(self, refs):
        def _worker():
            try:
                cmd = ["gam", "print", "orgs", "fields", "orgUnitPath,name"]
                self.log("[OU] Fetching organizational units from domain…", "preview")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.stderr.strip():
                    self.log("  " + result.stderr.strip(), "warning")
                stdout = result.stdout.strip()
                if not stdout:
                    self.after(0, lambda: messagebox.showwarning("Browse OUs", "No organizational units returned from GAM."))
                    return
                rows = list(csv.DictReader(io.StringIO(stdout)))
                if not rows:
                    self.after(0, lambda: messagebox.showwarning("Browse OUs", "No organizational units found."))
                    return
                self.after(0, lambda: self._show_ou_picker(rows, refs))
            except subprocess.TimeoutExpired:
                self.log("  TIMEOUT while fetching OUs.", "error")
                self.after(0, lambda: messagebox.showerror("Browse OUs", "Timeout while fetching organizational units."))
            except FileNotFoundError:
                self.log("ERROR: 'gam' not found.", "error")
                self.after(0, lambda: messagebox.showerror("Browse OUs", "'gam' not found. Is GAM installed and in your PATH?"))
        threading.Thread(target=_worker, daemon=True).start()

    def _show_ou_picker(self, rows, refs):
        win = tk.Toplevel(self)
        win.title("Select Organizational Unit")
        win.geometry("520x420")
        win.minsize(380, 300)
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text="Select an OU (type to filter):").pack(anchor="w", padx=12, pady=(10, 4))
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(win, textvariable=filter_var, font=("Segoe UI", 10))
        filter_entry.pack(fill="x", padx=12, pady=(0, 6))

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        col_map = {k.lower(): k for k in rows[0].keys()}
        path_key = col_map.get("orgunitpath", "orgUnitPath")

        all_paths = sorted(set(r.get(path_key, "").strip() for r in rows if r.get(path_key, "").strip()))

        listbox = tk.Listbox(frame, font=("Segoe UI", 10), selectmode="single", activestyle="none")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=vsb.set)
        listbox.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        def _populate(paths):
            listbox.delete(0, "end")
            for p in paths:
                listbox.insert("end", p)

        _populate(all_paths)

        def _filter(*_):
            term = filter_var.get().lower()
            _populate([p for p in all_paths if term in p.lower()])

        filter_var.trace_add("write", _filter)

        def _select():
            sel = listbox.curselection()
            if sel:
                refs["ou_var"].set(listbox.get(sel[0]))
            win.destroy()

        listbox.bind("<Double-Button-1>", lambda _: _select())

        btn_row = tk.Frame(win)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Button(btn_row, text="Select", command=_select).pack(side="right")
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side="right", padx=(0, 6))

        filter_entry.focus_set()
        self._theme_toplevel(win)

    def _show_drive_find_results(self, rows, query, refs):
        refs["find_btn"].config(state="normal")
        if not rows:
            messagebox.showinfo("Find Files", "No files matched.")
            return

        win = tk.Toplevel(self)
        win.title(f"Found Files — {len(rows)} result(s)")
        win.geometry("900x460")
        win.minsize(600, 250)

        ttk.Label(win, text=f"Query: {query}", font=("Segoe UI", 9),
                  style="Hint.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(win, text=f"{len(rows)} file(s) matched  •  max 100 shown",
                  style="Hint.TLabel").pack(anchor="w", padx=12, pady=(0, 6))

        btn_row = tk.Frame(win)
        btn_row.pack(fill="x", padx=12, pady=(0, 10), side="bottom")

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        sample = rows[0]
        col_map = {k.lower(): k for k in sample.keys()}
        name_key = col_map.get("name", "")
        id_key = col_map.get("id", "")
        mime_key = col_map.get("mimetype", "")
        size_key = col_map.get("size", "")
        mod_key = col_map.get("modifiedtime", "")
        owner_key = col_map.get("owneremail", "")

        display_cols = [c for c in (name_key, owner_key, mime_key, size_key, mod_key, id_key) if c]
        if not display_cols:
            display_cols = list(sample.keys())

        tree = ttk.Treeview(frame, columns=display_cols, show="headings", selectmode="browse")
        col_widths = {"name": 240, "owneremail": 200, "mimetype": 160, "size": 70, "modifiedtime": 150, "id": 200}
        for col in display_cols:
            width = col_widths.get(col.lower(), 150)
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=60)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        for row in rows:
            tree.insert("", "end", values=[row.get(c, "") for c in display_cols])

        _drive_labels = {
            "name": "File Name", "id": "File ID", "mimetype": "MIME Type",
            "size": "Size (bytes)", "modifiedtime": "Modified Time", "owneremail": "Owner Email",
        }
        col_labels = [_drive_labels.get(c.lower(), c) or c for c in display_cols]

        def _export(fmt):
            default = "drive_results.csv" if fmt == "csv" else "drive_results.txt"
            path = filedialog.asksaveasfilename(
                parent=win,
                title="Export Results",
                initialfile=default,
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    if fmt == "csv":
                        writer = csv.writer(f)
                        writer.writerow(col_labels)
                        for row in rows:
                            writer.writerow([row.get(c, "") for c in display_cols])
                    else:
                        col_w = [max(len(col_labels[i]), max((len(str(row.get(display_cols[i], ""))) for row in rows), default=0)) for i in range(len(display_cols))]
                        header = "  ".join(col_labels[i].ljust(col_w[i]) for i in range(len(col_labels)))
                        sep = "  ".join("-" * w for w in col_w)
                        f.write(f"Query: {query}\n{header}\n{sep}\n")
                        for row in rows:
                            f.write("  ".join(str(row.get(display_cols[i], "")).ljust(col_w[i]) for i in range(len(display_cols))) + "\n")
                messagebox.showinfo("Export", f"Saved {len(rows)} row(s) to:\n{path}", parent=win)
            except OSError as e:
                messagebox.showerror("Export Failed", str(e), parent=win)

        ttk.Button(btn_row, text="Export .csv", command=lambda: _export("csv")).pack(side="left")
        ttk.Button(btn_row, text="Export .txt", command=lambda: _export("txt")).pack(side="left", padx=(6, 0))
        ttk.Button(btn_row, text="Close", command=win.destroy).pack(side="right")
        self._theme_toplevel(win)

    # --- Drive delete ---

    def _confirm_delete_drive(self):
        refs = self.drive_tab
        scope = refs["scope_var"].get()
        method = refs["method_var"].get()
        drive_type = refs["drive_type_var"].get()
        shared_id = refs["shared_var"].get().strip()
        purge = refs["purge_var"].get()

        if drive_type == "shared" and not shared_id:
            messagebox.showwarning("Missing Input", "Please enter the Shared Drive ID.")
            return

        drive_label = f"Shared Drive ({shared_id})" if drive_type == "shared" else "My Drive"
        action = "Permanently delete" if purge else "Move to trash"

        if scope == "ou":
            ou_path = refs["ou_var"].get().strip()
            if not ou_path:
                messagebox.showwarning("Missing Input", "Please enter an OU path or use Browse to select one.")
                return
            name = refs["name_var"].get().strip()
            if not name:
                messagebox.showwarning("Missing Input", "Please enter a file name to search for.")
                return
            action_lower = action.lower()
            if messagebox.askyesno(
                "Confirm Delete",
                f"Find and {action_lower} all files matching:\n\n"
                f"    name contains '{name}'\n\n"
                f"across all users in OU:  {ou_path}\n"
                f"Drive:  {drive_label}\n\n"
                "This action cannot be undone. Continue?",
            ):
                self._run_delete_drive(refs, "name", "ou", ou_path, drive_type, shared_id, [name], purge)
        elif method == "fileid":
            email = refs["email_var"].get().strip()
            if not email:
                messagebox.showwarning("Missing Input", "Please enter a user email address.")
                return
            file_ids = [l.strip() for l in refs["fileid_text"].get("1.0", "end").splitlines() if l.strip()]
            if not file_ids:
                messagebox.showwarning("Missing Input", "Please enter at least one File ID.")
                return
            plural = "file" if len(file_ids) == 1 else "files"
            preview = "\n".join(f"    {fid}" for fid in file_ids[:10])
            if len(file_ids) > 10:
                preview += f"\n    ... and {len(file_ids) - 10} more"
            if messagebox.askyesno(
                "Confirm Delete",
                f"{action} {len(file_ids)} {plural} from {email} / {drive_label}:\n\n"
                f"{preview}\n\nThis action cannot be undone. Continue?",
            ):
                self._run_delete_drive(refs, "fileid", "user", email, drive_type, shared_id, file_ids, purge)
        else:
            email = refs["email_var"].get().strip()
            if not email:
                messagebox.showwarning("Missing Input", "Please enter a user email address.")
                return
            name = refs["name_var"].get().strip()
            if not name:
                messagebox.showwarning("Missing Input", "Please enter a file name to search for.")
                return
            action_lower = action.lower()
            if messagebox.askyesno(
                "Confirm Delete",
                f"Find and {action_lower} all files matching:\n\n"
                f"    name contains '{name}'\n\n"
                f"in {email} / {drive_label}\n\n"
                "This action cannot be undone. Continue?",
            ):
                self._run_delete_drive(refs, "name", "user", email, drive_type, shared_id, [name], purge)

    def _run_delete_drive(self, refs, method, scope, target, drive_type, shared_id, values, purge):
        refs["delete_btn"].config(state="disabled")
        refs["find_btn"].config(state="disabled")
        threading.Thread(
            target=self._delete_drive_worker,
            args=(refs, method, scope, target, drive_type, shared_id, values, purge),
            daemon=True,
        ).start()

    def _delete_drive_worker(self, refs, method, scope, target, drive_type, shared_id, values, purge):
        action = "purge" if purge else "delete"
        target_label = f"OU: {target}" if scope == "ou" else f"user: {target}"
        self.log(f"[DELETE] Drive files  •  {target_label}  •  action: {action}", "info")
        success = failed = 0

        def _do_delete(owner_email, fid, label):
            nonlocal success, failed
            cmd = ["gam", "user", owner_email, action, "drivefile", fid]
            self.log(">> " + " ".join(cmd), "cmd")
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                if r.returncode == 0:
                    self.log(f"  Done: {label}", "success")
                    success += 1
                else:
                    self.log(f"  FAILED: {label} (exit {r.returncode})", "error")
                    if r.stderr.strip():
                        self.log("  " + r.stderr.strip(), "error")
                    failed += 1
            except subprocess.TimeoutExpired:
                self.log(f"  TIMEOUT: {label}", "error")
                failed += 1

        try:
            if method == "fileid":
                # Single-user file-ID mode: target is the owner's email
                for fid in values:
                    _do_delete(target, fid, fid)
            else:
                name = values[0]
                clean = name.replace("'", "\\'")
                query = f"name contains '{clean}'"

                if scope == "ou":
                    list_cmd = ["gam", "ou_and_children", target, "print", "filelist"]
                    if drive_type == "shared" and shared_id:
                        list_cmd += ["teamdriveid", shared_id]
                    list_cmd += ["query", query, "fields", "id,name,ownerEmail", "maxfiles", "1000"]
                    list_timeout = 120
                else:
                    list_cmd = ["gam", "user", target, "print", "filelist"]
                    if drive_type == "shared" and shared_id:
                        list_cmd += ["teamdriveid", shared_id]
                    list_cmd += ["query", query, "fields", "id,name", "maxfiles", "1000"]
                    list_timeout = 60

                self.log(">> " + " ".join(list_cmd), "cmd")
                result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=list_timeout, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.stderr.strip():
                    self.log("  " + result.stderr.strip(), "warning")

                rows = list(csv.DictReader(io.StringIO(result.stdout.strip()))) if result.stdout.strip() else []
                if not rows:
                    self.log("  No files found matching the query.", "warning")
                    self.after(0, lambda: [
                        refs["delete_btn"].config(state="normal"),
                        refs["find_btn"].config(state="normal"),
                    ])
                    return

                col_map = {k.lower(): k for k in rows[0].keys()}
                id_key = col_map.get("id", "id")
                name_key = col_map.get("name", "name")
                owner_key = col_map.get("owneremail", "")
                self.log(f"  Found {len(rows)} file(s) — deleting...", "preview")
                for row in rows:
                    fid = row.get(id_key, "")
                    fname = row.get(name_key, "(unknown)")
                    # For OU scope use the file's ownerEmail; for user scope use target
                    owner = row.get(owner_key, target) if (scope == "ou" and owner_key) else target
                    if fid and owner:
                        _do_delete(owner, fid, f"{fname} ({fid})")

        except subprocess.TimeoutExpired:
            self.log("  TIMEOUT during file listing.", "error")
        except FileNotFoundError:
            self.log("ERROR: 'gam' not found. Is GAM installed and in your system PATH?", "error")

        self.log(
            f"Done — {success} completed, {failed} failed.",
            "info" if failed == 0 else "warning",
        )
        self.after(0, lambda: [
            refs["delete_btn"].config(state="normal"),
            refs["find_btn"].config(state="normal"),
        ])

    # --- Classroom find/delete ---

    def _find_classrooms(self):
        refs = self.classroom_tab
        teacher = refs["teacher_var"].get().strip()
        name_filter = refs["name_var"].get().strip()
        state = refs["state_var"].get()

        refs["find_btn"].config(state="disabled")
        refs["tree"].delete(*refs["tree"].get_children())
        refs["results_label_var"].set("Searching...")

        threading.Thread(
            target=self._find_classrooms_worker,
            args=(teacher, name_filter, state, refs),
            daemon=True,
        ).start()

    def _find_classrooms_worker(self, teacher, name_filter, state, refs):
        cmd = ["gam", "print", "courses"]
        if teacher:
            cmd += ["teacher", teacher]
        if state != "all":
            cmd += ["states", state]
        cmd += ["fields", "id,name,owneremail,coursestate"]

        self.log(f"[FIND] {' '.join(cmd)}", "cmd")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.stderr.strip():
                self.log("  " + result.stderr.strip(), "warning")

            stdout = result.stdout.strip()
            if not stdout:
                self.log("  No classrooms found.", "warning")
                self.after(0, lambda: refs["results_label_var"].set("No classrooms found."))
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return

            rows = list(csv.DictReader(io.StringIO(stdout)))
            if not rows:
                self.log("  No classrooms returned.", "warning")
                self.after(0, lambda: refs["results_label_var"].set("No classrooms found."))
                self.after(0, lambda: refs["find_btn"].config(state="normal"))
                return

            col_map = {k.lower(): k for k in rows[0].keys()}
            id_key    = col_map.get("id", "id")
            name_key  = col_map.get("name", "name")
            owner_key = col_map.get("owneremail", "") or col_map.get("ownerid", "")
            state_key = col_map.get("coursestate", "") or col_map.get("state", "")

            if name_filter:
                rows = [r for r in rows if name_filter.lower() in r.get(name_key, "").lower()]

            def _populate(rows=rows):
                refs["tree"].delete(*refs["tree"].get_children())
                for row in rows:
                    refs["tree"].insert("", "end", values=(
                        row.get(id_key, ""),
                        row.get(name_key, ""),
                        row.get(owner_key, ""),
                        row.get(state_key, ""),
                    ))
                count = len(rows)
                if count:
                    refs["results_label_var"].set(
                        f"{count} classroom(s) found  •  Ctrl+click or Shift+click to multi-select"
                    )
                else:
                    refs["results_label_var"].set("No classrooms matched the name filter.")
                refs["find_btn"].config(state="normal")

            self.log(f"  Found {len(rows)} classroom(s).", "preview")
            self.after(0, _populate)

        except subprocess.TimeoutExpired:
            self.log("  TIMEOUT during Find Classrooms.", "error")
            self.after(0, lambda: refs["results_label_var"].set("Search timed out — try a more specific query."))
            self.after(0, lambda: refs["find_btn"].config(state="normal"))
        except FileNotFoundError:
            self.log("ERROR: 'gam' not found.", "error")
            self.after(0, lambda: refs["find_btn"].config(state="normal"))

    def _clear_classrooms(self):
        refs = self.classroom_tab
        refs["teacher_var"].set("")
        refs["name_var"].set("")
        refs["state_var"].set("all")
        refs["tree"].delete(*refs["tree"].get_children())
        refs["results_label_var"].set("No results — use Find Classrooms to search")

    def _confirm_delete_classrooms(self):
        refs = self.classroom_tab
        selected = refs["tree"].selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one classroom to delete.")
            return

        courses = [
            {"id": refs["tree"].item(item, "values")[0],
             "name": refs["tree"].item(item, "values")[1]}
            for item in selected
        ]

        plural = "classroom" if len(courses) == 1 else "classrooms"
        preview = "\n".join(f"    {c['name']}  ({c['id']})" for c in courses[:10])
        if len(courses) > 10:
            preview += f"\n    ... and {len(courses) - 10} more"

        if messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete {len(courses)} {plural}?\n\n{preview}\n\n"
            "All course materials and rosters will be removed. This cannot be undone. Continue?",
        ):
            refs["delete_btn"].config(state="disabled")
            refs["find_btn"].config(state="disabled")
            threading.Thread(
                target=self._delete_classrooms_worker,
                args=(courses, refs),
                daemon=True,
            ).start()

    def _delete_classrooms_worker(self, courses, refs):
        self.log(f"[DELETE] {len(courses)} classroom(s)", "info")
        success = failed = 0

        for course in courses:
            cmd = ["gam", "course", course["id"], "delete"]
            self.log(">> " + " ".join(cmd), "cmd")
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                if r.returncode == 0:
                    self.log(f"  Deleted: {course['name']} ({course['id']})", "success")
                    success += 1
                else:
                    self.log(f"  FAILED: {course['name']} ({course['id']}) (exit {r.returncode})", "error")
                    if r.stderr.strip():
                        self.log("  " + r.stderr.strip(), "error")
                    failed += 1
            except subprocess.TimeoutExpired:
                self.log(f"  TIMEOUT: {course['name']}", "error")
                failed += 1
            except FileNotFoundError:
                self.log("ERROR: 'gam' not found.", "error")
                break

        self.log(
            f"Done — {success} deleted, {failed} failed.",
            "info" if failed == 0 else "warning",
        )
        self.after(0, lambda: [
            refs["delete_btn"].config(state="normal"),
            refs["find_btn"].config(state="normal"),
        ])

    # --- Custom command ---

    _ATLAS_URL = "https://chatgpt.com/g/g-PTxxnVPMG-gam-assist-now-featuring-gam7-atlas"

    def _open_atlas(self):
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() + 8
        y = self.winfo_y()

        edge_candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            shutil.which("msedge") or "",
        ]
        for edge in edge_candidates:
            if edge and os.path.exists(edge):
                subprocess.Popen(
                    [
                        edge,
                        f"--app={self._ATLAS_URL}",
                        "--window-size=960,780",
                        f"--window-position={x},{y}",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return

        # Edge not found — fall back to default browser
        self.log("Edge not found — opening GAM Atlas in default browser.", "warning")
        webbrowser.open(self._ATLAS_URL)

    def _run_custom_command(self):
        refs = self.custom_tab
        cmd_str = refs["cmd_var"].get().strip()
        if not cmd_str:
            messagebox.showwarning("No Command", "Please enter a GAM command to run.")
            return
        try:
            cmd = shlex.split(cmd_str)
        except ValueError as e:
            messagebox.showwarning("Invalid Command", f"Could not parse command:\n{e}")
            return
        if not cmd:
            return

        history = refs["history"]
        if cmd_str not in history:
            history.insert(0, cmd_str)
            del history[20:]
            refs["history_cb"]["values"] = history

        refs["run_btn"].config(state="disabled")
        threading.Thread(
            target=self._custom_command_worker,
            args=(cmd, refs),
            daemon=True,
        ).start()

    def _custom_command_worker(self, cmd, refs):
        self.log(f"[RUN] {' '.join(cmd)}", "cmd")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self.log("  " + line, "")
            proc.wait()
            if proc.returncode == 0:
                self.log("  Command completed successfully.", "success")
            else:
                self.log(f"  Command exited with code {proc.returncode}.", "warning")
        except FileNotFoundError:
            self.log(f"ERROR: '{cmd[0]}' not found. Make sure GAM is in your PATH.", "error")
        except Exception as e:
            self.log(f"ERROR: {e}", "error")
        self.after(0, lambda: refs["run_btn"].config(state="normal"))

    # --- Shared worker ---

    def _worker(self, tab, target, email, domain, values, mode, dry_run):
        target_label = self._target_label(target, email, domain)
        prefix = "PREVIEW" if dry_run else "DELETE"
        self.log(f"[{prefix}] {len(values)} item(s) — target: {target_label}", "preview" if dry_run else "info")
        success = failed = 0

        for value in values:
            if mode == "msgid":
                query = f"rfc822msgid:{value}"
            elif mode == "sender":
                query = f"from:{value}"
            else:
                query = value

            cmd = self._build_cmd(target, email, domain, query, dry_run)
            self.log(">> " + " ".join(cmd), "cmd")
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    if line and "no messages" not in line.lower():
                        self.log("  " + line, "preview" if dry_run else "")
                proc.wait()
                if proc.returncode == 0:
                    self.log(f"  {'Preview complete' if dry_run else 'Finished'}: {value}",
                             "preview" if dry_run else "success")
                    success += 1
                elif proc.returncode == 51 and dry_run:
                    self.log(f"  Preview complete: {value}", "preview")
                    success += 1
                elif proc.returncode == 60:
                    self.log(f"  No messages found for: {value}", "warning")
                    success += 1
                else:
                    self.log(f"  FAILED: {value} (exit {proc.returncode})", "error")
                    failed += 1
            except FileNotFoundError:
                self.log("ERROR: 'gam' not found. Is GAM installed and in your system PATH?", "error")
                break

        self.log(
            f"{'Preview done' if dry_run else 'Done'} — {success} completed, {failed} failed.",
            "preview" if dry_run else "info",
        )
        self.after(0, lambda: [
            tab["delete_btn"].config(state="normal"),
            tab["preview_btn"].config(state="normal"),
        ])

    # --------------------------------------------------------------- Theme --

    _LIGHT = {
        "bg":         "#f5f5f5",
        "fg":         "#111111",
        "hint_fg":    "#888888",
        "entry_bg":   "#ffffff",
        "entry_fg":   "#111111",
        "btn_bg":     "#e1e1e1",
        "btn_active": "#d0d0d0",
        "sel_bg":     "#0078d4",
        "sel_fg":     "#ffffff",
        "tab_bg":     "#e8e8e8",
        "tab_sel":    "#f5f5f5",
        "border":     "#cccccc",
        "trough":     "#e0e0e0",
    }
    _DARK = {
        "bg":         "#2b2b2b",
        "fg":         "#e0e0e0",
        "hint_fg":    "#999999",
        "entry_bg":   "#3c3f41",
        "entry_fg":   "#bbbbbb",
        "btn_bg":     "#4c5052",
        "btn_active": "#5c6264",
        "sel_bg":     "#2f65ca",
        "sel_fg":     "#ffffff",
        "tab_bg":     "#383838",
        "tab_sel":    "#2b2b2b",
        "border":     "#555555",
        "trough":     "#3c3c3c",
    }

    def _toggle_theme(self):
        self._dark = not self._dark
        self._apply_theme()

    def _apply_theme(self):
        p = self._DARK if self._dark else self._LIGHT
        s = ttk.Style()
        s.configure(".",                 background=p["bg"],      foreground=p["fg"])
        s.configure("TFrame",            background=p["bg"])
        s.configure("TLabel",            background=p["bg"],      foreground=p["fg"])
        s.configure("Hint.TLabel",       background=p["bg"],      foreground=p["hint_fg"],
                                         font=("Segoe UI", 8))
        s.configure("TButton",           background=p["btn_bg"],  foreground=p["fg"],
                                         bordercolor=p["border"],
                                         lightcolor=p["btn_bg"],  darkcolor=p["btn_bg"],
                                         relief="flat")
        s.map("TButton",                 background=[("active",  p["btn_active"]),
                                                     ("pressed", p["btn_active"])])
        s.configure("TEntry",            fieldbackground=p["entry_bg"], foreground=p["entry_fg"],
                                         insertcolor=p["entry_fg"],     bordercolor=p["border"])
        s.map("TEntry",                  fieldbackground=[("readonly", p["bg"]),
                                                          ("disabled",  p["bg"])],
                                         foreground=[("readonly", p["hint_fg"])])
        s.configure("TRadiobutton",      background=p["bg"],  foreground=p["fg"])
        s.map("TRadiobutton",            background=[("active", p["bg"])])
        s.configure("TCheckbutton",      background=p["bg"],  foreground=p["fg"])
        s.map("TCheckbutton",            background=[("active", p["bg"])])
        s.configure("TNotebook",         background=p["bg"])
        s.configure("TNotebook.Tab",     background=p["tab_bg"], foreground=p["fg"],
                                         padding=[8, 4])
        s.map("TNotebook.Tab",           background=[("selected", p["tab_sel"]),
                                                     ("active",   p["btn_active"])],
                                         foreground=[("selected", p["fg"])])
        s.configure("Treeview",          background=p["entry_bg"], foreground=p["fg"],
                                         fieldbackground=p["entry_bg"], bordercolor=p["border"])
        s.configure("Treeview.Heading",  background=p["btn_bg"], foreground=p["fg"],
                                         relief="flat", bordercolor=p["border"])
        s.map("Treeview",                background=[("selected", p["sel_bg"])],
                                         foreground=[("selected", p["sel_fg"])])
        s.configure("TLabelframe",       background=p["bg"],     bordercolor=p["border"])
        s.configure("TLabelframe.Label", background=p["bg"],     foreground=p["fg"])
        s.configure("TScrollbar",        background=p["btn_bg"], troughcolor=p["trough"],
                                         bordercolor=p["bg"],    arrowcolor=p["fg"],
                                         darkcolor=p["btn_bg"],  lightcolor=p["btn_bg"])
        self.configure(bg=p["bg"])
        self._theme_walk(self, p)
        self._theme_btn.config(
            text="☀  Light" if self._dark else "☾  Dark",
            bg="#6b0000", fg="white",
            activebackground="#560000", activeforeground="white",
        )

    def _theme_walk(self, widget, p):
        _skip = {id(self._header), id(self.log_area.frame)}
        for child in widget.winfo_children():
            if id(child) in _skip:
                continue
            mod  = type(child).__module__
            name = type(child).__name__
            if mod == "tkinter":
                if name == "Frame":
                    child.configure(bg=p["bg"])
                elif name == "Label":
                    child.configure(bg=p["bg"], fg=p["fg"])
                elif name == "Text":
                    child.configure(
                        bg=p["entry_bg"], fg=p["entry_fg"],
                        insertbackground=p["entry_fg"],
                        highlightbackground=p["border"],
                        selectbackground=p["sel_bg"],
                        selectforeground=p["sel_fg"],
                    )
            self._theme_walk(child, p)

    def _theme_toplevel(self, win):
        p = self._DARK if self._dark else self._LIGHT
        win.configure(bg=p["bg"])
        self._theme_walk(win, p)

    # --------------------------------------------------------------- Log --

    def log(self, message: str, tag: str = ""):
        def _append():
            self.log_area.config(state="normal")
            self.log_area.insert("end", message + "\n", tag)
            self.log_area.see("end")
            self.log_area.config(state="disabled")
        self.after(0, _append)

    def _clear_log(self):
        self.log_area.config(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.config(state="disabled")


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MarshallPublicSchools.GAMGUI")
    except Exception:
        pass
    app = GAMGui()
    app.mainloop()
