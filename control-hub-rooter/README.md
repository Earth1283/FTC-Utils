# 🔥 CONTROL HUB ROOTER 🔥
### *(or: How I Learned to Stop Worrying and Love `adb root`)*

You found it. The forbidden script. The one your mentor said not to run "the night before Worlds." You're running it the night before Worlds.

## What is this thing

`main.py` is a chatty little Python wizard that walks up to your REV Control Hub — the beige brick your entire robot's soul lives inside — and asks it, politely at first, then with increasing TCP/IP-based insistence, to hand over root.

It:
1. Finds your `adb` binary by crawling your filesystem like a raccoon looking for garbage
2. Makes you type "yes" not once, but **twice**, because the author knows you don't read
3. Slaps you with a big red-on-yellow `warning_explicit` banner that basically says *"not my problem, champ"*
4. Flips your Control Hub into TCP/IP mode on port 5555 (your robot is now, technically, on the network — do with that what you will)
5. Spam-calls `adb root` in a `for _ in range(10)` loop like it's redialing a food order that didn't go through
6. Remounts `/system` read-write, because apparently read-only filesystems are a suggestion
7. Checks `whoami` to confirm you are, in fact, god now
8. Drops you into a raw interactive root shell on your **competition robot controller**, or offers to make the rootedness **survive a reboot** by hand-appending to `/vendor/build.prop` like it's 2011 XDA-Developers forums

That's it. That's the whole ritual. No undo button. No dry-run flag. Just vibes, `rich` console colors, and a spinner called `"aesthetic"`.

## Why does this exist

Because somewhere, an FTC team's Control Hub needed something root-only — sysctl tweak, weird sensor driver, forbidden governor setting, who knows — and the normal, sane, competition-legal, sanctioned path was too slow. So now there's a script for that. A whole vibe-coded, rich-console, ANSI-colored ritual for it.

## ⚠️ things this script will absolutely NOT stop you from doing

- Bricking the exact device that needs to survive an FTC scrimmage in six hours
- Getting your Control Hub DQ'd for running modified firmware (READ YOUR GAME MANUAL)
- Typing shell commands into `root@yourFtcBot ❯` that you found in a forum post from a guy named `xXRobotGodXx`
- Persisting root across reboots by literally `echo`-ing into `/vendor/build.prop` like a caveman etching cave walls
- Crying

## Usage

```bash
python main.py
```

Then answer "yes" when it asks if you want to begin. Answer "yes" again when it asks if you're **sure** sure. Then plug in your Control Hub, wait for the spinner, and hand your robot's entire operating system over to a script that found `adb` by walking your directory tree hoping for the best.

If it can't find `adb`, it will ask you, an FTC team member, to locate a binary on your own filesystem by hand. Good luck.

## Don't have a Control Hub? There's a lie for that.

See [`fake-adb/`](fake-adb/) — a fake `adb` binary that answers every question this script asks with the exact string it wants to hear, and roots absolutely nothing. For demos, talks, and lying to pit judges.

## Roadmap / Prophecy

This repo is not done being unhinged. More tools are coming. This is Volume 1 in what will presumably become a shrine of increasingly deranged FTC utilities — scripts that do things to Control Hubs, Driver Stations, and possibly REV hardware that the sanctioning body has strong feelings about. Watch this space. Or don't. It'll find you anyway, probably during an actual match.

## Disclaimer

The author is **NOT LIABLE**. The script tells you this. Twice. In red-on-yellow. This README is telling you a third time, just to be safe. If your robot achieves sentience, unionizes, or refuses to move because it's still stuck in TCP/IP debug mode on port 5555 in the middle of a match — that's between you and it now. Godspeed.
