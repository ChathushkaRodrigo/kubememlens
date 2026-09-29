package nodebinding

import "time"

func (s *Service) wakeExpiry() {
	select {
	case s.wake <- struct{}{}:
	default:
	}
}

// nextExpiry is called with mu held. A live execution keeps its reference and
// replay record until finish. Expired executions retain the cleanup cadence
// instead of continuously rearming a timer for an already elapsed deadline.
func (s *Service) nextExpiry(now time.Time) time.Time {
	var next time.Time
	for _, l := range s.leases {
		at := l.expires
		if l.execution != nil && !at.After(now) {
			at = now.Add(100 * time.Millisecond)
		}
		if next.IsZero() || at.Before(next) {
			next = at
		}
	}
	for id, at := range s.seen {
		if _, busy := s.leases[id]; busy {
			continue
		}
		if next.IsZero() || at.Before(next) {
			next = at
		}
	}
	return next
}
