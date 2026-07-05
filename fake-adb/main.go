package main

import (
	"fmt"
	"os"
	"strings"
)

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		fmt.Println("Android Debug Bridge version 1.0.41 (demo)")
		return
	}

	switch args[0] {
	case "devices":
		fmt.Println("List of devices attached")
		fmt.Println("DEMOHUB001\tdevice")
	case "tcpip":
		port := "5555"
		if len(args) > 1 {
			port = args[1]
		}
		fmt.Printf("restarting in TCP mode port: %s\n", port)
	case "root":
		fmt.Println("adbd is already running as root")
	case "remount":
		fmt.Println("remount succeeded")
	case "disconnect":
	case "shell":
		handleShell(args[1:])
	}
}

func handleShell(shellArgs []string) {
	cmd := strings.Trim(strings.Join(shellArgs, " "), "\"")
	if strings.HasPrefix(cmd, "whoami") {
		fmt.Println("root")
	}
}
