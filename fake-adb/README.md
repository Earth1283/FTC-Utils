# 🎭 FAKE ADB 🎭
### *(or: How To Root A Robot That Doesn't Exist In Front Of A Judge Who Definitely Believes You)*

You know how `main.py` is a whole unhinged ritual that begs your actual Control Hub for actual root? This is the version for when you don't have a Control Hub, don't have time, or are standing in front of pit judges who just want to see the number go up.

This is a fake `adb`. It is not `adb`. It has never once talked to a real device. It is a Go binary that memorized the exact lines `main.py` checks for and says them back with a straight face.

## What it actually does

Reads `os.Args[1:]`, pattern-matches, prints the *exact* magic strings `main.py` is grepping for, exits happy. That's the whole binary. No device, no protocol, no `libusb`, no risk. `main.go` is like 40 lines. Go read it, it's short and there's nothing hiding in there.

| You type (via `main.py`) | It says back |
|---|---|
| `devices` | `DEMOHUB001    device` — a device that has never existed |
| `tcpip 5555` | `restarting in TCP mode port: 5555` |
| `root` | `adbd is already running as root` (first try, no 10x redial loop, we're not savages) |
| `remount` | `remount succeeded` |
| `shell whoami` | `root` — yes, you are god, no, not really |
| anything else | silence, which `main.py` reads as success because nobody checks exit codes around here |

## Why this exists

Because demoing `main.py` against a real Control Hub means owning a Control Hub, plugging it in, and hoping the USB gods cooperate on stage. This way you get the full red-banner, spinner-called-"aesthetic", "we are rooted" experience with zero hardware, zero risk, zero chance of actually bricking anything important. It is a magic trick. The rabbit was never real.

## Building it

```bash
go build -o adb main.go                              # native
GOOS=darwin  GOARCH=amd64 go build -o adb-mac-amd64   main.go
GOOS=darwin  GOARCH=arm64 go build -o adb-mac-arm64   main.go
GOOS=linux   GOARCH=amd64 go build -o adb-linux-amd64 main.go
GOOS=windows GOARCH=amd64 go build -o adb-windows.exe main.go
```

Drop the right one next to `main.py` (or point it there when asked for a path), name it `adb`/`adb.exe`, and `find_adb()` will happily believe it's the real thing. It has no idea. Neither will your audience.

## ⚠️ things this binary will absolutely NOT do

- Talk to an actual device
- Root anything, ever, under any circumstance
- Care what you type into the interactive shell afterward (it'll just sit there like a mime)
- Tell anyone it's fake unless they read this README or the 40 lines of Go

## Disclaimer

This is a prop. A puppet. Smoke and mirrors for a robot that's still fully unrooted and very confused about why everyone's clapping. Use it for demos, talks, and pit displays — not for convincing yourself you actually did the thing.

Built binaries (`adb`, `adb-*`, `*.exe`) are gitignored on purpose. Only `main.go` gets to live in the repo forever.
