package visualizer

import (
	"fmt"
	"testing"

	"github.com/computehub/opc/src/scheduler"
)

func TestRegisterNodeClean(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	node := &scheduler.NodeInfo{
		ID:     "node-clean-only",
		Region: "region-clean-only",
		GPUType: "A100",
		Status: "online",
	}
	gpm.RegisterNode(node)

	rd, exists := gpm.regions["region-clean-only"]
	if !exists {
		t.Fatal("region not found")
	}
	fmt.Printf("Nodes: %d\n", len(rd.Nodes))
	for i, n := range rd.Nodes {
		fmt.Printf("  [%d] ID=%q Region=%q\n", i, n.ID, n.Region)
	}
	if len(rd.Nodes) != 1 {
		t.Fatalf("Expected 1, got %d", len(rd.Nodes))
	}
}
