package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/danushkastanley/kube-memlens/internal/historyview"
)

func (m appModel) historyPanelLines(width int) []string {
	p := m.historyPanel
	name := p.request.Name
	if p.request.Namespace != "" {
		name = p.request.Namespace + "/" + name
	}
	lines := []string{fmt.Sprintf("%s history (%s): %s", p.request.Scope, p.source, name)}
	if p.loading {
		lines = append(lines, "Loading "+string(p.source)+" history...")
	}
	if p.err != nil {
		lines = append(lines, "History unavailable: "+p.err.Error(), "Press l to request local history explicitly, or Esc for live evidence.")
	}
	if p.report != nil {
		lines = append(lines, historyview.Lines(*p.report, time.Now().UTC(), width)...)
	}
	return wrapText(lines, width)
}

func (m appModel) renderHistoryPanel(width int) string {
	lines := m.historyPanelLines(width)
	v := m.historyPanel.viewport
	v.resize(max(1, m.bodyRows()-2))
	v.reconcile(len(lines))
	start, end := v.visibleRange()
	header := truncate("Memory trends: l local | p Prometheus | r refresh | Esc close", width)
	footer := truncate(fmt.Sprintf("Lines %d-%d/%d | j/k scroll | PgUp/PgDown page", start+1, end, len(lines)), width)
	return header + "\n" + strings.Join(lines[start:end], "\n") + "\n" + footer
}
