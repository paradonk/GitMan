#!/usr/bin/env python3
"""Universal Git Manager GUI"""

import tkinter as tk
from tkinter import ttk, filedialog
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
    r = subprocess.run('gh --version', shell=True, capture_output=True)
    return r.returncode == 0

def lighten(hex_color, amt=0x18):
    h = hex_color.lstrip('#')
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f'#{min(255,r+amt):02x}{min(255,g+amt):02x}{min(255,b+amt):02x}'


# ── Main App ──────────────────────────────────────────────────────────────────

class GitManager:
    def __init__(self, root: tk.Tk):
        self.root   = root
        self.repo   = tk.StringVar()
        self.recent = load_recent()

        root.title('Git Manager')
        root.geometry('920x640')
        root.minsize(700, 460)
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

        # ── Repo bar ──────────────────────────────────────────────────────────
        rb = tk.Frame(self.root, bg=BG2, padx=10, pady=7)
        rb.pack(fill='x')

        tk.Label(rb, text='Repo:', font=('Segoe UI', 9),
                 bg=BG2, fg=GRAY).pack(side='left')

        self._repo_lbl = tk.Label(rb, text='—', font=('Consolas', 10, 'bold'),
                                   bg=BG2, fg=FG, anchor='w')
        self._repo_lbl.pack(side='left', padx=(6, 0), fill='x', expand=True)

        self._recent_btn = self._mk_btn(rb, '▾ Recent', self._show_recent,
                                         bg=BG4, side='right')
        self._mk_btn(rb, 'Open…',   self._prompt_open,  bg=BG4, side='right')
        self._mk_btn(rb, '＋ New',   self.dlg_new_repo,  bg=BG4, side='right')

        self._dot        = tk.Label(rb, text='●', font=('Segoe UI', 11),
                                     bg=BG2, fg=GRAY)
        self._dot.pack(side='right', padx=(4, 2))
        self._status_lbl = tk.Label(rb, text='—', font=('Segoe UI', 9),
                                     bg=BG2, fg=GRAY)
        self._status_lbl.pack(side='right')
        self._branch_lbl = tk.Label(rb, text='', font=('Segoe UI', 9),
                                     bg=BG2, fg=ACCENT)
        self._branch_lbl.pack(side='right', padx=(0, 10))

        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = tk.Frame(self.root, bg=BG4, padx=8, pady=6)
        tb.pack(fill='x')

        def sep():
            tk.Frame(tb, bg=BORDER, width=1).pack(side='left', fill='y',
                                                    padx=6, pady=2)

        self._mk_btn(tb, 'Status',       self.do_status)
        self._mk_btn(tb, 'Diff',         self.do_diff)
        self._mk_btn(tb, 'Log',          self.do_log)
        self._mk_btn(tb, 'Pull',         self.do_pull)
        sep()
        self._mk_btn(tb, 'Stage All',    self.do_add_all)
        self._mk_btn(tb, 'Stage File…',  self.do_add_file)
        sep()
        self._mk_btn(tb, 'Commit',       self.do_commit,      bg=ACCENT)
        self._mk_btn(tb, 'Push',         self.do_push)
        sep()
        self._mk_btn(tb, '⚡ Quick',     self.do_quick,       bg=PURPLE)
        sep()
        self._mk_btn(tb, 'Add Remote',   self.dlg_add_remote)
        self._mk_btn(tb, '🐙 GitHub',    self.dlg_gh_create,  bg='#238636')
        self._mk_btn(tb, '↻', self._refresh, side='right')

        # ── Commit message row ────────────────────────────────────────────────
        mr = tk.Frame(self.root, bg=BG2, padx=10, pady=6)
        mr.pack(fill='x')

        tk.Label(mr, text='Message:', font=('Segoe UI', 9),
                 bg=BG2, fg=GRAY).pack(side='left')

        self._msg   = tk.StringVar()
        self._entry = tk.Entry(mr, textvariable=self._msg,
                                font=('Consolas', 10), bg='#3c3c3c', fg=FG,
                                insertbackground=FG, relief='flat',
                                highlightthickness=1, highlightcolor=ACCENT,
                                highlightbackground=BORDER)
        self._entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self._entry.bind('<Return>', lambda _: self.do_quick())

        # ── Output ────────────────────────────────────────────────────────────
        ow = tk.Frame(self.root, bg=BG, padx=8, pady=4)
        ow.pack(fill='both', expand=True)

        bar2 = tk.Frame(ow, bg=BG)
        bar2.pack(fill='x', pady=(2, 3))
        tk.Label(bar2, text='Output', font=('Segoe UI', 9),
                 bg=BG, fg=GRAY).pack(side='left')
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
        self._out.tag_config('head', foreground=ACCENT,
                              font=('Consolas', 10, 'bold'))
        self._out.tag_config('dim',  foreground=GRAY)

        # ── Status bar ────────────────────────────────────────────────────────
        self._statusbar = tk.Label(self.root, text='', bg=BG2, fg=GRAY,
                                    font=('Segoe UI', 8), anchor='w', padx=8)
        self._statusbar.pack(fill='x', side='bottom')

    # ── Widget factory ────────────────────────────────────────────────────────

    def _mk_btn(self, parent, text, cmd, bg=BG3, side='left', pady=5):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=FG, activebackground=lighten(bg),
                      activeforeground='white', relief='flat', bd=0,
                      padx=10, pady=pady, font=('Segoe UI', 9), cursor='hand2')
        b.pack(side=side, padx=3)
        b.bind('<Enter>', lambda e, b=b, c=bg: b.config(bg=lighten(c)))
        b.bind('<Leave>', lambda e, b=b, c=bg: b.config(bg=c))
        return b

    # ── Dialog helper ─────────────────────────────────────────────────────────

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

    def _dlg_entry(self, parent, var, placeholder=''):
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

    # ── New Repository dialog ─────────────────────────────────────────────────

    def dlg_new_repo(self):
        dlg = self._make_dialog('New Repository', 460, 310)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='New Repository', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        # Folder row
        folder_var = tk.StringVar()
        self._dlg_label(body, 'Parent folder')
        fr = tk.Frame(body, bg=BG)
        fr.pack(fill='x')
        tk.Entry(fr, textvariable=folder_var, font=('Consolas', 10),
                 bg='#3c3c3c', fg=FG, insertbackground=FG, relief='flat',
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER).pack(side='left', fill='x',
                                                   expand=True, ipady=4)
        def browse():
            p = filedialog.askdirectory(title='Choose parent folder')
            if p:
                folder_var.set(p)
                if not name_var.get():
                    name_var.set(os.path.basename(p))
        self._mk_btn(fr, 'Browse…', browse, bg=BG4, pady=4)

        # Repo name
        name_var = tk.StringVar()
        self._dlg_label(body, 'Repository name')
        self._dlg_entry(body, name_var)

        # Init README checkbox
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
                self._write(f'$ git init {path}\n', 'cmd')
                r = subprocess.run(['git', 'init', path],
                                   capture_output=True, text=True)
                self._write(r.stdout or r.stderr)
                if r.returncode != 0:
                    return
                if readme_var.get():
                    readme = os.path.join(path, 'README.md')
                    with open(readme, 'w') as f:
                        f.write(f'# {name}\n')
                    self._write('  Created README.md\n', 'dim')
                    subprocess.run(['git', 'add', 'README.md'], cwd=path)
                    subprocess.run(['git', 'commit', '-m',
                                    f'Initial commit\n\n{CO_AUTHOR}'], cwd=path)
                self._write(f'✓ Repository created: {path}\n', 'ok')
                self.root.after(0, self._set_repo, path, True)
                self.root.after(0, self._clear)
                self.root.after(10, self._write, f'  Opened: {path}\n', 'ok')
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Create', create, dlg.destroy)

    # ── Add Remote dialog ─────────────────────────────────────────────────────

    def dlg_add_remote(self):
        if not self.repo.get():
            self._write('\n  ✗ No repository open\n', 'err')
            return

        # Get current remote
        existing = subprocess.run('git remote get-url origin', shell=True,
                                   cwd=self.repo.get(), capture_output=True,
                                   text=True).stdout.strip()

        dlg = self._make_dialog('Add / Update Remote', 460, 240)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Add Remote', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        if existing:
            tk.Label(body, text=f'Current origin:  {existing}',
                     bg=BG, fg=GRAY, font=('Consolas', 9)).pack(anchor='w')

        name_var = tk.StringVar(value='origin')
        self._dlg_label(body, 'Remote name')
        self._dlg_entry(body, name_var)

        url_var = tk.StringVar(value=existing)
        self._dlg_label(body, 'Remote URL  (e.g. https://github.com/user/repo.git)')
        self._dlg_entry(body, url_var)

        def add():
            name = name_var.get().strip()
            url  = url_var.get().strip()
            if not url:
                return
            dlg.destroy()
            def w():
                self._section('Add Remote')
                # Remove existing if present so we can set/update
                subprocess.run(f'git remote remove {name}', shell=True,
                               cwd=self.repo.get(), capture_output=True)
                r = subprocess.run(['git', 'remote', 'add', name, url],
                                   cwd=self.repo.get(),
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    self._write(f'✓ Remote "{name}" → {url}\n', 'ok')
                else:
                    self._write(r.stderr, 'err')
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Add', add, dlg.destroy)

    # ── Create GitHub repo dialog ─────────────────────────────────────────────

    def dlg_gh_create(self):
        if not self.repo.get():
            self._write('\n  ✗ No repository open\n', 'err')
            return
        if not gh_available():
            self._write('\n  ✗ GitHub CLI (gh) not found.\n'
                        '    Install: https://cli.github.com\n', 'err')
            return

        dlg = self._make_dialog('Create GitHub Repository', 460, 310)
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill='both', expand=True)

        tk.Label(body, text='Create on GitHub', font=('Segoe UI', 12, 'bold'),
                 bg=BG, fg=FG).pack(anchor='w', pady=(0, 12))

        default_name = os.path.basename(self.repo.get())
        name_var = tk.StringVar(value=default_name)
        self._dlg_label(body, 'Repository name')
        self._dlg_entry(body, name_var)

        desc_var = tk.StringVar()
        self._dlg_label(body, 'Description  (optional)')
        self._dlg_entry(body, desc_var)

        # Public / Private
        vis_var = tk.StringVar(value='private')
        vf = tk.Frame(body, bg=BG)
        vf.pack(anchor='w', pady=(10, 0))
        for val, lbl in [('public', 'Public'), ('private', 'Private')]:
            tk.Radiobutton(vf, text=lbl, variable=vis_var, value=val,
                           bg=BG, fg=FG, selectcolor=BG3,
                           activebackground=BG, activeforeground=FG,
                           font=('Segoe UI', 9), cursor='hand2').pack(side='left',
                                                                       padx=(0, 12))

        # Push after create
        push_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text='Push current branch after creating',
                       variable=push_var, bg=BG, fg=FG, selectcolor=BG3,
                       activebackground=BG, activeforeground=FG,
                       font=('Segoe UI', 9), cursor='hand2').pack(anchor='w',
                                                                    pady=(8, 0))

        def create():
            name = name_var.get().strip()
            desc = desc_var.get().strip()
            vis  = vis_var.get()
            push = push_var.get()
            if not name:
                return
            dlg.destroy()
            def w():
                self._section(f'Create GitHub: {name}')
                cmd = ['gh', 'repo', 'create', name, f'--{vis}',
                       '--source', self.repo.get(), '--remote', 'origin']
                if desc:
                    cmd += ['--description', desc]
                if push:
                    cmd.append('--push')
                self._write('$ ' + ' '.join(cmd) + '\n', 'cmd')
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.stdout:
                    self._write(r.stdout)
                if r.stderr:
                    self._write(r.stderr, 'err' if r.returncode != 0 else 'dim')
                if r.returncode == 0:
                    self._write(f'✓ GitHub repo "{name}" created\n', 'ok')
                self._refresh()
            threading.Thread(target=w, daemon=True).start()

        self._dlg_buttons(body, 'Create', create, dlg.destroy)

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
            # Offer to initialise the folder instead of just rejecting it
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
                    r = subprocess.run(['git', 'init', path],
                                       capture_output=True, text=True)
                    self._write(r.stdout or r.stderr)
                    if r.returncode == 0:
                        self._write(f'✓ Initialised: {path}\n', 'ok')
                        self.root.after(0, self._set_repo, path, True)
                        self.root.after(0, self._clear)
                        self.root.after(10, self._write, f'  Opened: {path}\n', 'ok')
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
        """Check for staged files using porcelain status — works even with no commits."""
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
        r = subprocess.run(cmd, shell=True, cwd=repo,
                           capture_output=True, text=True)
        if r.stdout:
            self._write(r.stdout)
        if r.stderr:
            self._write(r.stderr, 'dim' if r.returncode == 0 else 'err')
        return r

    def _git_commit(self, msg):
        repo = self.repo.get()
        full = f"{msg}\n\n{CO_AUTHOR}"
        self._write(f'$ git commit -m "{msg}"\n', 'cmd')
        r = subprocess.run(['git', 'commit', '-m', full],
                           cwd=repo, capture_output=True, text=True)
        if r.stdout:
            self._write(r.stdout)
        if r.stderr:
            self._write(r.stderr, 'dim' if r.returncode == 0 else 'err')
        return r

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
            self.root.after(0, self._update_header, branch, dirty)
        threading.Thread(target=worker, daemon=True).start()

    def _update_header(self, branch, dirty):
        self._branch_lbl.config(text=f'⎇  {branch}')
        c = ORANGE if dirty else GREEN
        self._dot.config(fg=c)
        self._status_lbl.config(text='Modified' if dirty else 'Clean', fg=c)

    # ── Actions ───────────────────────────────────────────────────────────────

    def do_status(self):
        def w():
            self._section('Status')
            self._git('git status')
            self._refresh()
        self._run(w)

    def do_diff(self):
        def w():
            self._section('Diff')
            r = subprocess.run('git diff --stat', shell=True, cwd=self.repo.get(),
                               capture_output=True, text=True)
            if r.stdout.strip():
                self._git('git diff')
            else:
                self._write('  No unstaged changes\n', 'info')
        self._run(w)

    def do_log(self):
        def w():
            self._section('Log  (last 20)')
            self._git('git log --oneline --graph --color=never -20')
        self._run(w)

    def do_pull(self):
        def w():
            self._section('Pull')
            self._git('git pull')
            self._refresh()
        self._run(w)

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
        path = filedialog.askopenfilename(initialdir=repo,
                                           title='Select file to stage')
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

    def do_commit(self):
        msg = self._msg.get().strip()
        if not msg:
            self._write('\n  ✗ Type a commit message first\n', 'err')
            self._entry.focus()
            return
        def w():
            self._section('Commit')
            if not self._has_staged():
                self._write('  Nothing staged — run Stage All first\n', 'info')
                return
            r2 = self._git_commit(msg)
            if r2.returncode == 0:
                self._write('✓ Committed\n', 'ok')
                self.root.after(0, self._msg.set, '')
            self._refresh()
        self._run(w)

    def do_push(self):
        def w():
            self._section('Push')
            r = self._git('git push')
            if r.returncode == 0:
                self._write('✓ Pushed\n', 'ok')
            self._refresh()
        self._run(w)

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
            r3 = self._git('git push')
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
    root.tk_setPalette(background=BG, foreground=FG)
    GitManager(root)
    root.mainloop()
