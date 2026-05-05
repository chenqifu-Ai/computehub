package prometheus

import (
	"fmt"
	"net/http"
	"sync"
	"sync/atomic"
	"time"
)

// ====== Metrics Registry ======

// Registry is a simple metrics registry
type Registry struct {
	mu          sync.RWMutex
	totalNodes       atomic.Int64
	onlineNodes      atomic.Int64
	totalTasks       atomic.Int64
	activeTasks      atomic.Int64
	taskSubmissions  atomic.Int64
	taskCompletions  atomic.Int64
	taskFailures     atomic.Int64
}

// NewRegistry creates a new metrics registry
func NewRegistry() *Registry {
	return &Registry{}
}

// CreateMetrics initializes and returns the Metrics struct
func (r *Registry) CreateMetrics() *Metrics {
	r.mu.Lock()
	defer r.mu.Unlock()
	return &Metrics{Registry: r}
}

// ====== Metrics Data Structure ======

// Metrics holds current metrics data
type Metrics struct {
	Registry *Registry
}

// ====== Metrics Collector ======

// Collector periodically updates metrics from kernel state
type Collector struct {
	metrics  *Metrics
	interval time.Duration
	stopCh   chan struct{}
	done     chan struct{}
	mu       sync.Mutex
	running  bool
}

// NewCollector creates a new metrics collector
func NewCollector(metrics *Metrics) *Collector {
	return &Collector{
		metrics:  metrics,
		interval: 5 * time.Second,
		stopCh:   make(chan struct{}),
		done:     make(chan struct{}),
	}
}

// Start begins the metrics collection loop
func (c *Collector) Start(interval time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.running {
		return
	}
	if interval > 0 {
		c.interval = interval
	}
	c.running = true
	go c.run()
}

// Stop stops the metrics collection loop
func (c *Collector) Stop() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.running {
		return
	}
	c.running = false
	close(c.stopCh)
	<-c.done
}

func (c *Collector) run() {
	defer close(c.done)
	ticker := time.NewTicker(c.interval)
	defer ticker.Stop()

	for {
		select {
		case <-c.stopCh:
			return
		case <-ticker.C:
			c.updateMetrics()
		}
	}
}

// updateMetrics refreshes metrics from kernel state
func (c *Collector) updateMetrics() {
	// Placeholder - will be connected to kernel.NodeMgr in gateway initialization
	if c.metrics == nil {
		return
	}
}

// RecordTaskSubmission increments the task submission counter
func (c *Collector) RecordTaskSubmission() {
	if c.metrics != nil && c.metrics.Registry != nil {
		c.metrics.Registry.taskSubmissions.Add(1)
	}
}

// RecordTaskCompletion records a completed task
func (c *Collector) RecordTaskCompletion(success bool, durationSeconds float64) {
	if c.metrics != nil && c.metrics.Registry != nil {
		c.metrics.Registry.taskCompletions.Add(1)
		if !success {
			c.metrics.Registry.taskFailures.Add(1)
		}
	}
}

// ====== HTTP Handler ======

// MetricsHandler returns an HTTP handler that serves Prometheus metrics
func MetricsHandler(reg *Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var output []string

		// System metrics
		output = append(output, gauge("computehub_total_nodes", reg.totalNodes.Load()))
		output = append(output, gauge("computehub_online_nodes", reg.onlineNodes.Load()))
		output = append(output, gauge("computehub_active_tasks", reg.activeTasks.Load()))
		output = append(output, counter("computehub_total_tasks", reg.totalTasks.Load()))
		output = append(output, counter("computehub_task_submissions_total", reg.taskSubmissions.Load()))
		output = append(output, counter("computehub_task_completions_total", reg.taskCompletions.Load()))
		output = append(output, counter("computehub_task_failures_total", reg.taskFailures.Load()))

		// Node metrics from kernel state
		output = append(output, nodeMetrics(reg)...)

		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, join(output))
	}
}

// ====== Helper Functions ======

func gauge(name string, value int64) string {
	return fmt.Sprintf("# HELP %s %s\n# TYPE %s gauge\n%s %d\n", name, name, name, name, value)
}

func counter(name string, value int64) string {
	return fmt.Sprintf("# HELP %s %s\n# TYPE %s counter\n%s %d\n", name, name, name, name, value)
}

func nodeMetrics(reg *Registry) []string {
	var lines []string
	// Placeholder - connects to kernel.NodeMgr when gateway initializes
	_ = reg
	_ = lines
	return lines
}

func join(s []string) string {
	if len(s) == 0 {
		return ""
	}
	result := s[0]
	for i := 1; i < len(s); i++ {
		result += s[i]
	}
	return result
}
