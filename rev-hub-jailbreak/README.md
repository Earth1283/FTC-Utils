# 🔓 REV HUB JAILBREAK 🔓
### *(or: talking to your Expansion Hub without asking the Robot Controller app for permission)*

Volume 2 of the shrine promised in the main README. This time it's REV's Expansion Hub instead of the Control Hub's Android side.

## What is this thing

Your REV Expansion Hub doesn't speak "FTC SDK." It speaks a dumb little serial protocol called **Lynx**, and the SDK's Java classes are just one client of it. This repo re-implements that protocol directly in Python (`lynx.py`) and gives you a CLI (`main.py`) to poke at a hub without an Android device, a Robot Controller app, or an OpMode anywhere in the loop.

None of this is secret or reverse-engineered from a binary. The protocol is sitting in plain sight in the open-source FTC SDK (`com.qualcomm.hardware.lynx`), in REV's own [Saleae logic analyzer plugin](https://github.com/REVrobotics/REV-Hub-Serial-Protocol-Analyzer-For-Saleae), and in the community [REVHubInterface](https://github.com/unofficial-rev-port/REVHubInterface) project, which got there first and deserves the credit. This is a from-scratch reimplementation of the same wire format, built for messing around at the protocol layer instead of driving motors through the normal API.

## What "jailbreak" actually means here

Be honest with yourself about what this is: it's a raw command sender for a protocol that already has *some* commands the SDK doesn't bother exposing to teams (debug log verbosity, direct LED control/patterns, interface introspection via `QUERY_INTERFACE`). It is **not** a firmware exploit. There is no known vulnerability being used. You already have full authority to send any Lynx command to your own hub - this just removes the Java/Android/OpMode scaffolding in the way.

## What it does

1. Finds your hub by scanning USB serial ports for REV's FTDI chip (VID `0x0403`, PID `0x6015`)
2. Opens a raw 460800-baud connection and does a keep-alive / discovery handshake
3. Drops you into a `lynx>` REPL:

   ```
   lynx> help
   lynx> heartbeat              # keep-alive loop, Ctrl+C to stop
   lynx> status                 # raw module status dump
   lynx> strobe                 # LED color cycle, Ctrl+C to stop
   lynx> led 255 0 128          # set LED to one color
   lynx> query DEKAInterface    # ask the hub for a command group's base opcode
   lynx> debuglog 3 5           # bump debug log verbosity
   lynx> scan                   # probe every DEKAInterface ordinal, report what answers
   lynx> raw 7f0a ff0080        # send any opcode + payload you want
   lynx> exit
   ```

   `query` is how you find opcodes the SDK doesn't publish a constant for (e.g. `DEKAInterface`, the group owning motors/servos/DIO/I2C/ADC). `scan` is the actual "what does this hub do that nobody told you about" button. `raw` is the whole point of the tool - everything else is a convenience wrapper around it.

## What it deliberately does NOT do

**No firmware flashing.** `START_DOWNLOAD` (`0x7f08`) and `DOWNLOAD_CHUNK` (`0x7f09`) exist in the protocol and are defined as constants in `lynx.py`, but nothing calls them. Nobody has published the actual bootloader image format or a legitimate custom firmware to push through them. Implementing that without the real payload spec isn't a jailbreak, it's a coin flip on turning your hub into e-waste. If you want to go there, that's a separate, much better-researched project - not this one.

## ⚠️ things this script will absolutely NOT stop you from doing

- Sending a raw command that happens to also be a motor/servo SET opcode with garbage in the payload, while a motor is still plugged in
- Bricking your bus timing by holding the port open during an actual match
- Getting DQ'd for "unauthorized modification of REV hardware behavior" (READ YOUR GAME MANUAL, again)
- Finding an undocumented opcode that does something delightful and never telling anyone
- Crying, again

**Before scanning or raw-sending: unplug your motors and servos.** The scanner sends zero-payload probes, and a zero-payload "set power" command is unlikely to spin anything up hard - but this whole tool exists because "documented behavior" or "defined behavior" is not something we're relying on here.

## Usage

```bash
pip install -r requirements.txt
python main.py
```

Plug in an Expansion Hub over USB (a bare board, not a Control Hub's Android port - the Control Hub's internal Lynx chip isn't reachable externally over USB, only over its internal UART). Pick a menu option. Find out what your hub actually does.

## Disclaimer

Same as Volume 1: the author is **NOT LIABLE**. You're sending arbitrary commands to a daisy-chain protocol designed for a very specific set of Java classes to talk to, from a Python script that was designed to be *slightly* little unhinged. Act accordingly.
