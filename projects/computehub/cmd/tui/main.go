package main

import (
	"os"

	"github.com/computehub/opc/src/tuicmd"
)

func main() {
	tuicmd.Run(os.Args[1:])
}
