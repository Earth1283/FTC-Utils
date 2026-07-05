import shlex
import sys

from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

from lynx import (
    CH_EMBEDDED_MODULE_ADDRESS,
    LynxError,
    LynxHub,
    LynxNack,
    LynxTimeout,
    find_hub_port,
)

main_theme = Theme({
    "warning_explicit": "#FF0000 on #FFFF00",
    "success": "green bold",
    "warning": "yellow",
    "error": "bold #FF0000",
})

console = Console(theme=main_theme)


def connect() -> LynxHub:
    with console.status("[blue]Scanning USB for a REV Expansion Hub (FTDI 0403:6015)...", spinner="aesthetic"):
        port = find_hub_port()
    if port is None:
        console.print(
            Panel(
                "[error]No REV hub found on any serial port.[/]\n"
                "Plug an Expansion Hub in over USB (not a Control Hub's Android side - "
                "that one only talks Lynx internally), or check `python -m serial.tools.list_ports -v`.",
                title="[bold red]Not Found[/bold red]",
                border_style="red",
            )
        )
        sys.exit(1)
    console.print(f"[#90ee90]Found hub on {port}")
    hub = LynxHub(port=port, dest_address=CH_EMBEDDED_MODULE_ADDRESS)
    hub.open()
    try:
        hub.keep_alive()
    except LynxError as e:
        console.print(f"[warning]Keep-alive at default address {CH_EMBEDDED_MODULE_ADDRESS} failed ({e}). "
                       "Trying discovery instead...[/]")
        found = hub.discover()
        if not found:
            console.print("[error]Discovery found nothing either. Is the hub powered?[/]")
            sys.exit(1)
        hub.dest_address = found[0]
        console.print(f"[#90ee90]Discovered module at address {found[0]}")
    return hub


HELP_TEXT = (
    "[bold]help[/bold]                       this text\n"
    "[bold]heartbeat[/bold]                  keep-alive loop (0x7f04), Ctrl+C to stop\n"
    "[bold]status[/bold]                     dump raw module status (0x7f03)\n"
    "[bold]strobe[/bold]                     LED color cycle (0x7f0a spammed), Ctrl+C to stop\n"
    "[bold]led <r> <g> <b>[/bold]            set LED to one color, 0-255 each\n"
    "[bold]query <name>[/bold]               QUERY_INTERFACE (0x7f07), e.g. 'query DEKAInterface'\n"
    "[bold]debuglog <group> <verbosity>[/bold]  DEBUG_LOG_LEVEL (0x7f0e)\n"
    "[bold]scan[/bold]                       probe every DEKAInterface ordinal, report what answers\n"
    "[bold]raw <opcode_hex> [payload_hex][/bold]  send any opcode you want - everything above wraps this\n"
    "[bold]exit[/bold] / [bold]quit[/bold]                exit\n\n"
    "No command here flashes firmware. See the README for why."
)


def cmd_help(hub: LynxHub, args: list[str]):
    console.print(Panel(HELP_TEXT, title="Help", border_style="blue"))


def cmd_heartbeat(hub: LynxHub, args: list[str]):
    import time as _time
    console.print("[#87ceeb]Sending keep-alive every second. Ctrl+C to stop.")
    try:
        while True:
            hub.keep_alive()
            console.print("[success]  alive")
            _time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[warning]Stopped.")


def cmd_status(hub: LynxHub, args: list[str]):
    payload = hub.get_module_status()
    console.print(f"raw status payload: {payload.hex()}")


def cmd_led_strobe(hub: LynxHub, args: list[str]):
    import itertools
    import time as _time
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
    console.print("[#87ceeb]Strobing. Ctrl+C to stop and leave it however it lands.")
    try:
        for r, g, b in itertools.cycle(colors):
            hub.set_led_color(r, g, b)
            _time.sleep(0.15)
    except KeyboardInterrupt:
        console.print("\n[warning]Stopped mid-strobe. Sorry about your eyes.")


def cmd_led_set(hub: LynxHub, args: list[str]):
    if len(args) != 3:
        console.print("[error]Usage: led <r> <g> <b>")
        return
    try:
        r, g, b = (max(0, min(255, int(x))) for x in args)
    except ValueError:
        console.print("[error]That's not three numbers.")
        return
    hub.set_led_color(r, g, b)
    console.print(f"[success]LED set to ({r}, {g}, {b})")


def cmd_query_interface(hub: LynxHub, args: list[str]):
    if len(args) != 1:
        console.print("[error]Usage: query <interface name>, e.g. query DEKAInterface")
        return
    name = args[0]
    try:
        first_cmd, count = hub.query_interface(name)
        console.print(f"[success]'{name}' -> base opcode 0x{first_cmd:04x}, {count} commands")
        console.print(f"[#87ceeb]Ordinals 0..{count - 1} map to opcodes 0x{first_cmd:04x}..0x{first_cmd + count - 1:04x}")
    except LynxNack as e:
        console.print(f"[error]NACKed (reason 0x{e.nack_reason:02x}) - interface probably doesn't exist by that name.")


