package incident

import (
	"encoding/json"
	"fmt"
	"io"
	"slices"
	"strings"
	"time"

	"github.com/danushkastanley/kube-memlens/internal/changemarkers"
)

const HistorySchemaVersion = 6
const MaxHistoryBytes = 2 << 20

var historyCaveats = []string{
	"Retained events are best-effort reports; missing events do not prove no changes.",
	"Source clocks may differ; correlation does not establish causation.",
	"History covers current selected instances; markers do not join memory across UIDs.",
}

const historyAliasCaveat = "Aliases apply only within this capture; they cannot establish identity continuity across captures."

type HistoryBundle struct {
	SchemaVersion int                   `json:"schemaVersion"`
	CapturedAt    time.Time             `json:"capturedAt"`
	ToolVersion   string                `json:"toolVersion"`
	Redacted      bool                  `json:"redacted"`
	Context       changemarkers.Context `json:"context"`
	Caveats       []string              `json:"caveats"`
}

func NewHistory(c changemarkers.Context, version string, at time.Time, sensitive bool) (HistoryBundle, error) {
	b := HistoryBundle{SchemaVersion: HistorySchemaVersion, CapturedAt: at.UTC(), ToolVersion: version, Context: c, Caveats: append([]string(nil), historyCaveats...)}
	if err := ValidateHistory(b); err != nil {
		return HistoryBundle{}, err
	}
	encoded, err := json.Marshal(b)
	if err != nil {
		return HistoryBundle{}, err
	}
	var copied HistoryBundle
	if err := json.Unmarshal(encoded, &copied); err != nil {
		return HistoryBundle{}, err
	}
	if !sensitive {
		if err := redactHistory(&copied); err != nil {
			return HistoryBundle{}, err
		}
		copied.Caveats = append(copied.Caveats, historyAliasCaveat)
	}
	return copied, ValidateHistory(copied)
}

func ValidateHistory(b HistoryBundle) error {
	if b.SchemaVersion != HistorySchemaVersion || b.Context.Validate() != nil || b.CapturedAt.IsZero() || b.Context.Changes.ObservedAt.After(b.CapturedAt) || b.Context.History.ReceivedAt.After(b.CapturedAt) || b.ToolVersion == "" || len(b.ToolVersion) > 512 || strings.IndexFunc(b.ToolVersion, func(r rune) bool { return r < 32 || r == 127 }) >= 0 {
		return fmt.Errorf("invalid memory history incident")
	}
	expected := append([]string(nil), historyCaveats...)
	if b.Redacted {
		expected = append(expected, historyAliasCaveat)
		if err := validateHistoryAliases(b.Context); err != nil {
			return err
		}
	}
	if !slices.Equal(expected, b.Caveats) {
		return fmt.Errorf("memory history incident lacks its provenance caveats")
	}
	encoded, err := json.Marshal(b)
	if err != nil || len(encoded) > MaxHistoryBytes {
		return fmt.Errorf("memory history incident exceeds its byte limit")
	}
	return nil
}

func WriteHistory(w io.Writer, path string, overwrite bool, b HistoryBundle) error {
	if err := ValidateHistory(b); err != nil {
		return err
	}
	encoder := json.NewEncoder(&boundedWriter{destination: io.Discard, remaining: MaxHistoryBytes})
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(b); err != nil {
		return fmt.Errorf("memory history incident exceeds its file byte limit")
	}
	return writeDocument(w, path, overwrite, b)
}
