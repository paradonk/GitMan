#!/usr/bin/env python3
"""Universal Git Manager GUI v2.0.0"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, os, threading, json

# ── Config ────────────────────────────────────────────────────────────────────
RECENT_FILE = os.path.expanduser('~/.gitman_recent.json')
MAX_RECENT  = 10
CO_AUTHOR   = ('Co-Authored-By: K.Paradorn <paradonk@gmail.com>\n'
               'Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>')

# ── Colours ───────────────────────────────────────────────────────────────────
BG     = '#1e1e1e'
BG2    = '#252526'
BG3    = '#2d2d2d'
BG4    = '#333333'
FG     = '#cccccc'
ACCENT = '#007acc'
GREEN  = '#4caf50'
RED    = '#d13438'
ORANGE = '#e08000'
PURPLE = '#5c4f85'
TEAL   = '#00897b'
GRAY   = '#777777'
BORDER = '#444444'


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_recent():
    try:
        with open(RECENT_FILE) as f:
            return [p for p in json.load(f) if os.path.isdir(p)]
    except Exception:
        return []

def save_recent(repos):
    try:
        with open(RECENT_FILE, 'w') as f:
            json.dump(repos[:MAX_RECENT], f, indent=2)
    except Exception:
        pass

def push_recent(path, repos):
    repos = [p for p in repos if p != path]
    repos.insert(0, path)
    return repos[:MAX_RECENT]

def is_git_repo(path):
    r = subprocess.run('git rev-parse --git-dir', shell=True,
                       cwd=path, capture_output=True)
    return r.returncode == 0

def gh_available():
    return subprocess.run('gh --version', shell=True, capture_output=True).returncode == 0

def lighten(hex_color, amt=0x18):
    h = hex_color.lstrip('#')
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'#{min(255,r+amt):02x}{min(255,g+amt):02x}{min(255,b+amt):02x}'


# ── Main App ──────────────────────────────────────────────────────────────────

class GitManager:
    def __init__(self, root: tk.Tk):
        self.root   = root
        self.repo   = tk.StringVar()
        self.recent = load_recent()
        self._branch_var      = tk.StringVar()
        self._switching_branch = False

        root.title('Git Manager')
        root.geometry('1000x700')
        root.minsize(760, 500)
        root.configure(bg=BG)

        self._build()

        start = self._find_start()
        if start:
            self._set_repo(start, refresh=True)
        else:
            self._prompt_open()

    def _find_start(self):
        cwd = os.getcwd()
        if is_git_repo(cwd):
            return cwd
        for p in self.recent:
            if is_git_repo(p):
                return p
        return None

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_menubar()
        self._build_repobar()
        self._build_toolbar()
        self._build_msgrow()
        self._build_output()
        self._build_statusbar()

    def _build_menubar(self):
        mb = tk.Menu(self.root, bg=BG3, fg=FG, activebackground=ACCENT,
                     activeforeground='white', relief='flat', bd=0)
        self.root.config(menu=mb)

        def menu(label, items):
            m = tk.Menu(mb, bg=BG3, fg=FG, activebackground=ACCENT,
                        activeforeground='white', tearoff=False)
            for item in items:
                if item == '---':
                    m.add_separator()
                else:
                    m.add_command(label=item[0], command=item[1])
            mb.add_cascade(label=label, menu=m)

        menu('File', [
            ('＋ New Repository…',     self.dlg_new_repo),
            ('⬇ Clone Repository…',   self.dlg_clone),
            ('Open Repository…',       self._prompt_open),
            '---',
            ('Git Config…',            self.dlg_config),
            '---',
            ('Exit',                   self.root.quit),
        ])

        menu('View', [
            ('Status',                 self.do_status),
            ('Diff  (unstaged)',       self.do_diff),
            ('Diff  (staged)',         self.do_diff_staged),
            '---',
            ('Log — Oneline',          self.do_log),
            ('Log — Detailed',         self.do_log_detail),
            ('Log — Graph all branches', self.do_log_graph),
            ('Reflog',                 self.do_reflog),
            '---',
            ('Show Commit…',           self.do_show_commit),
            ('Blame File…',            self.do_blame),
            '---',
            ('↻ Refresh',              self._refresh),
            ('Clear Output',           self._clear),
        ])

        menu('Stage', [
            ('Stage All',              self.do_add_all),
            ('Stage File…',            self.do_add_file),
            '---',
            ('Unstage All',            self.do_unstage_all),
            ('Discard All Changes',    self.do_discard_all),
            ('Discard File…',          self.do_discard_file),
        ])

        menu('Commit', [
            ('Commit',                 self.do_commit),
            ('Amend Last Commit',      self.do_amend),
            '---',
            ('Revert Commit…',         self.do_revert_commit),
            ('Cherry-pick…',           self.do_cherry_pick),
            '---',
            ('Reset…',                 self.dlg_reset),
            ('Clean Untracked…',       self.do_clean),
        ])

        menu('Branch', [
            ('Branch Manager…',        self.dlg_branch_manager),
            '---',
            ('New Branch…',            self.do_new_branch),
            ('Rename Branch…',         self.do_rename_branch),
            ('Delete Branch…',         self.do_delete_branch),
            '---',
            ('Merge Branch…',          self.do_merge),
            ('Rebase onto…',           self.do_rebase),
        ])

        menu('Remote', [
            ('Fetch',                  self.do_fetch),
            ('Fetch All  (--prune)',   self.do_fetch_all),
            ('Pull',                   self.do_pull),
            '---',
            ('Push',                   self.do_push),
            ('Push Tags',              self.do_push_tags),
            ('Force Push  (--force-with-lease)', self.do_push_force),
            '---',
            ('Manage Remotes…',        self.dlg_manage_remotes),
            ('🐙 Create GitHub Repo…', self.dlg_gh_create),
        ])

        menu('Stash', [
            ('Stash Changes',          self.do_stash),
            ('Stash with Message…',    self.do_stash_msg),
            '---',
            ('Pop Stash',              self.do_stash_pop),
            ('Apply Stash…',           self.do_stash_apply),
            '---',
            ('Stash Manager…',         self.dlg_stash_list),
            ('Drop Stash…',            self.do_stash_drop),
            ('Clear All Stashes',      self.do_stash_clear),
        ])

        menu('Tags', [
            ('Tag Manager…',           self.dlg_tag_manager),
            ('List Tags',              self.do_list_tags),
            '---',
            ('Create Tag…',            self.do_create_tag),
            ('Create Annotated Tag…',  self.do_create_tag_annotated),
            ('Delete Tag…',            self.do_delete_tag),
            '---',
            ('Push All Tags',          self.do_push_tags),
            ('Push Tag…',              self.do_push_tag),
        ])

    def _build_repobar(self):
        rb = tk.Frame(self.root, bg=BG2, padx=10, pady=7)
        rb.pack(fill='x')

        tk.Label(rb, text='Repo:', font=('Segoe UI', 9), bg=BG2, fg=GRAY).pack(side='left')
        self._repo_lbl = tk.Label(rb, text='—', font=('Consolas', 10, 'bold'),
                                   bg=BG2, fg=FG, anchor='w')
        self._repo_lbl.pack(side='left', padx=(6, 0), fill='x', expand=True)

        self._recent_btn = self._mk_btn(rb, '▾ Recent', self._show_recent, bg=BG4, side='right')
        self._mk_btn(rb, 'Open…',    self._prompt_open,  bg=BG4, side='right')
        self._mk_btn(rb, '⬇ Clone',  self.dlg_clone,     bg=BG4, side='right')
        self._mk_btn(rb, '＋ New',   self.dlg_new_repo,  bg=BG4, side='right')

        self._dot = tk.Label(rb, text='●', font=('Segoe UI', 11), bg=BG2, fg=GRAY)
        self._dot.pack(side='right', padx=(4, 2))
        self._status_lbl = tk.Label(rb, text='—', font=('Segoe UI', 9), bg=BG2, fg=GRAY)
        self._status_lbl.pack(side='right')

        self._branch_cb = ttk.Combobox(rb, textvariable=self._branch_var,
                                        state='readonly', width=22, font=('Consolas', 9))
        self._branch_cb.pack(side='right', padx=(0, 8))
        self._branch_cb.bind('<<ComboboxSelected>>', self._on_branch_selected)
        tk.Label(rb, text='⎇', font=('Segoe UI', 10), bg=BG2, fg=ACCENT).pack(side='right')

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=BG4, padx=8, pady=6)
        tb.pack(fill='x')

        def sep():
            tk.Frame(tb, bg=BORDER, width=1).pack(side='left', fill='y', padx=6, pady=2)

        self._mk_btn(tb, 'Status',      self.do_status)
        self._mk_btn(tb, 'Diff',        self.do_diff)
        self._mk_btn(tb, 'Staged',      self.do_diff_staged)
        self._mk_btn(tb, 'Log',         self.do_log)
        sep()
        self._mk_btn(tb, 'Fetch',       self.do_fetch,        bg=BG3)
        self._mk_btn(tb, 'Pull',        self.do_pull)
        sep()
        self._mk_btn(tb, 'Stage All',   self.do_add_all)
        self._mk_btn(tb, 'Stage File…', self.do_add_file)
        self._mk_btn(tb, 'Unstage',     self.do_unstage_all,  bg=BG3)
        sep()
        self._mk_btn(tb, 'Commit',      self.do_commit,       bg=ACCENT)
        self._mk_btn(tb, 'Push',        self.do_push)
        self._mk_btn(tb, '⚡ Quick',    self.do_quick,        bg=PURPLE)
        sep()
        self._mk_btn(tb, 'Stash',       self.do_stash,        bg=TEAL)
        self._mk_btn(tb, 'Pop',         self.do_stash_pop,    bg=TEAL)
        sep()
        self._mk_btn(tb, 'Branch…',     self.dlg_branch_manager, bg=BG3)
        self._mk_btn(tb, '↻',           self._refresh,        side='right')

    def _build_msgrow(self):
        mr = tk.Frame(self.root, bg=BG2, padx=10, pady=6)
        mr.pack(fill='x')

        tk.Label(mr, text='Message:', font=('Segoe UI', 9), bg=BG2, fg=GRAY).pack(side='left')
        self._msg   = tk.StringVar()
        self._entry = tk.Entry(mr, textvariable=self._msg, font=('Consolas', 10),
                                bg='#3c3c3c', fg=FG, insertbackground=FG, relief='flat',
                                highlightthickness=1, highlightcolor=ACCENT,
                                highlightbackground=BORDER)
        self._entry.pack(side='left', fill='x', expand=True, padx=(8, 8))
        self._entry.bind('<Return>', lambda _: self.do_quick())

        self._amend_var = tk.BooleanVar()
        tk.Checkbutton(mr, text='Amend', variable=self._amend_var,
                       bg=BG2, fg=FG, selectcolor=BG3, activebackground=BG2,
                       activeforeground=FG, font=('Segoe UI', 9),
                       cursor='hand2').pack(side='left', padx=(0, 6))

    def _build_output(self):
        ow = tk.Frame(self.root, bg=BG, padx=8, pady=4)
        ow.pack(fill='both', expand=True)

        bar2 = tk.Frame(ow, bg=BG)
        bar2.pack(fill='x', pady=(2, 3))
        tk.Label(bar2, text='Output', font=('Segoe UI', 9), bg=BG, fg=GRAY).pack(side='left')
        self._mk_btn(bar2, 'Clear', self._clear, bg=BG3, side='right', pady=2)

        self._out = tk.Text(ow, bg='#181818', fg=FG, font=('Consolas', 10),
                             relief='flat', wrap='word', state='disabled',
                             selectbackground='#264f78', insertbackground=FG,
                             highlightthickness=1, highlightbackground=BORDER)
        sb = ttk.Scrollbar(ow, orient='vertical', command=self._out.yview)
        self._out.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._out.pack(fill='both', expand=True)

        self._out.tag_config('cmd',  foreground=ACCENT)
        self._out.tag_config('ok',   foreground=GREEN)
        self._out.tag_config('err',  foreground=RED)
        self._out.tag_config('info', foreground=ORANGE)
        self._out.tag_config('head', foreground=ACCENT, font=('Consolas', 10, 'bold'))
        self._out.tag_config('dim',  foreground=GRAY)

    def _build_statusbar(self):
        self._statusbar = tk.Label(self.root, text='', bg=BG2, fg=GRAY,
                                    font=('Segoe UI', 8), anchor='w', padx=8)
        self._statusbar.pack(fill='x', side='bottom')

    # ── Widget factory ────────────────────────────────────────────────────────

    def _mk_btn(self, parent, text, cmd, bg=BG3, side='left', pady=5):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=FG,
                      activebackground=lighten(bg), activeforeground='white',
                      relief='flat', bd=0, padx=10, pady=pady,
                      font=('Segoe UI', 9), cursor='hand2')
        b.pack(side=side, padx=3)
        b.bind('<Enter>', lambda e, b=b, c=bg: b.config(bg=lighten(c)))
        b.bind('<Leave>', lambda e, b=b, c=bg: b.config(bg=c))
        return b

    # ── Dialog helpers ────────────────────────────────────────────────────────

    def _make_dialog(self, title, width=440, height=300):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - width)  // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        dlg.geometry(f'{width}x{height}+{x}+{y}')
        return dlg

    def _dlg_label(self, parent, text, fg=GRAY):
        tk.Label(parent, text=text, bg=BG, fg=fg,
                 font=('Segoe UI', 9), anchor='w').pack(fill='x', pady=(6, 2))

    def _dlg_entry(self, parent, var):
        e = tk.Entry(parent, textvariable=var, font=('Consolas', 10),
                     bg='#3c3c3c', fg=FG, insertbackground=FG, relief='flat',
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER)
        e.pack(fill='x', ipady=4)
        return e

    def _dlg_buttons(self, parent, ok_text, ok_cmd, cancel_cmd):
        bf = tk.Frame(parent, bg=BG)
        bf.pack(fill='x', pady=(16, 0))
        self._mk_btn(bf, 'Cancel', cancel_cmd, bg=BG4, side='right')
        self._mk_btn(bf, ok_text,  ok_cmd,     bg=ACCENT, side='right')

    def _ask(self, title, prompt, initial=''):
        """Single-line input dialog; returns string or None if cancelled."""
        dlg = self._make_dialog(title, 420, 148)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)
        self._dlg_label(body, prompt)
        var = tk.StringVar(value=initial)
        entry = self._dlg_entry(body, var)
        result = [None]
        def ok():
            result[0] = var.get().strip()
            dlg.destroy()
        entry.bind('<Return>', lambda _: ok())
        self._dlg_buttons(body, 'OK', ok, dlg.destroy)
        entry.focus_set()
        dlg.wait_window()
        return result[0]

    # ── New Repository ────────────────────────────────────────────────────────

    def dlg_new_repo(self):
        dlg = self._make_dialog('New Repository', 460, 310)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='New Repository', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        folder_var = tk.StringVar()
        self._dlg_label(body, 'Parent folder')
        fr = tk.Frame(body, bg=BG)
        fr.pack(fill='x')
        tk.Entry(fr, textvariable=folder_var, font=('Consolas', 10),
                 bg='#3c3c3c', fg=FG, insertbackground=FG, relief='flat',
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER).pack(side='left', fill='x', expand=True, ipady=4)
        def browse_folder():
            p = filedialog.askdirectory(title='Choose parent folder')
            if p:
                folder_var.set(p)
                if not name_var.get():
                    name_var.set(os.path.basename(p))
        self._mk_btn(fr, 'Browse…', browse_folder, bg=BG4, pady=4)

        name_var = tk.StringVar()
        self._dlg_label(body, 'Repository name')
        self._dlg_entry(body, name_var)

        readme_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text='Create README.md', variable=readme_var,
                       bg=BG, fg=FG, selectcolor=BG3, activebackground=BG,
                       activeforeground=FG, font=('Segoe UI', 9),
                       cursor='hand2').pack(anchor='w', pady=(8, 0))

        def create():
            folder = folder_var.get().strip()
            name   = name_var.get().strip()
            if not folder or not name:
                return
            path = os.path.join(folder, name)
            dlg.destroy()
            def w():
                self._section(f'New Repo: {name}')
                os.makedirs(path, exist_ok=True)
                r = subprocess.run(['git', 'init', '-b', 'main', path],
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr)
                if r.returncode != 0:
                    return
                if readme_var.get():
                    with open(os.path.join(path, 'README.md'), 'w') as f:
                        f.write(f'# {name}\n')
                    subprocess.run(['git', 'add', 'README.md'], cwd=path)
                    subprocess.run(['git', 'commit', '-m',
                                    f'Initial commit\n\n{CO_AUTHOR}'], cwd=path)
                self._write(f'✓ Repository created: {path}\n', 'ok')
                self.root.after(0, self._set_repo, path, True)
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Create', create, dlg.destroy)

    # ── Clone ─────────────────────────────────────────────────────────────────

    def dlg_clone(self):
        dlg = self._make_dialog('Clone Repository', 460, 240)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Clone Repository', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        url_var = tk.StringVar()
        self._dlg_label(body, 'Repository URL')
        self._dlg_entry(body, url_var)

        dest_var = tk.StringVar(value=os.path.expanduser('~'))
        self._dlg_label(body, 'Destination folder')
        dr = tk.Frame(body, bg=BG)
        dr.pack(fill='x')
        tk.Entry(dr, textvariable=dest_var, font=('Consolas', 10),
                 bg='#3c3c3c', fg=FG, insertbackground=FG, relief='flat',
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER).pack(side='left', fill='x', expand=True, ipady=4)
        def browse_dest():
            p = filedialog.askdirectory(title='Destination folder')
            if p:
                dest_var.set(p)
        self._mk_btn(dr, 'Browse…', browse_dest, bg=BG4, pady=4)

        def clone():
            url  = url_var.get().strip()
            dest = dest_var.get().strip()
            if not url or not dest:
                return
            dlg.destroy()
            def w():
                self._section('Clone')
                self._write(f'$ git clone {url}\n', 'cmd')
                r = subprocess.run(['git', 'clone', url], cwd=dest,
                                   capture_output=True, text=True)
                if r.stdout:
                    self._write(r.stdout)
                if r.stderr:
                    self._write(r.stderr, 'dim' if r.returncode == 0 else 'err')
                if r.returncode == 0:
                    name = url.rstrip('/').split('/')[-1]
                    if name.endswith('.git'):
                        name = name[:-4]
                    cloned = os.path.join(dest, name)
                    self._write(f'✓ Cloned to: {cloned}\n', 'ok')
                    if os.path.isdir(cloned):
                        self.root.after(0, self._set_repo, cloned, True)
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Clone', clone, dlg.destroy)

    # ── Git Config ────────────────────────────────────────────────────────────

    def dlg_config(self):
        def get_cfg(key):
            r = subprocess.run(['git', 'config', '--global', key],
                               capture_output=True, text=True)
            return r.stdout.strip()

        dlg = self._make_dialog('Git Config', 420, 220)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Global Git Config', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        name_var = tk.StringVar(value=get_cfg('user.name'))
        self._dlg_label(body, 'user.name')
        self._dlg_entry(body, name_var)

        email_var = tk.StringVar(value=get_cfg('user.email'))
        self._dlg_label(body, 'user.email')
        self._dlg_entry(body, email_var)

        def save():
            dlg.destroy()
            def w():
                self._section('Git Config')
                for key, val in [('user.name', name_var.get().strip()),
                                  ('user.email', email_var.get().strip())]:
                    if val:
                        r = subprocess.run(['git', 'config', '--global', key, val],
                                           capture_output=True, text=True)
                        self._write(f'  {key} = {val}\n',
                                    'ok' if r.returncode == 0 else 'err')
                self._write('✓ Config saved\n', 'ok')
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Save', save, dlg.destroy)

    # ── Manage Remotes ────────────────────────────────────────────────────────

    def dlg_manage_remotes(self):
        if not self.repo.get():
            return
        repo = self.repo.get()
        existing = subprocess.run('git remote -v', shell=True, cwd=repo,
                                   capture_output=True, text=True).stdout.strip()

        dlg = self._make_dialog('Manage Remotes', 500, 300)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Remotes', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 8))

        txt = tk.Text(body, bg='#181818', fg=FG, font=('Consolas', 9),
                      height=4, relief='flat', state='normal')
        txt.insert('1.0', existing or '  (no remotes)')
        txt.config(state='disabled')
        txt.pack(fill='x', pady=(0, 4))

        name_var = tk.StringVar(value='origin')
        self._dlg_label(body, 'Remote name')
        self._dlg_entry(body, name_var)

        url_var = tk.StringVar()
        self._dlg_label(body, 'URL')
        self._dlg_entry(body, url_var)

        def add():
            name = name_var.get().strip()
            url  = url_var.get().strip()
            if not url:
                return
            dlg.destroy()
            def w():
                self._section('Set Remote')
                subprocess.run(f'git remote remove {name}', shell=True,
                               cwd=repo, capture_output=True)
                r = subprocess.run(['git', 'remote', 'add', name, url],
                                   cwd=repo, capture_output=True, text=True)
                self._write(f'✓ Remote "{name}" → {url}\n' if r.returncode == 0 else r.stderr,
                            'ok' if r.returncode == 0 else 'err')
            threading.Thread(target=w, daemon=True).start()

        def remove():
            name = name_var.get().strip()
            if not name:
                return
            dlg.destroy()
            def w():
                self._section('Remove Remote')
                r = subprocess.run(['git', 'remote', 'remove', name],
                                   cwd=repo, capture_output=True, text=True)
                self._write(f'✓ Removed "{name}"\n' if r.returncode == 0 else r.stderr,
                            'ok' if r.returncode == 0 else 'err')
            threading.Thread(target=w, daemon=True).start()

        bf = tk.Frame(body, bg=BG)
        bf.pack(fill='x', pady=(8, 0))
        self._mk_btn(bf, 'Cancel',     dlg.destroy, bg=BG4,  side='right')
        self._mk_btn(bf, 'Set Remote', add,         bg=ACCENT, side='right')
        self._mk_btn(bf, 'Remove',     remove,      bg=RED,   side='right')

    # Keep original alias
    def dlg_add_remote(self):
        self.dlg_manage_remotes()

    # ── Create GitHub Repo ────────────────────────────────────────────────────

    def dlg_gh_create(self):
        if not self.repo.get():
            self._write('\n  ✗ No repository open\n', 'err'); return
        if not gh_available():
            self._write('\n  ✗ GitHub CLI (gh) not found — https://cli.github.com\n', 'err'); return

        dlg = self._make_dialog('Create GitHub Repository', 460, 310)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Create on GitHub', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        name_var = tk.StringVar(value=os.path.basename(self.repo.get()))
        self._dlg_label(body, 'Repository name')
        self._dlg_entry(body, name_var)

        desc_var = tk.StringVar()
        self._dlg_label(body, 'Description  (optional)')
        self._dlg_entry(body, desc_var)

        vis_var = tk.StringVar(value='private')
        vf = tk.Frame(body, bg=BG)
        vf.pack(anchor='w', pady=(10, 0))
        for val, lbl in [('public', 'Public'), ('private', 'Private')]:
            tk.Radiobutton(vf, text=lbl, variable=vis_var, value=val,
                           bg=BG, fg=FG, selectcolor=BG3, activebackground=BG,
                           activeforeground=FG, font=('Segoe UI', 9),
                           cursor='hand2').pack(side='left', padx=(0, 12))

        push_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text='Push current branch after creating',
                       variable=push_var, bg=BG, fg=FG, selectcolor=BG3,
                       activebackground=BG, activeforeground=FG,
                       font=('Segoe UI', 9), cursor='hand2').pack(anchor='w', pady=(8, 0))

        def create():
            name = name_var.get().strip()
            if not name:
                return
            dlg.destroy()
            def w():
                self._section(f'Create GitHub: {name}')
                cmd = ['gh', 'repo', 'create', name, f'--{vis_var.get()}',
                       '--source', self.repo.get(), '--remote', 'origin']
                if desc_var.get().strip():
                    cmd += ['--description', desc_var.get().strip()]
                if push_var.get():
                    cmd.append('--push')
                self._write('$ ' + ' '.join(cmd) + '\n', 'cmd')
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.stdout: self._write(r.stdout)
                if r.stderr: self._write(r.stderr, 'err' if r.returncode != 0 else 'dim')
                if r.returncode == 0:
                    self._write(f'✓ GitHub repo "{name}" created\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Create', create, dlg.destroy)

    # ── Branch Manager ────────────────────────────────────────────────────────

    def dlg_branch_manager(self):
        if not self.repo.get():
            return
        repo = self.repo.get()

        dlg = self._make_dialog('Branch Manager', 560, 420)
        dlg.resizable(True, True)
        body = tk.Frame(dlg, bg=BG, padx=12, pady=12)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Branch Manager', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 8))

        nb = ttk.Notebook(body)
        nb.pack(fill='both', expand=True)

        def make_lb_frame():
            f = tk.Frame(nb, bg='#181818')
            lb = tk.Listbox(f, bg='#181818', fg=FG, font=('Consolas', 10),
                            selectbackground=ACCENT, relief='flat', bd=0,
                            highlightthickness=0, activestyle='none')
            sb = ttk.Scrollbar(f, orient='vertical', command=lb.yview)
            lb.config(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
            lb.pack(fill='both', expand=True)
            return f, lb

        local_frame,  local_lb  = make_lb_frame()
        remote_frame, remote_lb = make_lb_frame()
        nb.add(local_frame,  text=' Local  ')
        nb.add(remote_frame, text=' Remote ')

        def reload():
            local_lb.delete(0, 'end')
            raw = subprocess.run('git branch', shell=True, cwd=repo,
                                  capture_output=True, text=True).stdout
            for line in raw.splitlines():
                name = line.strip().lstrip('* ')
                is_cur = line.startswith('*')
                local_lb.insert('end', f'▶  {name}' if is_cur else f'   {name}')
                if is_cur:
                    local_lb.itemconfig('end', fg=GREEN)

            remote_lb.delete(0, 'end')
            raw2 = subprocess.run('git branch -r', shell=True, cwd=repo,
                                   capture_output=True, text=True).stdout
            for line in raw2.splitlines():
                name = line.strip()
                if '-> ' not in name:
                    remote_lb.insert('end', f'   {name}')

        reload()

        def sel_local():
            s = local_lb.curselection()
            return local_lb.get(s[0]).strip().lstrip('▶').strip() if s else None

        def sel_remote():
            s = remote_lb.curselection()
            return remote_lb.get(s[0]).strip() if s else None

        def switch():
            name = sel_local()
            if not name: return
            dlg.destroy()
            def w():
                self._section(f'Switch: {name}')
                r = subprocess.run(['git', 'switch', name], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                if r.returncode == 0:
                    self._write(f'✓ Switched to {name}\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def track_remote():
            name = sel_remote()
            if not name: return
            local_name = name.split('/', 1)[-1] if '/' in name else name
            dlg.destroy()
            def w():
                self._section(f'Track Remote: {name}')
                r = subprocess.run(['git', 'checkout', '-b', local_name, '--track', name],
                                   cwd=repo, capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def new():
            name = self._ask('New Branch', 'Branch name:')
            if not name: return
            switch_now = messagebox.askyesno('Switch?', f'Switch to "{name}" immediately?',
                                              parent=dlg)
            dlg.destroy()
            def w():
                self._section(f'New Branch: {name}')
                cmd = ['git', 'switch', '-c', name] if switch_now else ['git', 'branch', name]
                r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                if r.returncode == 0:
                    self._write(f'✓ Branch "{name}" created\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def rename():
            old = sel_local()
            if not old: return
            new_name = self._ask('Rename Branch', f'New name for "{old}":', initial=old)
            if not new_name or new_name == old: return
            dlg.destroy()
            def w():
                self._section(f'Rename: {old} → {new_name}')
                r = subprocess.run(['git', 'branch', '-m', old, new_name],
                                   cwd=repo, capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                if r.returncode == 0:
                    self._write(f'✓ Renamed to "{new_name}"\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def delete():
            name = sel_local()
            if not name: return
            if not messagebox.askyesno('Delete Branch', f'Delete branch "{name}"?', parent=dlg):
                return
            force = messagebox.askyesno('Force?', 'Force delete (-D) even if unmerged?', parent=dlg)
            dlg.destroy()
            def w():
                self._section(f'Delete Branch: {name}')
                r = subprocess.run(['git', 'branch', '-D' if force else '-d', name],
                                   cwd=repo, capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def merge():
            name = sel_local()
            if not name: return
            dlg.destroy()
            def w():
                self._section(f'Merge: {name}')
                r = subprocess.run(['git', 'merge', name], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def rebase():
            name = sel_local()
            if not name: return
            dlg.destroy()
            def w():
                self._section(f'Rebase onto: {name}')
                r = subprocess.run(['git', 'rebase', name], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        bf = tk.Frame(body, bg=BG)
        bf.pack(fill='x', pady=(8, 0))
        self._mk_btn(bf, 'Switch',        switch,       bg=ACCENT)
        self._mk_btn(bf, 'New…',          new,          bg=GREEN)
        self._mk_btn(bf, 'Rename…',       rename,       bg=BG4)
        self._mk_btn(bf, 'Delete',        delete,       bg=RED)
        self._mk_btn(bf, 'Merge in',      merge,        bg=TEAL)
        self._mk_btn(bf, 'Rebase on',     rebase,       bg=ORANGE)
        self._mk_btn(bf, 'Track Remote',  track_remote, bg=BG4)

    # ── Stash Manager ─────────────────────────────────────────────────────────

    def dlg_stash_list(self):
        if not self.repo.get():
            return
        repo = self.repo.get()

        dlg = self._make_dialog('Stash Manager', 520, 320)
        dlg.resizable(True, True)
        body = tk.Frame(dlg, bg=BG, padx=12, pady=12)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Stash List', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 8))

        lf = tk.Frame(body, bg='#181818')
        lf.pack(fill='both', expand=True)
        lb = tk.Listbox(lf, bg='#181818', fg=FG, font=('Consolas', 10),
                        selectbackground=ACCENT, relief='flat', bd=0,
                        highlightthickness=0, activestyle='none')
        sb2 = ttk.Scrollbar(lf, orient='vertical', command=lb.yview)
        lb.config(yscrollcommand=sb2.set)
        sb2.pack(side='right', fill='y')
        lb.pack(fill='both', expand=True)

        def reload():
            lb.delete(0, 'end')
            r = subprocess.run('git stash list', shell=True, cwd=repo,
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                lb.insert('end', line)
            if not r.stdout.strip():
                lb.insert('end', '  (no stashes)')

        reload()

        def get_ref():
            s = lb.curselection()
            if not s: return None
            line = lb.get(s[0])
            return line.split(':')[0] if ':' in line else None

        def pop():
            ref = get_ref()
            if not ref: return
            dlg.destroy()
            def w():
                self._section(f'Stash Pop: {ref}')
                r = subprocess.run(['git', 'stash', 'pop', ref], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def apply():
            ref = get_ref()
            if not ref: return
            dlg.destroy()
            def w():
                self._section(f'Stash Apply: {ref}')
                r = subprocess.run(['git', 'stash', 'apply', ref], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        def show():
            ref = get_ref()
            if not ref: return
            def w():
                self._section(f'Stash Show: {ref}')
                r = subprocess.run(['git', 'stash', 'show', '-p', ref], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr)
            threading.Thread(target=w, daemon=True).start()

        def drop():
            ref = get_ref()
            if not ref: return
            if not messagebox.askyesno('Drop', f'Drop {ref}?', parent=dlg):
                return
            def w():
                self._section(f'Stash Drop: {ref}')
                r = subprocess.run(['git', 'stash', 'drop', ref], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self.root.after(0, reload)
            threading.Thread(target=w, daemon=True).start()

        bf = tk.Frame(body, bg=BG)
        bf.pack(fill='x', pady=(8, 0))
        self._mk_btn(bf, 'Pop',   pop,   bg=ACCENT)
        self._mk_btn(bf, 'Apply', apply, bg=TEAL)
        self._mk_btn(bf, 'Show',  show,  bg=BG4)
        self._mk_btn(bf, 'Drop',  drop,  bg=RED)

    # ── Tag Manager ───────────────────────────────────────────────────────────

    def dlg_tag_manager(self):
        if not self.repo.get():
            return
        repo = self.repo.get()

        dlg = self._make_dialog('Tag Manager', 520, 360)
        dlg.resizable(True, True)
        body = tk.Frame(dlg, bg=BG, padx=12, pady=12)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Tags', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 8))

        lf = tk.Frame(body, bg='#181818')
        lf.pack(fill='both', expand=True)
        lb = tk.Listbox(lf, bg='#181818', fg=FG, font=('Consolas', 10),
                        selectbackground=ACCENT, relief='flat', bd=0,
                        highlightthickness=0, activestyle='none')
        sb2 = ttk.Scrollbar(lf, orient='vertical', command=lb.yview)
        lb.config(yscrollcommand=sb2.set)
        sb2.pack(side='right', fill='y')
        lb.pack(fill='both', expand=True)

        def reload():
            lb.delete(0, 'end')
            r = subprocess.run('git tag -l --sort=-version:refname', shell=True,
                               cwd=repo, capture_output=True, text=True)
            for line in r.stdout.splitlines():
                lb.insert('end', f'  {line}')
            if not r.stdout.strip():
                lb.insert('end', '  (no tags)')

        reload()

        def get_tag():
            s = lb.curselection()
            return lb.get(s[0]).strip() if s else None

        def show():
            tag = get_tag()
            if not tag: return
            def w():
                self._section(f'Tag: {tag}')
                r = subprocess.run(['git', 'show', '--stat', tag], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout[:6000])
            threading.Thread(target=w, daemon=True).start()

        def create():
            name = self._ask('Create Tag', 'Tag name (e.g. v1.0.0):')
            if not name: return
            def w():
                self._section(f'Create Tag: {name}')
                r = subprocess.run(['git', 'tag', name], cwd=repo,
                                   capture_output=True, text=True)
                self._write(f'✓ Tag "{name}" created\n' if r.returncode == 0 else r.stderr,
                            'ok' if r.returncode == 0 else 'err')
                self.root.after(0, reload)
            threading.Thread(target=w, daemon=True).start()

        def create_ann():
            name = self._ask('Annotated Tag', 'Tag name:')
            if not name: return
            msg = self._ask('Annotated Tag', 'Tag message:')
            if not msg: return
            def w():
                self._section(f'Create Annotated Tag: {name}')
                r = subprocess.run(['git', 'tag', '-a', name, '-m', msg], cwd=repo,
                                   capture_output=True, text=True)
                self._write(f'✓ Annotated tag "{name}" created\n' if r.returncode == 0 else r.stderr,
                            'ok' if r.returncode == 0 else 'err')
                self.root.after(0, reload)
            threading.Thread(target=w, daemon=True).start()

        def delete():
            tag = get_tag()
            if not tag: return
            if not messagebox.askyesno('Delete Tag', f'Delete tag "{tag}"?', parent=dlg):
                return
            def w():
                self._section(f'Delete Tag: {tag}')
                r = subprocess.run(['git', 'tag', '-d', tag], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                self.root.after(0, reload)
            threading.Thread(target=w, daemon=True).start()

        def push():
            tag = get_tag()
            if not tag: return
            def w():
                self._section(f'Push Tag: {tag}')
                r = subprocess.run(['git', 'push', 'origin', tag], cwd=repo,
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            threading.Thread(target=w, daemon=True).start()

        bf = tk.Frame(body, bg=BG)
        bf.pack(fill='x', pady=(8, 0))
        self._mk_btn(bf, 'Show',       show,       bg=BG4)
        self._mk_btn(bf, 'Create',     create,     bg=GREEN)
        self._mk_btn(bf, 'Annotated…', create_ann, bg=TEAL)
        self._mk_btn(bf, 'Delete',     delete,     bg=RED)
        self._mk_btn(bf, 'Push',       push,       bg=ACCENT)

    # ── Reset dialog ──────────────────────────────────────────────────────────

    def dlg_reset(self):
        if not self.repo.get():
            return

        dlg = self._make_dialog('Reset', 400, 230)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Reset', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        ref_var = tk.StringVar(value='HEAD~1')
        self._dlg_label(body, 'Reset to (commit ref or HEAD~N)')
        self._dlg_entry(body, ref_var)

        mode_var = tk.StringVar(value='mixed')
        mf = tk.Frame(body, bg=BG)
        mf.pack(anchor='w', pady=(10, 0))
        for val, lbl in [('soft',  'Soft  — keep staged'),
                          ('mixed', 'Mixed — keep working tree'),
                          ('hard',  'Hard  — discard ALL changes')]:
            tk.Radiobutton(mf, text=lbl, variable=mode_var, value=val,
                           bg=BG, fg=FG, selectcolor=BG3, activebackground=BG,
                           activeforeground=FG, font=('Segoe UI', 9),
                           cursor='hand2').pack(anchor='w')

        def do_reset():
            ref  = ref_var.get().strip()
            mode = mode_var.get()
            if not ref: return
            if mode == 'hard' and not messagebox.askyesno(
                    'Hard Reset', 'Hard reset DISCARDS all uncommitted changes.\nContinue?',
                    parent=dlg):
                return
            dlg.destroy()
            def w():
                self._section(f'Reset ({mode}): {ref}')
                r = subprocess.run(['git', 'reset', f'--{mode}', ref],
                                   cwd=self.repo.get(), capture_output=True, text=True)
                self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
                if r.returncode == 0:
                    self._write(f'✓ Reset to {ref}\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Reset', do_reset, dlg.destroy)

    # ── Repo management ───────────────────────────────────────────────────────

    def _set_repo(self, path, refresh=False):
        path = os.path.abspath(path)
        self.repo.set(path)
        self._repo_lbl.config(text=path)
        self.root.title(f'Git Manager — {os.path.basename(path)}')
        self._statusbar.config(text=path)
        self.recent = push_recent(path, self.recent)
        save_recent(self.recent)
        if refresh:
            self._refresh()

    def _prompt_open(self):
        path = filedialog.askdirectory(title='Select repository folder')
        if not path:
            return
        if not is_git_repo(path):
            dlg = self._make_dialog('Initialise Repository?', 420, 160)
            body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
            body.pack(fill='both', expand=True)
            tk.Label(body, text='Not a git repository.',
                     bg=BG, fg=FG, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
            tk.Label(body, text=path, bg=BG, fg=GRAY,
                     font=('Consolas', 9), wraplength=380).pack(anchor='w', pady=(4, 12))
            tk.Label(body, text='Run git init here?', bg=BG, fg=FG,
                     font=('Segoe UI', 9)).pack(anchor='w')
            def do_init():
                dlg.destroy()
                def w():
                    self._section('Init')
                    r = subprocess.run(['git', 'init', '-b', 'main', path],
                                       capture_output=True, text=True)
                    self._write(r.stdout or r.stderr)
                    if r.returncode == 0:
                        self._write(f'✓ Initialised: {path}\n', 'ok')
                        self.root.after(0, self._set_repo, path, True)
                threading.Thread(target=w, daemon=True).start()
            self._dlg_buttons(body, 'Init here', do_init, dlg.destroy)
            return
        self._set_repo(path, refresh=True)
        self._clear()
        self._write(f'  Opened: {path}\n', 'ok')

    def _show_recent(self):
        if not self.recent:
            return
        menu = tk.Menu(self.root, tearoff=0, bg=BG3, fg=FG,
                       activebackground=ACCENT, activeforeground='white',
                       relief='flat', bd=0, font=('Segoe UI', 9))
        for path in self.recent:
            display = path if len(path) < 55 else '…' + path[-52:]
            menu.add_command(label=display,
                             command=lambda p=path: self._open_recent(p))
        menu.add_separator()
        menu.add_command(label='Clear Recent', command=self._clear_recent)
        try:
            x = self._recent_btn.winfo_rootx()
            y = self._recent_btn.winfo_rooty() + self._recent_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _open_recent(self, path):
        if not os.path.isdir(path):
            self._write(f'\n  ✗ Path no longer exists: {path}\n', 'err')
            self.recent = [p for p in self.recent if p != path]
            save_recent(self.recent)
            return
        if not is_git_repo(path):
            self._write(f'\n  ✗ Not a git repo: {path}\n', 'err')
            return
        self._set_repo(path, refresh=True)
        self._clear()
        self._write(f'  Opened: {path}\n', 'ok')

    def _clear_recent(self):
        self.recent = []
        save_recent(self.recent)

    # ── Output helpers ────────────────────────────────────────────────────────

    def _write(self, text, tag=None):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self._write, text, tag)
            return
        self._out.configure(state='normal')
        self._out.insert('end', text, (tag,) if tag else ())
        self._out.see('end')
        self._out.configure(state='disabled')

    def _clear(self):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, self._clear)
            return
        self._out.configure(state='normal')
        self._out.delete('1.0', 'end')
        self._out.configure(state='disabled')

    def _section(self, title):
        pad = max(0, 40 - len(title))
        self._write(f'\n── {title} {"─"*pad}\n', 'head')

    # ── Git runner ────────────────────────────────────────────────────────────

    def _has_staged(self):
        r = subprocess.run('git status --porcelain', shell=True,
                           cwd=self.repo.get(), capture_output=True, text=True)
        return any(l and l[0] not in (' ', '?') for l in r.stdout.splitlines())

    def _run(self, fn):
        if not self.repo.get():
            self._write('\n  ✗ No repository open\n', 'err')
            return
        threading.Thread(target=fn, daemon=True).start()

    def _git(self, cmd):
        repo = self.repo.get()
        self._write(f'$ {cmd}\n', 'cmd')
        r = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True)
        if r.stdout: self._write(r.stdout)
        if r.stderr: self._write(r.stderr, 'dim' if r.returncode == 0 else 'err')
        return r

    def _git_commit(self, msg, amend=False):
        repo = self.repo.get()
        full = f"{msg}\n\n{CO_AUTHOR}"
        self._write(f'$ git commit {"--amend " if amend else ""}-m "{msg}"\n', 'cmd')
        cmd = ['git', 'commit', '-m', full]
        if amend:
            cmd.insert(2, '--amend')
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if r.stdout: self._write(r.stdout)
        if r.stderr: self._write(r.stderr, 'dim' if r.returncode == 0 else 'err')
        return r

    def _get_branches(self):
        if not self.repo.get():
            return [], ''
        r = subprocess.run('git branch', shell=True, cwd=self.repo.get(),
                           capture_output=True, text=True)
        branches, current = [], ''
        for line in r.stdout.splitlines():
            name = line.strip().lstrip('* ')
            branches.append(name)
            if line.startswith('*'):
                current = name
        return branches, current

    def _refresh(self):
        repo = self.repo.get()
        if not repo:
            return
        def worker():
            b = subprocess.run('git branch --show-current', shell=True,
                               cwd=repo, capture_output=True, text=True)
            branch = b.stdout.strip() or '—'
            d = subprocess.run('git status --porcelain', shell=True,
                               cwd=repo, capture_output=True, text=True)
            dirty = bool(d.stdout.strip())
            br = subprocess.run('git branch', shell=True, cwd=repo,
                                capture_output=True, text=True)
            branches = [l.strip().lstrip('* ') for l in br.stdout.splitlines()]
            self.root.after(0, self._update_header, branch, dirty, branches)
        threading.Thread(target=worker, daemon=True).start()

    def _update_header(self, branch, dirty, branches=None):
        self._switching_branch = True
        if branches is not None:
            self._branch_cb['values'] = branches
        self._branch_var.set(branch)
        self._switching_branch = False
        c = ORANGE if dirty else GREEN
        self._dot.config(fg=c)
        self._status_lbl.config(text='Modified' if dirty else 'Clean', fg=c)

    def _on_branch_selected(self, event=None):
        if self._switching_branch:
            return
        name = self._branch_var.get()
        if not name or not self.repo.get():
            return
        def w():
            self._section(f'Switch Branch: {name}')
            r = subprocess.run(['git', 'switch', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Switched to {name}\n', 'ok')
            self._refresh()
        threading.Thread(target=w, daemon=True).start()

    # ── View / History ────────────────────────────────────────────────────────

    def do_status(self):
        def w():
            self._section('Status')
            self._git('git status')
            self._refresh()
        self._run(w)

    def do_diff(self):
        def w():
            self._section('Diff (Unstaged)')
            r = subprocess.run('git diff --stat', shell=True, cwd=self.repo.get(),
                               capture_output=True, text=True)
            if r.stdout.strip():
                self._git('git diff')
            else:
                self._write('  No unstaged changes\n', 'info')
        self._run(w)

    def do_diff_staged(self):
        def w():
            self._section('Diff (Staged)')
            r = subprocess.run('git diff --cached --stat', shell=True,
                               cwd=self.repo.get(), capture_output=True, text=True)
            if r.stdout.strip():
                self._git('git diff --cached')
            else:
                self._write('  No staged changes\n', 'info')
        self._run(w)

    def do_log(self):
        def w():
            self._section('Log  (last 30)')
            self._git('git log --oneline --graph --color=never -30')
        self._run(w)

    def do_log_detail(self):
        def w():
            self._section('Log — Detailed (last 10)')
            self._git('git log --stat -10')
        self._run(w)

    def do_log_graph(self):
        def w():
            self._section('Log — Graph (all branches)')
            self._git('git log --oneline --graph --color=never --all -50')
        self._run(w)

    def do_reflog(self):
        def w():
            self._section('Reflog')
            self._git('git reflog -20')
        self._run(w)

    def do_show_commit(self):
        ref = self._ask('Show Commit', 'Commit hash or ref:', initial='HEAD')
        if not ref:
            return
        def w():
            self._section(f'Show: {ref}')
            self._git(f'git show --stat {ref}')
        self._run(w)

    def do_blame(self):
        repo = self.repo.get()
        if not repo:
            return
        path = filedialog.askopenfilename(initialdir=repo, title='Blame — select file')
        if not path:
            return
        rel = os.path.relpath(path, repo)
        def w():
            self._section(f'Blame: {rel}')
            self._git(f'git blame "{rel}"')
        self._run(w)

    # ── Stage / Unstage ───────────────────────────────────────────────────────

    def do_add_all(self):
        def w():
            self._section('Stage All')
            self._git('git add -A')
            if self._has_staged():
                self._write('✓ All changes staged\n', 'ok')
            else:
                self._write('  Nothing to stage — working tree clean\n', 'info')
            self._refresh()
        self._run(w)

    def do_add_file(self):
        repo = self.repo.get()
        if not repo:
            return
        path = filedialog.askopenfilename(initialdir=repo, title='Stage — select file')
        if not path:
            return
        rel = os.path.relpath(path, repo)
        def w():
            self._section(f'Stage: {rel}')
            r = self._git(f'git add -- "{rel}"')
            if r.returncode == 0:
                self._write(f'✓ Staged: {rel}\n', 'ok')
            self._refresh()
        self._run(w)

    def do_unstage_all(self):
        def w():
            self._section('Unstage All')
            self._git('git restore --staged .')
            self._write('✓ All files unstaged\n', 'ok')
            self._refresh()
        self._run(w)

    def do_discard_all(self):
        if not messagebox.askyesno('Discard Changes',
                'Discard ALL unstaged changes? This cannot be undone.'):
            return
        def w():
            self._section('Discard All Changes')
            self._git('git restore .')
            self._write('✓ Working tree restored\n', 'ok')
            self._refresh()
        self._run(w)

    def do_discard_file(self):
        repo = self.repo.get()
        if not repo:
            return
        path = filedialog.askopenfilename(initialdir=repo, title='Discard — select file')
        if not path:
            return
        rel = os.path.relpath(path, repo)
        if not messagebox.askyesno('Discard File', f'Discard changes in "{rel}"?'):
            return
        def w():
            self._section(f'Discard: {rel}')
            r = self._git(f'git restore -- "{rel}"')
            if r.returncode == 0:
                self._write(f'✓ Restored: {rel}\n', 'ok')
            self._refresh()
        self._run(w)

    # ── Commit operations ─────────────────────────────────────────────────────

    def do_commit(self):
        msg   = self._msg.get().strip()
        amend = self._amend_var.get()
        if not msg and not amend:
            self._write('\n  ✗ Type a commit message first\n', 'err')
            self._entry.focus()
            return
        if amend and not msg:
            msg = subprocess.run('git log -1 --format=%s', shell=True,
                                  cwd=self.repo.get(), capture_output=True,
                                  text=True).stdout.strip()
        def w():
            self._section('Commit' + (' (amend)' if amend else ''))
            if not amend and not self._has_staged():
                self._write('  Nothing staged — run Stage All first\n', 'info')
                return
            r = self._git_commit(msg, amend=amend)
            if r.returncode == 0:
                self._write('✓ Committed\n', 'ok')
                self.root.after(0, self._msg.set, '')
                self.root.after(0, self._amend_var.set, False)
            self._refresh()
        self._run(w)

    def do_amend(self):
        if not self.repo.get():
            return
        last = subprocess.run('git log -1 --format=%s', shell=True,
                               cwd=self.repo.get(), capture_output=True,
                               text=True).stdout.strip()
        self._msg.set(last)
        self._amend_var.set(True)
        self._entry.focus()
        self._write('\n  → Edit the message above then click Commit (Amend is checked)\n', 'info')

    def do_revert_commit(self):
        ref = self._ask('Revert Commit', 'Commit hash to revert:', initial='HEAD')
        if not ref:
            return
        def w():
            self._section(f'Revert: {ref}')
            r = subprocess.run(['git', 'revert', '--no-edit', ref],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Reverted {ref}\n', 'ok')
            self._refresh()
        self._run(w)

    def do_cherry_pick(self):
        ref = self._ask('Cherry-pick', 'Commit hash to cherry-pick:')
        if not ref:
            return
        def w():
            self._section(f'Cherry-pick: {ref}')
            r = subprocess.run(['git', 'cherry-pick', ref],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Cherry-picked {ref}\n', 'ok')
            self._refresh()
        self._run(w)

    def do_clean(self):
        if not messagebox.askyesno('Clean Untracked',
                'Remove all untracked files and directories?\nThis cannot be undone.'):
            return
        def w():
            self._section('Clean Untracked')
            self._git('git clean -fd')
            self._refresh()
        self._run(w)

    # ── Remote operations ─────────────────────────────────────────────────────

    def do_fetch(self):
        def w():
            self._section('Fetch')
            self._git('git fetch')
            self._refresh()
        self._run(w)

    def do_fetch_all(self):
        def w():
            self._section('Fetch All')
            self._git('git fetch --all --prune')
            self._refresh()
        self._run(w)

    def do_pull(self):
        def w():
            self._section('Pull')
            self._git('git pull')
            self._refresh()
        self._run(w)

    def do_push(self):
        def w():
            self._section('Push')
            r = self._git('git push -u origin HEAD')
            if r.returncode == 0:
                self._write('✓ Pushed\n', 'ok')
            self._refresh()
        self._run(w)

    def do_push_force(self):
        if not messagebox.askyesno('Force Push',
                'Force push with --force-with-lease?\nThis rewrites remote history.'):
            return
        def w():
            self._section('Force Push (with-lease)')
            r = self._git('git push --force-with-lease')
            if r.returncode == 0:
                self._write('✓ Force-pushed\n', 'ok')
            self._refresh()
        self._run(w)

    def do_push_tags(self):
        def w():
            self._section('Push Tags')
            r = self._git('git push --tags')
            if r.returncode == 0:
                self._write('✓ Tags pushed\n', 'ok')
        self._run(w)

    def do_push_tag(self):
        tag = self._ask('Push Tag', 'Tag name:')
        if not tag:
            return
        def w():
            self._section(f'Push Tag: {tag}')
            r = self._git(f'git push origin {tag}')
            if r.returncode == 0:
                self._write(f'✓ Pushed tag "{tag}"\n', 'ok')
        self._run(w)

    # ── Branch operations (standalone, called from menus) ─────────────────────

    def do_new_branch(self):
        name = self._ask('New Branch', 'Branch name:')
        if not name:
            return
        def w():
            self._section(f'New Branch: {name}')
            r = subprocess.run(['git', 'switch', '-c', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Created and switched to "{name}"\n', 'ok')
            self._refresh()
        self._run(w)

    def do_rename_branch(self):
        _, current = self._get_branches()
        old = self._ask('Rename Branch', 'Current branch name:', initial=current)
        if not old:
            return
        new_name = self._ask('Rename Branch', f'New name for "{old}":')
        if not new_name or new_name == old:
            return
        def w():
            self._section(f'Rename: {old} → {new_name}')
            r = subprocess.run(['git', 'branch', '-m', old, new_name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Renamed to "{new_name}"\n', 'ok')
            self._refresh()
        self._run(w)

    def do_delete_branch(self):
        name = self._ask('Delete Branch', 'Branch name to delete:')
        if not name:
            return
        def w():
            self._section(f'Delete Branch: {name}')
            r = subprocess.run(['git', 'branch', '-d', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            if r.returncode != 0:
                self._write(r.stderr, 'err')
                self._write('  Tip: use Branch Manager → Delete with force if unmerged\n', 'info')
            else:
                self._write(f'✓ Deleted "{name}"\n', 'ok')
            self._refresh()
        self._run(w)

    def do_merge(self):
        branches, current = self._get_branches()
        opts = [b for b in branches if b != current]
        name = self._ask('Merge', f'Branch to merge into {current}:',
                         initial=opts[0] if opts else '')
        if not name:
            return
        def w():
            self._section(f'Merge: {name} → {current}')
            r = subprocess.run(['git', 'merge', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            self._refresh()
        self._run(w)

    def do_rebase(self):
        name = self._ask('Rebase', 'Rebase current branch onto:')
        if not name:
            return
        def w():
            self._section(f'Rebase onto: {name}')
            r = subprocess.run(['git', 'rebase', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            self._refresh()
        self._run(w)

    # ── Stash operations ──────────────────────────────────────────────────────

    def do_stash(self):
        def w():
            self._section('Stash')
            r = self._git('git stash push')
            if r.returncode == 0:
                self._write('✓ Changes stashed\n', 'ok')
            self._refresh()
        self._run(w)

    def do_stash_msg(self):
        msg = self._ask('Stash', 'Stash message:')
        if not msg:
            return
        def w():
            self._section('Stash')
            r = subprocess.run(['git', 'stash', 'push', '-m', msg],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            if r.returncode == 0:
                self._write(f'✓ Stashed: {msg}\n', 'ok')
            self._refresh()
        self._run(w)

    def do_stash_pop(self):
        def w():
            self._section('Stash Pop')
            r = self._git('git stash pop')
            if r.returncode == 0:
                self._write('✓ Stash applied and removed\n', 'ok')
            self._refresh()
        self._run(w)

    def do_stash_apply(self):
        ref = self._ask('Apply Stash', 'Stash ref:', initial='stash@{0}')
        if not ref:
            return
        def w():
            self._section(f'Stash Apply: {ref}')
            r = subprocess.run(['git', 'stash', 'apply', ref],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
            self._refresh()
        self._run(w)

    def do_stash_drop(self):
        ref = self._ask('Drop Stash', 'Stash ref:', initial='stash@{0}')
        if not ref:
            return
        def w():
            self._section(f'Stash Drop: {ref}')
            r = subprocess.run(['git', 'stash', 'drop', ref],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
        self._run(w)

    def do_stash_clear(self):
        if not messagebox.askyesno('Clear Stashes', 'Clear ALL stashes? Cannot be undone.'):
            return
        def w():
            self._section('Stash Clear')
            self._git('git stash clear')
            self._write('✓ All stashes cleared\n', 'ok')
        self._run(w)

    # ── Tag operations (standalone) ───────────────────────────────────────────

    def do_list_tags(self):
        def w():
            self._section('Tags')
            r = self._git('git tag -l --sort=-version:refname')
            if not r.stdout.strip():
                self._write('  (no tags)\n', 'info')
        self._run(w)

    def do_create_tag(self):
        name = self._ask('Create Tag', 'Tag name (e.g. v1.0.0):')
        if not name:
            return
        def w():
            self._section(f'Create Tag: {name}')
            r = subprocess.run(['git', 'tag', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(f'✓ Tag "{name}" created\n' if r.returncode == 0 else r.stderr,
                        'ok' if r.returncode == 0 else 'err')
        self._run(w)

    def do_create_tag_annotated(self):
        name = self._ask('Annotated Tag', 'Tag name:')
        if not name:
            return
        msg = self._ask('Annotated Tag', 'Tag message:')
        if not msg:
            return
        def w():
            self._section(f'Create Annotated Tag: {name}')
            r = subprocess.run(['git', 'tag', '-a', name, '-m', msg],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(f'✓ Annotated tag "{name}" created\n' if r.returncode == 0 else r.stderr,
                        'ok' if r.returncode == 0 else 'err')
        self._run(w)

    def do_delete_tag(self):
        name = self._ask('Delete Tag', 'Tag name:')
        if not name:
            return
        def w():
            self._section(f'Delete Tag: {name}')
            r = subprocess.run(['git', 'tag', '-d', name],
                               cwd=self.repo.get(), capture_output=True, text=True)
            self._write(r.stdout or r.stderr, 'ok' if r.returncode == 0 else 'err')
        self._run(w)

    # ── Quick ─────────────────────────────────────────────────────────────────

    def do_quick(self):
        msg = self._msg.get().strip()
        if not msg:
            self._write('\n  ✗ Type a commit message first\n', 'err')
            self._entry.focus()
            return
        def w():
            self._section('Quick: Add → Commit → Push')
            self._git('git add -A')
            if not self._has_staged():
                self._write('  Nothing to commit — working tree clean\n', 'info')
                return
            r2 = self._git_commit(msg)
            if r2.returncode != 0:
                return
            self._write('✓ Committed\n', 'ok')
            self.root.after(0, self._msg.set, '')
            r3 = self._git('git push -u origin HEAD')
            if r3.returncode == 0:
                self._write('✓ Pushed\n', 'ok')
            self._refresh()
        self._run(w)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Vertical.TScrollbar', background='#333',
                    troughcolor=BG, bordercolor=BG, arrowcolor=GRAY)
    style.configure('TNotebook', background=BG2, bordercolor=BORDER)
    style.configure('TNotebook.Tab', background=BG3, foreground=FG, padding=[10, 4])
    style.map('TNotebook.Tab',
              background=[('selected', BG)],
              foreground=[('selected', ACCENT)])
    style.configure('TCombobox', fieldbackground='#3c3c3c', background=BG3,
                    foreground=FG, arrowcolor=FG, bordercolor=BORDER)
    style.map('TCombobox',
              fieldbackground=[('readonly', '#3c3c3c')],
              foreground=[('readonly', FG)],
              selectbackground=[('readonly', ACCENT)])
    root.tk_setPalette(background=BG, foreground=FG)
    GitManager(root)
    root.mainloop()
