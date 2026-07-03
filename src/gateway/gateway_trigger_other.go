//go:build !linux

package gateway

// Platform fallbacks for non-Linux systems (darwin, windows, etc.)

func readCPUPercent() float64 {
	return 0
}

func readMemPercent() float64 {
	return 0
}

func readLoad1m() float64 {
	return 0
}

func readDiskPercent() float64 {
	return 0
}