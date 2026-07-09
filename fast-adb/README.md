# ⚡ FAST ADB ⚡
### *(adb, but it stops making you type the same six flags every five minutes)*

You know the drill: build, hunt for the apk, `adb install -r`, watch logcat, reconnect wifi adb after it drops for the 40th time. `fast-adb` wraps all of that in one command (or a REPL, if you're feeling chatty).

## What is this thing

`main.py` finds `adb` and `gradlew` by crawling the local directory tree (no PATH required, no hunting for the SDK), then gives you short commands for the stuff you do a hundred times a match day:

- **`reconnect` / `rcon`** - disconnect + reconnect to the Control Hub over wifi (defaults to `192.168.43.1:5555`)
- **`check` / `compile`** - run `./gradlew assembleDebug` with live output
- **`devices` / `ls`** - list connected/known devices in a clean table
- **`install`** - install the newest debug apk under `**/build/outputs/apk/debug/`, or pass `--apk`
- **`deploy` / `push`** - `check` then `install`, back to back
- **`logcat [filter]`** - stream logcat live, optionally filtered
- **`restart` / `restart-adb`** - kill and restart the adb server
- **`tcpip`** - flip a USB-connected device into tcpip mode on a given port (default 5555)

Run it with no args and it drops into a REPL (`fast-adb>`) so you can fire off commands without re-invoking python each time.

## Usage

```bash
pip install -r requirements.txt

python main.py devices
python main.py check
python main.py install
python main.py deploy
python main.py reconnect --host 192.168.43.1 --port 5555
python main.py logcat "MyTag:D *:S"
python main.py tcpip --port 5555

# or just run it bare for the REPL
python main.py
```

Needs an `adb` binary somewhere under the current directory (this folder ships one) and, for `check`/`deploy`, a `gradlew` somewhere under the current directory too — point it at your FTC project root.

## Why does this exist
Because I am profoundly disappointed at Android Studio's handling of ADB (and as a result, I no longer use Android Studio; I exclusively use IntelliJ IDEA). Additionally, Google engineers think it's a great idea to persist dead connections to the robot without an explicit `./adb disconnect`, so every match you get to watch `device offline` mock you until you remember to kill the server yourself. And don't get me started on wifi adb dropping mid-match for no reason, silently, with zero indication anything went wrong until your next `install` hangs forever.