def cmd_debug_log(hub: LynxHub, args: list[str]):
    if len(args) != 2:
        console.print("[error]Usage: debuglog <group> <verbosity> (both 0-255)")
        return
    try:
        group, verbosity = int(args[0]), int(args[1])
    except ValueError:
        console.print("[error]Need two integers.")
        return
    hub.debug_log_level(group, verbosity)
    console.print("[success]Debug log level set. Check the hub's serial debug output (if you're tapped into it).")


def cmd_deka_scan(hub: LynxHub, args: list[str]):
    console.print(
        Panel(
            "[warning_explicit]This sends zero-payload probes to a range of DEKA ordinals.[/]\n"
            "Ordinal 0 (GetBulkInputData) is a known-safe read. Higher ordinals include motor/servo "
            "SET commands - a zero-payload SET is unlikely to spin anything up, but 'unlikely' is not "
            "'impossible'. Unplug motors and servos before continuing if you want to be safe about it.",
            title="[bold red]Read before continuing[/bold red]",
            border_style="red",
        )
    )
    if console.input("Type 'yes' to continue: \n> ").strip().lower() not in ("yes", "y"):
        return
    try:
        base, count = hub.query_interface("DEKAInterface")
    except LynxNack:
        console.print("[error]Couldn't get a DEKAInterface base opcode. Aborting scan.")
        return
    console.print(f"[#87ceeb]Probing {count} DEKA ordinals from base 0x{base:04x}...")
    for i in range(count):
        opcode = base + i
        try:
            resp = hub.raw_command(opcode, b"")
            console.print(f"  ordinal {i:>3} (0x{opcode:04x}): [success]responded[/] - {resp.payload.hex() or '(empty)'}")
        except LynxNack as e:
            console.print(f"  ordinal {i:>3} (0x{opcode:04x}): NACK 0x{e.nack_reason:02x}")
        except LynxTimeout:
            console.print(f"  ordinal {i:>3} (0x{opcode:04x}): [warning]no response[/]")


def cmd_raw(hub: LynxHub, args: list[str]):
    if not args:
        console.print("[error]Usage: raw <opcode_hex> [payload_hex], e.g. raw 7f0a ff0080")
        return
    try:
        opcode = int(args[0], 16)
        payload = bytes.fromhex(args[1]) if len(args) > 1 else b""
    except ValueError:
        console.print("[error]Bad hex.")
        return
    try:
        resp = hub.raw_command(opcode, payload)
        console.print(f"[success]Response payload: {resp.payload.hex() or '(empty)'}")
    except LynxNack as e:
        console.print(f"[error]NACK, reason 0x{e.nack_reason:02x}")
    except LynxTimeout:
        console.print("[error]Timed out. Hub either ignored it or fell over. Check the LED.")


COMMANDS = {
    "help": cmd_help,
    "?": cmd_help,
    "heartbeat": cmd_heartbeat,
    "hb": cmd_heartbeat,
    "status": cmd_status,
    "strobe": cmd_led_strobe,
    "led": cmd_led_set,
    "query": cmd_query_interface,
    "debuglog": cmd_debug_log,
    "scan": cmd_deka_scan,
    "raw": cmd_raw,
}


def main():
    console.clear()
    console.print("[bold]REV Hub Jailbreak[/bold] - talks raw Lynx protocol directly to your Expansion Hub.")
    console.print("[#FF0000 on #FFFF00]No firmware flashing here on purpose - that's how you turn a hub into a paperweight.[/]")
    console.print("This pokes documented-but-unexposed corners of the protocol instead. Type 'help' to see commands.\n")

    hub = connect()

    try:
        while True:
            try:
                line = console.input("[bold cyan]lynx>[/bold cyan] ").strip()
            except EOFError:
                break
            if not line:
                continue
            try:
                parts = shlex.split(line)
            except ValueError as e:
                console.print(f"[error]Bad input: {e}")
                continue
            name, args = parts[0].lower(), parts[1:]
            if name in ("exit", "quit", "q"):
                break
            action = COMMANDS.get(name)
            if action is None:
                console.print(f"[error]Unknown command '{name}'. Type 'help' for the list.")
                continue
            try:
                action(hub, args)
            except LynxTimeout as e:
                console.print(f"[error]Timeout: {e}")
            except LynxNack as e:
                console.print(f"[error]{e}")
    finally:
        hub.close()

    console.print("Goodbye :)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[warning]Interrupted. Goodbye :)[/]")
        sys.exit(1)
