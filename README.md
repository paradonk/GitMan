# GitMan

A lightweight desktop GUI for Git, built with Python and Tkinter.  
Dark-themed, thread-safe, works with any repository.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Tkinter](https://img.shields.io/badge/UI-Tkinter-green) ![License](https://img.shields.io/badge/license-MIT-gray)

---

## Requirements

- Python 3.8 or later
- Tkinter (included with most Python installations)
- Git installed and available in PATH
- GitHub CLI (`gh`) — optional, required for **🐙 GitHub** feature

---

## Run

```bash
python3 gitman.py
```

Or add an alias to `~/.bashrc`:

```bash
alias gitman='python3 /path/GitMan/gitman.py'
```

Then just type `gitman` from anywhere.

---

## Features

| Button | Action |
|--------|--------|
| **＋ New** | Create a new local repository |
| **Open…** | Open an existing repository |
| **▾ Recent** | Switch between recently opened repositories |
| **Status** | Show working tree status |
| **Diff** | Show unstaged changes |
| **Log** | Last 20 commits with graph |
| **Pull** | Pull from remote |
| **Stage All** | Stage every changed file (`git add -A`) |
| **Stage File…** | Open file picker and stage a specific file |
| **Commit** | Commit staged files using the message box |
| **Push** | Push to origin |
| **⚡ Quick** | Stage all + commit + push in one click |
| **Add Remote** | Add or update the remote URL |
| **🐙 GitHub** | Create a GitHub repository via `gh` CLI |
| **↻** | Refresh branch name and status indicator |

---

## Workflow

### New project from scratch
1. Click **＋ New** — create local repo with optional README
2. Click **🐙 GitHub** — create GitHub repo and push in one step

### Quick commit & push (most common)
1. Type a commit message in the message box
2. Click **⚡ Quick** — stages everything, commits, and pushes

### Step by step
1. **Stage All** — stage all changes
2. Type a commit message
3. **Commit** — commits locally only
4. **Push** — push when ready

### Stage specific files
1. **Stage File…** — pick one file to stage
2. Repeat for other files if needed
3. Type a message → **Commit**

---

## Repo Management

- **＋ New** — create a new folder, run `git init`, optionally add README
- **Open…** — browse to any folder and open it as a repository
- **▾ Recent** — dropdown of last 10 opened repositories
- Recent repos are saved to `~/.gitman_recent.json`
- On startup, the app opens the last used repo automatically

---

## Status Indicator

| Colour | Meaning |
|--------|---------|
| 🟢 Green — Clean | No uncommitted changes |
| 🟠 Orange — Modified | Uncommitted changes exist |

---

## Output Panel

Command output is colour-coded:

| Colour | Meaning |
|--------|---------|
| Blue | Command being run |
| Green | Success |
| Red | Error |
| Orange | Warning / info |
| Gray | Secondary output |

Click **Clear** to clear the output panel.

---

## Commit Message Format

Every commit automatically appends:

```
Co-Authored-By: K.Paradorn <paradonk@gmail.com>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Messages are passed to Git as a list argument (not a shell string),  
so quotes, apostrophes, and special characters work without escaping.

---

## Files

```
GitMan/
├── gitman.py    # Main application
└── README.md    # This file
```

Config file created automatically:

```
~/.gitman_recent.json    # Recent repository list
```
